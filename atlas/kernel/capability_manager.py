from typing import Dict, List, Optional

from atlas.kernel.event_bus import EventBus


class CapabilityManager:
    """
    Administra las capacidades disponibles en Atlas AI Platform.

    Una capacidad representa una función de alto nivel,
    como mathematics, spreadsheet o filesystem.

    Cada capacidad se vincula con una herramienta registrada.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

        self._capabilities: Dict[str, str] = {}

    def register(
        self,
        capability_name: str,
        tool_name: str,
        replace: bool = False,
    ) -> None:
        """
        Registra una capacidad y la herramienta que la implementa.
        """
        normalized_capability = self._normalize_name(
            capability_name
        )

        normalized_tool = self._normalize_name(
            tool_name
        )

        if (
            normalized_capability in self._capabilities
            and not replace
        ):
            raise ValueError(
                "La capacidad "
                f"'{normalized_capability}' "
                "ya está registrada."
            )

        previous_tool = self._capabilities.get(
            normalized_capability
        )

        self._capabilities[
            normalized_capability
        ] = normalized_tool

        event_name = (
            "capability.replaced"
            if previous_tool is not None
            else "capability.registered"
        )

        self.event_bus.publish(
            event_name,
            {
                "capability": normalized_capability,
                "tool": normalized_tool,
                "previous_tool": previous_tool,
            },
        )

    def resolve(
        self,
        capability_name: str,
    ) -> str:
        """
        Devuelve la herramienta asociada a una capacidad.
        """
        normalized_capability = self._normalize_name(
            capability_name
        )

        if normalized_capability not in self._capabilities:
            raise KeyError(
                "La capacidad "
                f"'{normalized_capability}' "
                "no está registrada."
            )

        tool_name = self._capabilities[
            normalized_capability
        ]

        self.event_bus.publish(
            "capability.resolved",
            {
                "capability": normalized_capability,
                "tool": tool_name,
            },
        )

        return tool_name

    def exists(
        self,
        capability_name: str,
    ) -> bool:
        """
        Verifica si una capacidad está registrada.
        """
        normalized_capability = self._normalize_name(
            capability_name
        )

        return (
            normalized_capability
            in self._capabilities
        )

    def remove(
        self,
        capability_name: str,
    ) -> None:
        """
        Elimina una capacidad registrada.
        """
        normalized_capability = self._normalize_name(
            capability_name
        )

        if normalized_capability not in self._capabilities:
            raise KeyError(
                "La capacidad "
                f"'{normalized_capability}' "
                "no está registrada."
            )

        tool_name = self._capabilities.pop(
            normalized_capability
        )

        self.event_bus.publish(
            "capability.removed",
            {
                "capability": normalized_capability,
                "tool": tool_name,
            },
        )

    def get_tool(
        self,
        capability_name: str,
    ) -> Optional[str]:
        """
        Devuelve la herramienta asociada o None.
        """
        normalized_capability = self._normalize_name(
            capability_name
        )

        return self._capabilities.get(
            normalized_capability
        )

    def list_capabilities(
        self,
    ) -> List[Dict[str, str]]:
        """
        Devuelve todas las capacidades registradas.
        """
        return [
            {
                "capability": capability_name,
                "tool": tool_name,
            }
            for capability_name, tool_name
            in sorted(self._capabilities.items())
        ]

    def list_names(self) -> List[str]:
        """
        Devuelve los nombres de las capacidades.
        """
        return sorted(
            self._capabilities.keys()
        )

    def count(self) -> int:
        """
        Devuelve la cantidad de capacidades registradas.
        """
        return len(self._capabilities)

    @staticmethod
    def _normalize_name(name: str) -> str:
        """
        Normaliza nombres de capacidades y herramientas.
        """
        normalized_name = name.strip().lower()

        if not normalized_name:
            raise ValueError(
                "El nombre no puede estar vacío."
            )

        return normalized_name