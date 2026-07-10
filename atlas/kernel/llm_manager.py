from typing import Any, Dict, List, Optional

from atlas.kernel.event_bus import EventBus
from atlas.llm.base_provider import BaseLLMProvider


class LLMManager:
    """
    Administra los proveedores LLM de Atlas AI Platform.

    Permite registrar proveedores, elegir uno predeterminado
    y generar respuestas mediante una interfaz común.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._default_provider: Optional[str] = None

    def register(
        self,
        provider: BaseLLMProvider,
        make_default: bool = False,
    ) -> None:
        """
        Registra un proveedor LLM.
        """
        provider_name = self._normalize_name(provider.name)

        if provider_name in self._providers:
            raise ValueError(
                f"El proveedor '{provider_name}' ya está registrado."
            )

        self._providers[provider_name] = provider

        if make_default or self._default_provider is None:
            self._default_provider = provider_name

        self.event_bus.publish(
            "llm.provider.registered",
            {
                "provider": provider_name,
                "model": provider.model,
                "default": self._default_provider == provider_name,
            },
        )

    def get(
        self,
        provider_name: Optional[str] = None,
    ) -> BaseLLMProvider:
        """
        Obtiene un proveedor por nombre.

        Si no se indica uno, devuelve el proveedor predeterminado.
        """
        selected_name = provider_name or self._default_provider

        if selected_name is None:
            raise RuntimeError(
                "No hay proveedores LLM registrados."
            )

        normalized_name = self._normalize_name(selected_name)

        if normalized_name not in self._providers:
            raise KeyError(
                f"El proveedor '{normalized_name}' no está registrado."
            )

        return self._providers[normalized_name]

    def set_default(self, provider_name: str) -> None:
        """
        Establece el proveedor predeterminado.
        """
        normalized_name = self._normalize_name(provider_name)

        if normalized_name not in self._providers:
            raise KeyError(
                f"El proveedor '{normalized_name}' no está registrado."
            )

        self._default_provider = normalized_name

        self.event_bus.publish(
            "llm.default.changed",
            {
                "provider": normalized_name,
            },
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        provider_name: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Genera una respuesta mediante el proveedor seleccionado.
        """
        provider = self.get(provider_name)

        self.event_bus.publish(
            "llm.generation.started",
            {
                "provider": provider.name,
                "model": provider.model,
            },
        )

        try:
            response = provider.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                **kwargs,
            )

            self._validate_response(response)

            self.event_bus.publish(
                "llm.generation.completed",
                response,
            )

            return response

        except Exception as exc:
            self.event_bus.publish(
                "llm.generation.failed",
                {
                    "provider": provider.name,
                    "model": provider.model,
                    "error": str(exc),
                },
            )
            raise

    def list_names(self) -> List[str]:
        """
        Devuelve los nombres de los proveedores registrados.
        """
        return sorted(self._providers.keys())

    def list_providers(self) -> List[Dict[str, str]]:
        """
        Devuelve información de los proveedores registrados.
        """
        return [
            provider.information()
            for provider in self._providers.values()
        ]

    def count(self) -> int:
        """
        Devuelve la cantidad de proveedores registrados.
        """
        return len(self._providers)

    @property
    def default_provider(self) -> Optional[str]:
        """
        Devuelve el nombre del proveedor predeterminado.
        """
        return self._default_provider

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized_name = name.strip().lower()

        if not normalized_name:
            raise ValueError(
                "El nombre del proveedor no puede estar vacío."
            )

        return normalized_name

    @staticmethod
    def _validate_response(response: Dict[str, Any]) -> None:
        """
        Verifica que la respuesta tenga la estructura mínima requerida.
        """
        required_fields = {
            "provider",
            "model",
            "status",
            "content",
        }

        missing_fields = required_fields.difference(response.keys())

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))

            raise ValueError(
                "La respuesta del proveedor no contiene "
                f"los campos requeridos: {missing}"
            )