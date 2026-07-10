from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgent(ABC):
    """
    Clase base para todos los agentes de Atlas AI Platform.
    """

    name: str = "base-agent"
    description: str = "Agente base de Atlas."
    capabilities = []

    @abstractmethod
    def execute(self, task: str) -> Dict[str, Any]:
        """
        Ejecuta una tarea y devuelve un resultado estructurado.
        """
        raise NotImplementedError

    def information(self) -> Dict[str, Any]:
        """
        Devuelve información pública del agente.
        """
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": list(self.capabilities),
        }
