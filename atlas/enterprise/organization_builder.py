from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from atlas.enterprise.agent_profile import (
    AgentLevel,
    AgentMetrics,
    AgentProfile,
    AgentStatus,
    AuthorityLevel,
)
from atlas.enterprise.capability_registry import (
    CapabilityProfile,
    build_default_capabilities,
)
from atlas.enterprise.department_registry import (
    DepartmentProfile,
    build_default_departments,
)
from atlas.enterprise.organization import AtlasOrganization


@dataclass
class BuilderConfig:
    """
    Configuración del constructor organizacional.
    """

    organization_name: str = "Atlas AI OS"
    include_default_departments: bool = True
    include_default_capabilities: bool = True
    include_default_agents: bool = True
    validate_on_build: bool = True
    replace_existing: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class AtlasOrganizationBuilder:
    """
    Constructor oficial de la organización Enterprise de Atlas AI OS.

    Permite crear una organización completa mediante una interfaz fluida,
    agregar componentes personalizados y validar la estructura antes de
    entregarla al Kernel.
    """

    def __init__(
        self,
        config: Optional[BuilderConfig] = None,
    ) -> None:
        self.config = config or BuilderConfig()

        self._departments: List[DepartmentProfile] = []
        self._capabilities: List[CapabilityProfile] = []
        self._agents: List[AgentProfile] = []

        self._use_default_departments = (
            self.config.include_default_departments
        )
        self._use_default_capabilities = (
            self.config.include_default_capabilities
        )
        self._use_default_agents = (
            self.config.include_default_agents
        )

    # ============================================================
    # Configuración fluida
    # ============================================================

    def named(
        self,
        organization_name: str,
    ) -> "AtlasOrganizationBuilder":
        name = str(organization_name).strip()

        if not name:
            raise ValueError(
                "El nombre de la organización no puede estar vacío."
            )

        self.config.organization_name = name
        return self

    def with_validation(
        self,
        enabled: bool = True,
    ) -> "AtlasOrganizationBuilder":
        self.config.validate_on_build = bool(enabled)
        return self

    def with_replace_existing(
        self,
        enabled: bool = True,
    ) -> "AtlasOrganizationBuilder":
        self.config.replace_existing = bool(enabled)
        return self

    def with_default_departments(
        self,
        enabled: bool = True,
    ) -> "AtlasOrganizationBuilder":
        self._use_default_departments = bool(enabled)
        return self

    def with_default_capabilities(
        self,
        enabled: bool = True,
    ) -> "AtlasOrganizationBuilder":
        self._use_default_capabilities = bool(enabled)
        return self

    def with_default_agents(
        self,
        enabled: bool = True,
    ) -> "AtlasOrganizationBuilder":
        self._use_default_agents = bool(enabled)
        return self

    # ============================================================
    # Componentes personalizados
    # ============================================================

    def add_department(
        self,
        department: DepartmentProfile,
    ) -> "AtlasOrganizationBuilder":
        if not isinstance(department, DepartmentProfile):
            raise TypeError(
                "department debe ser una instancia de DepartmentProfile."
            )

        self._departments.append(department)
        return self

    def add_departments(
        self,
        departments: Sequence[DepartmentProfile],
    ) -> "AtlasOrganizationBuilder":
        for department in departments:
            self.add_department(department)

        return self

    def add_capability(
        self,
        capability: CapabilityProfile,
    ) -> "AtlasOrganizationBuilder":
        if not isinstance(capability, CapabilityProfile):
            raise TypeError(
                "capability debe ser una instancia de CapabilityProfile."
            )

        self._capabilities.append(capability)
        return self

    def add_capabilities(
        self,
        capabilities: Sequence[CapabilityProfile],
    ) -> "AtlasOrganizationBuilder":
        for capability in capabilities:
            self.add_capability(capability)

        return self

    def add_agent(
        self,
        agent: AgentProfile,
    ) -> "AtlasOrganizationBuilder":
        if not isinstance(agent, AgentProfile):
            raise TypeError(
                "agent debe ser una instancia de AgentProfile."
            )

        self._agents.append(agent)
        return self

    def add_agents(
        self,
        agents: Sequence[AgentProfile],
    ) -> "AtlasOrganizationBuilder":
        for agent in agents:
            self.add_agent(agent)

        return self

    # ============================================================
    # Agentes por defecto
    # ============================================================

    @staticmethod
    def default_agents() -> List[AgentProfile]:
        """
        Crea los perfiles empresariales iniciales de Atlas AI OS.
        """
        planner_metrics = AgentMetrics()
        general_metrics = AgentMetrics()

        return [
            AgentProfile(
                agent_id="planner-agent",
                name="Planner Agent",
                description=(
                    "Agente responsable de interpretar objetivos, "
                    "diseñar planes y coordinar flujos de trabajo."
                ),
                department="planning",
                role="planner",
                status=AgentStatus.IDLE,
                level=AgentLevel.SENIOR,
                authority=AuthorityLevel.HIGH,
                capabilities=[
                    "general-reasoning",
                    "intent-analysis",
                    "task-planning",
                    "workflow-planning",
                ],
                tools=[
                    "calculator",
                    "file-info",
                ],
                llm_providers=[
                    "mock",
                ],
                permissions=[
                    "plan-workflows",
                    "select-agents",
                    "delegate-tasks",
                ],
                metrics=planner_metrics,
                priority=20,
                max_concurrent_tasks=2,
                enabled=True,
            ),
            AgentProfile(
                agent_id="general-agent",
                name="General Agent",
                description=(
                    "Agente generalista para razonamiento, análisis "
                    "y ejecución de tareas operativas."
                ),
                department="operations",
                role="generalist",
                status=AgentStatus.IDLE,
                level=AgentLevel.MID,
                authority=AuthorityLevel.MEDIUM,
                capabilities=[
                    "general-reasoning",
                    "monitoring",
                ],
                tools=[
                    "calculator",
                    "file-info",
                ],
                llm_providers=[
                    "mock",
                ],
                permissions=[
                    "execute-tasks",
                    "use-tools",
                ],
                metrics=general_metrics,
                priority=50,
                max_concurrent_tasks=2,
                enabled=True,
            ),
        ]

    # ============================================================
    # Construcción
    # ============================================================

    def build(self) -> AtlasOrganization:
        """
        Construye y devuelve una organización lista para operar.
        """
        organization = AtlasOrganization(
            name=self.config.organization_name,
            load_defaults=False,
        )

        departments = self._collect_departments()
        capabilities = self._collect_capabilities()
        agents = self._collect_agents()

        for department in departments:
            organization.register_department(
                department=department,
                replace=self.config.replace_existing,
            )

        for capability in capabilities:
            organization.register_capability(
                capability=capability,
                replace=self.config.replace_existing,
            )

        for agent in agents:
            organization.register_agent(
                agent=agent,
                replace=self.config.replace_existing,
                sync_capabilities=True,
            )

        if self.config.validate_on_build:
            validation = organization.validate()

            if not validation["valid"]:
                details = "; ".join(validation["errors"])
                raise ValueError(
                    "La organización construida no es válida: "
                    + details
                )

        return organization

    @classmethod
    def build_default(
        cls,
        organization_name: str = "Atlas AI OS",
        validate: bool = True,
    ) -> AtlasOrganization:
        """
        Construye la organización predeterminada en una sola llamada.
        """
        config = BuilderConfig(
            organization_name=organization_name,
            include_default_departments=True,
            include_default_capabilities=True,
            include_default_agents=True,
            validate_on_build=validate,
        )

        return cls(config).build()

    # ============================================================
    # Validación previa
    # ============================================================

    def validate(self) -> Dict[str, Any]:
        """
        Construye temporalmente la organización y devuelve su validación.
        """
        original = self.config.validate_on_build

        try:
            self.config.validate_on_build = False
            organization = self.build()
            return organization.validate()
        finally:
            self.config.validate_on_build = original

    def summary(self) -> Dict[str, Any]:
        """
        Devuelve un resumen previo de lo que construirá el builder.
        """
        departments = self._collect_departments()
        capabilities = self._collect_capabilities()
        agents = self._collect_agents()

        return {
            "organization_name": self.config.organization_name,
            "departments": len(departments),
            "capabilities": len(capabilities),
            "agents": len(agents),
            "department_ids": sorted(
                department.department_id
                for department in departments
            ),
            "capability_ids": sorted(
                capability.capability_id
                for capability in capabilities
            ),
            "agent_ids": sorted(
                agent.agent_id
                for agent in agents
            ),
            "validate_on_build": self.config.validate_on_build,
            "replace_existing": self.config.replace_existing,
        }

    # ============================================================
    # Utilidades internas
    # ============================================================

    def _collect_departments(self) -> List[DepartmentProfile]:
        items: List[DepartmentProfile] = []

        if self._use_default_departments:
            items.extend(build_default_departments())

        items.extend(self._departments)

        return self._deduplicate(
            items=items,
            key_name="department_id",
        )

    def _collect_capabilities(self) -> List[CapabilityProfile]:
        items: List[CapabilityProfile] = []

        if self._use_default_capabilities:
            items.extend(build_default_capabilities())

        items.extend(self._capabilities)

        return self._deduplicate(
            items=items,
            key_name="capability_id",
        )

    def _collect_agents(self) -> List[AgentProfile]:
        items: List[AgentProfile] = []

        if self._use_default_agents:
            items.extend(self.default_agents())

        items.extend(self._agents)

        return self._deduplicate(
            items=items,
            key_name="agent_id",
        )

    @staticmethod
    def _deduplicate(
        items: Sequence[Any],
        key_name: str,
    ) -> List[Any]:
        """
        Elimina duplicados conservando la última definición.
        """
        indexed: Dict[str, Any] = {}

        for item in items:
            key = getattr(item, key_name)
            indexed[str(key)] = item

        return list(indexed.values())
