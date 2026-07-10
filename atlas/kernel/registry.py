from typing import Any, Dict, List


class ComponentRegistry:
    """
    Registro central de componentes de Atlas AI Platform.

    Permite registrar agentes, herramientas, proveedores LLM,
    memorias y otros componentes del sistema.
    """

    def __init__(self) -> None:
        self._components: Dict[str, Any] = {}

    def register(self, name: str, component: Any) -> None:
        """Registra un componente con un nombre único."""
        normalized_name = name.strip().lower()

        if not normalized_name:
            raise ValueError(
                "El nombre del componente no puede estar vacío."
            )

        if normalized_name in self._components:
            raise ValueError(
                f"El componente '{normalized_name}' ya está registrado."
            )

        self._components[normalized_name] = component

    def get(self, name: str) -> Any:
        """Obtiene un componente registrado."""
        normalized_name = name.strip().lower()

        if normalized_name not in self._components:
            raise KeyError(
                f"El componente '{normalized_name}' no está registrado."
            )

        return self._components[normalized_name]

    def exists(self, name: str) -> bool:
        """Verifica si un componente está registrado."""
        return name.strip().lower() in self._components

    def remove(self, name: str) -> None:
        """Elimina un componente del registro."""
        normalized_name = name.strip().lower()

        if normalized_name not in self._components:
            raise KeyError(
                f"El componente '{normalized_name}' no está registrado."
            )

        del self._components[normalized_name]

    def list_names(self) -> List[str]:
        """Devuelve los nombres de todos los componentes."""
        return sorted(self._components.keys())

    def count(self) -> int:
        """Devuelve la cantidad total de componentes."""
        return len(self._components)
