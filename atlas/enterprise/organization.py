from typing import Any, Dict, List, Optional, Sequence

from atlas.enterprise.agent_profile import AgentProfile
from atlas.enterprise.agent_selector import (
    AgentSelectionCriteria,
    AgentSelectionResult,
    AgentSelector,
)
from atlas.enterprise.capability_registry import (
    CapabilityProfile,
    CapabilityRegistry,
    build_default_capabilities,
)
from atlas.enterprise.department_registry import (
    DepartmentProfile,
    DepartmentRegistry,
    build_default_departments,
)
from atlas.enterprise.enterprise_agent_registry import (
    EnterpriseAgentRegistry,
)


class AtlasOrganization:
    """
    Coordinador central de la capa Enterprise de Atlas AI OS.

    Une departamentos, capacidades, perfiles de agentes y selección
    inteligente bajo una única interfaz organizacional.
    """

    def __init__(
        self,
        name: str = "Atlas AI OS",
        departments: Optional[DepartmentRegistry] = None,
        capabilities: Optional[CapabilityRegistry] = None,
        agents: Optional[EnterpriseAgentRegistry] = None,
        load_defaults: bool = True,
    ) -> None:
        self.name = name.strip() or "Atlas AI OS"

        self.departments = departments or DepartmentRegistry()
        self.capabilities = capabilities or CapabilityRegistry()
        self.agents = agents or EnterpriseAgentRegistry()

        self.selector = AgentSelector(self.agents)

        if load_defaults:
            self._load_defaults()

    def _load_defaults(self) -> None:
        """
        Carga departamentos y capacidades iniciales sin duplicar registros.
        """
        for department in build_default_departments():
            if not self.departments.contains(department.department_id):
                self.departments.register(department)

        for capability in build_default_capabilities():
            if not self.capabilities.contains(capability.capability_id):
                self.capabilities.register(capability)

    # ============================================================
    # Departamentos
    # ============================================================

    def register_department(
        self,
        department: DepartmentProfile,
        replace: bool = False,
    ) -> None:
        self.departments.register(
            department=department,
            replace=replace,
        )

    def get_department(
        self,
        department_id: str,
    ) -> DepartmentProfile:
        return self.departments.get(department_id)

    # ============================================================
    # Capacidades
    # ============================================================

    def register_capability(
        self,
        capability: CapabilityProfile,
        replace: bool = False,
    ) -> None:
        self.capabilities.register(
            capability=capability,
            replace=replace,
        )

    def get_capability(
        self,
        capability_id: str,
    ) -> CapabilityProfile:
        return self.capabilities.get(capability_id)

    # ============================================================
    # Agentes
    # ============================================================

    def register_agent(
        self,
        agent: AgentProfile,
        replace: bool = False,
        sync_capabilities: bool = True,
    ) -> None:
        """
        Registra un agente y sincroniza sus capacidades con el catálogo.
        """
        department_id = self._normalize_identifier(agent.department)

        if not self.departments.contains(department_id):
            raise ValueError(
                f"El departamento '{department_id}' no está registrado."
            )

        unknown_capabilities = [
            capability_id
            for capability_id in agent.capabilities
            if not self.capabilities.contains(capability_id)
        ]

        if unknown_capabilities:
            raise ValueError(
                "El agente contiene capacidades no registradas: "
                + ", ".join(sorted(unknown_capabilities))
            )

        self.agents.register(
            agent,
            replace=replace,
        )

        if sync_capabilities:
            self._sync_agent_capabilities(agent)

    def register_agents(
        self,
        agents: Sequence[AgentProfile],
        replace: bool = False,
        sync_capabilities: bool = True,
    ) -> None:
        for agent in agents:
            self.register_agent(
                agent=agent,
                replace=replace,
                sync_capabilities=sync_capabilities,
            )

    def get_agent(
        self,
        agent_id: str,
    ) -> AgentProfile:
        return self.agents.get(agent_id)

    def remove_agent(
        self,
        agent_id: str,
    ) -> AgentProfile:
        """
        Elimina el agente y sus asignaciones en capacidades.
        """
        agent = self.agents.get(agent_id)

        for capability_id in list(agent.capabilities):
            capability = self.capabilities.find(capability_id)

            if capability is not None:
                capability.remove_agent(agent.agent_id)

        return self.agents.remove(agent_id)

    # ============================================================
    # Asignaciones
    # ============================================================

    def assign_agent_capability(
        self,
        agent_id: str,
        capability_id: str,
    ) -> None:
        """
        Asigna una capacidad en ambas direcciones:
        AgentProfile y CapabilityProfile.
        """
        agent = self.agents.get(agent_id)
        capability = self.capabilities.get(capability_id)

        normalized_capability = capability.capability_id

        if normalized_capability not in agent.capabilities:
            agent.capabilities.append(normalized_capability)
            agent.capabilities.sort()

        capability.add_agent(agent.agent_id)

    def unassign_agent_capability(
        self,
        agent_id: str,
        capability_id: str,
    ) -> bool:
        """
        Retira una capacidad del agente y del catálogo.
        """
        agent = self.agents.get(agent_id)
        capability = self.capabilities.get(capability_id)

        removed = False

        if capability.capability_id in agent.capabilities:
            agent.capabilities.remove(capability.capability_id)
            removed = True

        if capability.remove_agent(agent.agent_id):
            removed = True

        return removed

    def get_agent_capabilities(
        self,
        agent_id: str,
    ) -> List[CapabilityProfile]:
        """
        Devuelve los perfiles de capacidades asignados a un agente.
        """
        agent = self.agents.get(agent_id)

        return [
            self.capabilities.get(capability_id)
            for capability_id in agent.capabilities
            if self.capabilities.contains(capability_id)
        ]

    def get_capability_agents(
        self,
        capability_id: str,
    ) -> List[AgentProfile]:
        """
        Devuelve los agentes asignados a una capacidad.
        """
        capability = self.capabilities.get(capability_id)

        return [
            self.agents.get(agent_id)
            for agent_id in capability.agent_ids
            if self.agents.contains(agent_id)
        ]

    def _sync_agent_capabilities(
        self,
        agent: AgentProfile,
    ) -> None:
        for capability_id in agent.capabilities:
            self.capabilities.assign_agent(
                capability_id=capability_id,
                agent_id=agent.agent_id,
            )

    # ============================================================
    # Selección
    # ============================================================

    def select_agent(
        self,
        criteria: AgentSelectionCriteria,
    ) -> AgentSelectionResult:
        """
        Selecciona el mejor agente disponible según los criterios.
        """
        return self.selector.select(criteria)

    def rank_agents(
        self,
        criteria: AgentSelectionCriteria,
    ) -> List[AgentSelectionResult]:
        """
        Devuelve el ranking de agentes candidatos.
        """
        return self.selector.rank(criteria)

    def select_by_capability(
        self,
        capability_id: str,
    ) -> AgentSelectionResult:
        """
        Selecciona un agente para una capacidad registrada.
        """
        capability = self.capabilities.get(capability_id)

        if not capability.is_operational:
            raise ValueError(
                f"La capacidad '{capability.capability_id}' no está operativa."
            )

        return self.selector.select_by_capability(
            capability.capability_id
        )

    # ============================================================
    # Estado operativo
    # ============================================================

    def start_agent_task(
        self,
        agent_id: str,
    ) -> AgentProfile:
        """
        Marca el inicio de una tarea para el agente.
        """
        return self.agents.start_task(agent_id)

    def finish_agent_task(
        self,
        agent_id: str,
        success: bool = True,
        duration_seconds: Optional[float] = None,
        quality_score: Optional[float] = None,
        confidence_score: Optional[float] = None,
    ) -> AgentProfile:
        """
        Finaliza una tarea y, cuando es posible, actualiza métricas.
        """
        agent = self.agents.finish_task(agent_id)

        metrics = getattr(agent, "metrics", None)

        if metrics is not None:
            if success and hasattr(metrics, "register_success"):
                metrics.register_success(
                    duration_seconds or 0.0,
                    quality_score or 0.0,
                    confidence_score or 0.0,
                )
            elif not success and hasattr(metrics, "register_failure"):
                metrics.register_failure(
                    duration_seconds or 0.0
                )

        return agent

    # ============================================================
    # Validación
    # ============================================================

    def validate(self) -> Dict[str, Any]:
        """
        Comprueba la consistencia de toda la organización.
        """
        errors: List[str] = []
        warnings: List[str] = []

        dependency_validation = (
            self.capabilities.validate_dependencies()
        )

        if not dependency_validation["valid"]:
            errors.append(
                "El catálogo de capacidades contiene "
                "dependencias inválidas."
            )

        for agent in self.agents.list_profiles():
            department_id = self._normalize_identifier(
                agent.department
            )

            if not self.departments.contains(department_id):
                errors.append(
                    f"El agente '{agent.agent_id}' pertenece al "
                    f"departamento inexistente '{department_id}'."
                )

            for capability_id in agent.capabilities:
                capability = self.capabilities.find(capability_id)

                if capability is None:
                    errors.append(
                        f"El agente '{agent.agent_id}' utiliza la "
                        f"capacidad inexistente '{capability_id}'."
                    )
                    continue

                if agent.agent_id not in capability.agent_ids:
                    warnings.append(
                        f"La capacidad '{capability_id}' no contiene "
                        f"la asignación inversa de '{agent.agent_id}'."
                    )

        for capability in self.capabilities.list_capabilities():
            for agent_id in capability.agent_ids:
                agent = self.agents.find(agent_id)

                if agent is None:
                    errors.append(
                        f"La capacidad '{capability.capability_id}' "
                        f"referencia al agente inexistente '{agent_id}'."
                    )
                    continue

                if capability.capability_id not in agent.capabilities:
                    warnings.append(
                        f"El agente '{agent_id}' no contiene la "
                        f"asignación inversa de "
                        f"'{capability.capability_id}'."
                    )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "dependency_validation": dependency_validation,
        }

    # ============================================================
    # Resumen
    # ============================================================

    def summary(self) -> Dict[str, Any]:
        """
        Devuelve un resumen consolidado de AtlasOrganization.
        """
        validation = self.validate()

        return {
            "organization": self.name,
            "departments": self.departments.summary(),
            "capabilities": self.capabilities.summary(),
            "agents": self.agents.summary(),
            "validation": validation,
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Devuelve la organización completa en formato serializable.
        """
        return {
            "name": self.name,
            "departments": [
                department.to_dict()
                for department in self.departments.list_departments()
            ],
            "capabilities": self.capabilities.list_items(),
            "agents": [
                agent.to_dict()
                for agent in self.agents.list_profiles()
            ],
            "summary": self.summary(),
        }

    @staticmethod
    def _normalize_identifier(
        value: str,
    ) -> str:
        normalized = str(value).strip().lower()
        normalized = normalized.replace(" ", "-")
        normalized = normalized.replace("_", "-")

        if not normalized:
            raise ValueError(
                "El identificador no puede estar vacío."
            )

        return normalized
