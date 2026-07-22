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
    def execute(
        self,
        task: Any,
    ) -> Dict[str, Any]:
        """
        Ejecuta una tarea y devuelve un resultado estructurado.

        La tarea puede ser texto plano o una estructura compleja,
        por ejemplo un diccionario generado por WorkflowEngine.
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