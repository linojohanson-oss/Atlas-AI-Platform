from typing import Any, Dict, List

from atlas.agents.base_agent import BaseAgent
from atlas.kernel.event_bus import EventBus


class AgentManager:
    """
    Administra los agentes disponibles en Atlas AI Platform.

    Permite registrar, consultar, eliminar y ejecutar agentes.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """
        Registra un agente.
        """
        agent_name = self._normalize_name(agent.name)

        if agent_name in self._agents:
            raise ValueError(
                f"El agente '{agent_name}' ya está registrado."
            )

        self._agents[agent_name] = agent

        self.event_bus.publish(
            "agent.registered",
            {
                "agent": agent_name,
                "description": agent.description,
                "capabilities": list(agent.capabilities),
            },
        )

    def get(self, agent_name: str) -> BaseAgent:
        """
        Obtiene un agente por nombre.
        """
        normalized_name = self._normalize_name(agent_name)

        if normalized_name not in self._agents:
            raise KeyError(
                f"El agente '{normalized_name}' no está registrado."
            )

        return self._agents[normalized_name]

    def remove(self, agent_name: str) -> None:
        """
        Elimina un agente.
        """
        normalized_name = self._normalize_name(agent_name)

        if normalized_name not in self._agents:
            raise KeyError(
                f"El agente '{normalized_name}' no está registrado."
            )

        del self._agents[normalized_name]

        self.event_bus.publish(
            "agent.removed",
            {
                "agent": normalized_name,
            },
        )

    def execute(
        self,
        agent_name: str,
        task: str,
    ) -> Dict[str, Any]:
        """
        Ejecuta una tarea utilizando un agente registrado.
        """
        agent = self.get(agent_name)

        self.event_bus.publish(
            "agent.started",
            {
                "agent": agent.name,
                "task": task,
            },
        )

        try:
            result = agent.execute(task)

            self.event_bus.publish(
                "agent.completed",
                result,
            )

            return result

        except Exception as exc:
            self.event_bus.publish(
                "agent.failed",
                {
                    "agent": agent.name,
                    "task": task,
                    "error": str(exc),
                },
            )
            raise

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        Devuelve información de todos los agentes.
        """
        return [
            agent.information()
            for agent in self._agents.values()
        ]

    def list_names(self) -> List[str]:
        """
        Devuelve los nombres de los agentes registrados.
        """
        return sorted(self._agents.keys())

    def count(self) -> int:
        """
        Devuelve la cantidad de agentes registrados.
        """
        return len(self._agents)

    @staticmethod
    def _normalize_name(agent_name: str) -> str:
        normalized_name = agent_name.strip().lower()

        if not normalized_name:
            raise ValueError(
                "El nombre del agente no puede estar vacío."
            )

        return normalized_name
