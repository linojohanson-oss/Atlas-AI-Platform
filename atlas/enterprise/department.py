"""
Atlas AI OS - Enterprise Department

Define departamentos empresariales capaces de agrupar agentes
especializados y seleccionar el agente más apropiado para una tarea.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Department:
    """
    Representa un departamento dentro de una organización Atlas AI.

    Un departamento agrupa agentes especializados y permite administrar
    su registro, eliminación y selección.
    """

    name: str
    description: str = ""
    department_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.name = self.name.strip()

        if not self.name:
            raise ValueError("El nombre del departamento no puede estar vacío.")

        if self.department_id is None:
            self.department_id = self._generate_department_id(self.name)

        self._agents: Dict[str, Any] = {}

    @staticmethod
    def _generate_department_id(name: str) -> str:
        """
        Genera un identificador normalizado para el departamento.
        """
        return (
            name.strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
        )

    @property
    def agents(self) -> List[Any]:
        """
        Devuelve la lista de agentes registrados.
        """
        return list(self._agents.values())

    @property
    def agent_count(self) -> int:
        """
        Devuelve la cantidad de agentes registrados.
        """
        return len(self._agents)

    def add_agent(self, agent: Any, agent_id: Optional[str] = None) -> str:
        """
        Registra un agente dentro del departamento.

        El identificador puede proporcionarse manualmente o inferirse
        desde los atributos comunes del agente.
        """
        resolved_agent_id = agent_id or self._resolve_agent_id(agent)

        if not resolved_agent_id:
            raise ValueError(
                "No fue posible determinar el identificador del agente."
            )

        if resolved_agent_id in self._agents:
            raise ValueError(
                f"El agente '{resolved_agent_id}' ya está registrado "
                f"en el departamento '{self.name}'."
            )

        self._agents[resolved_agent_id] = agent
        return resolved_agent_id

    def remove_agent(self, agent_id: str) -> Any:
        """
        Elimina un agente del departamento.
        """
        if agent_id not in self._agents:
            raise KeyError(
                f"El agente '{agent_id}' no existe "
                f"en el departamento '{self.name}'."
            )

        return self._agents.pop(agent_id)

    def get_agent(self, agent_id: str) -> Optional[Any]:
        """
        Obtiene un agente por su identificador.
        """
        return self._agents.get(agent_id)

    def has_agent(self, agent_id: str) -> bool:
        """
        Indica si un agente está registrado.
        """
        return agent_id in self._agents

    def select_agent(self, capability: Optional[str] = None) -> Optional[Any]:
        """
        Selecciona un agente del departamento.

        Si se proporciona una capacidad, busca un agente que la declare
        en sus atributos `capabilities` o `skills`.

        Si no encuentra coincidencias, devuelve el primer agente disponible.
        """
        if not self._agents:
            return None

        if capability:
            normalized_capability = capability.strip().lower()

            for agent in self._agents.values():
                capabilities = getattr(agent, "capabilities", None)
                skills = getattr(agent, "skills", None)

                declared_capabilities = capabilities or skills or []

                normalized_values = {
                    str(value).strip().lower()
                    for value in declared_capabilities
                }

                if normalized_capability in normalized_values:
                    return agent

        return next(iter(self._agents.values()))

    def clear_agents(self) -> None:
        """
        Elimina todos los agentes del departamento.
        """
        self._agents.clear()

    def to_dict(self) -> Dict[str, Any]:
        """
        Devuelve una representación serializable del departamento.
        """
        return {
            "department_id": self.department_id,
            "name": self.name,
            "description": self.description,
            "agent_count": self.agent_count,
            "agents": list(self._agents.keys()),
            "metadata": self.metadata,
        }

    def _resolve_agent_id(self, agent: Any) -> Optional[str]:
        """
        Intenta determinar el identificador de un agente.
        """
        possible_attributes = (
            "agent_id",
            "name",
            "id",
        )

        for attribute in possible_attributes:
            value = getattr(agent, attribute, None)

            if value:
                return self._generate_department_id(str(value))

        return None

    def __len__(self) -> int:
        return self.agent_count

    def __contains__(self, agent_id: str) -> bool:
        return self.has_agent(agent_id)

    def __repr__(self) -> str:
        return (
            f"Department("
            f"name='{self.name}', "
            f"department_id='{self.department_id}', "
            f"agents={self.agent_count}"
            f")"
        )