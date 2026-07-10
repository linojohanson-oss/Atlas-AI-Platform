from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseLLMProvider(ABC):
    """
    Clase base para todos los proveedores LLM de Atlas AI Platform.

    Todo proveedor (OpenAI, Gemini, Ollama, Claude, etc.)
    debe implementar esta interfaz.
    """

    name: str = "base"
    model: str = "unknown"

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Genera una respuesta utilizando un modelo de lenguaje.

        Returns
        -------
        Dict[str, Any]
            Diccionario estandarizado con la respuesta del proveedor.
        """
        raise NotImplementedError

    def information(self) -> Dict[str, str]:
        """
        Devuelve información básica del proveedor.
        """
        return {
            "provider": self.name,
            "model": self.model,
        }