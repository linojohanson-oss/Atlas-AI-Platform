from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """Contrato base para todas las herramientas de Atlas."""

    name: str = "base-tool"
    description: str = "Herramienta base."
    version: str = "1.0.0"

    @abstractmethod
    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """Ejecuta la herramienta y devuelve un resultado estructurado."""
        raise NotImplementedError

    def information(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
        }
