from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from atlas.enterprise.agent_profile import AgentProfile
from atlas.enterprise.agent_selector import (
    AgentSelectionCriteria,
    AgentSelectionResult,
)
from atlas.enterprise.organization import AtlasOrganization
from atlas.enterprise.organization_builder import (
    AtlasOrganizationBuilder,
    BuilderConfig,
)


class OrganizationManagerStatus(str, Enum):
    """
    Estados posibles del administrador organizacional.
    """

    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class OrganizationManagerConfig:
    """
    Configuración del puente entre el Kernel y la capa Enterprise.
    """

    organization_name: str = "Atlas AI OS"
    auto_initialize: bool = False
    validate_on_initialize: bool = True
    include_default_departments: bool = True
    include_default_capabilities: bool = True
    include_default_agents: bool = True
    replace_existing: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class OrganizationManager:
    """
    Puente oficial entre Atlas Kernel y Atlas Enterprise.

    Encapsula la creación, inicialización, consulta, selección de agentes,
    validación y cierre de AtlasOrganization.

    El Kernel debería interactuar con esta clase y no con los registros
    empresariales internos de forma directa.
    """

    def __init__(
        self,
        config: Optional[OrganizationManagerConfig] = None,
        organization: Optional[AtlasOrganization] = None,
    ) -> None:
        self.config = config or OrganizationManagerConfig()

        self._organization: Optional[AtlasOrganization] = organization
        self._status = (
            OrganizationManagerStatus.READY
            if organization is not None
            else OrganizationManagerStatus.CREATED
        )

        self._created_at = datetime.now().isoformat()
        self._initialized_at: Optional[str] = None
        self._stopped_at: Optional[str] = None
        self._last_error: Optional[str] = None

        if organization is not None:
            self._initialized_at = datetime.now().isoformat()

        if self.config.auto_initialize and organization is None:
            self.initialize()

    # ============================================================
    # Propiedades
    # ============================================================

    @property
    def status(self) -> OrganizationManagerStatus:
        return self._status

    @property
    def organization(self) -> AtlasOrganization:
        """
        Devuelve la organización activa.
        """
        self._ensure_ready()

        assert self._organization is not None
        return self._organization

    @property
    def is_ready(self) -> bool:
        return (
            self._status == OrganizationManagerStatus.READY
            and self._organization is not None
        )

    @property
    def is_initialized(self) -> bool:
        return self._organization is not None

    # ============================================================
    # Ciclo de vida
    # ============================================================

    def initialize(
        self,
        force: bool = False,
    ) -> AtlasOrganization:
        """
        Construye e inicializa la organización Enterprise.

        Si ya está inicializada, devuelve la instancia existente.
        Use force=True para reconstruirla.
        """
        if self.is_ready and not force:
            assert self._organization is not None
            return self._organization

        self._status = OrganizationManagerStatus.INITIALIZING
        self._last_error = None

        try:
            builder_config = BuilderConfig(
                organization_name=self.config.organization_name,
                include_default_departments=(
                    self.config.include_default_departments
                ),
                include_default_capabilities=(
                    self.config.include_default_capabilities
                ),
                include_default_agents=(
                    self.config.include_default_agents
                ),
                validate_on_build=(
                    self.config.validate_on_initialize
                ),
                replace_existing=self.config.replace_existing,
                metadata=dict(self.config.metadata),
            )

            builder = AtlasOrganizationBuilder(builder_config)
            self._organization = builder.build()

            if self.config.validate_on_initialize:
                validation = self._organization.validate()

                if not validation["valid"]:
                    details = "; ".join(validation["errors"])
                    raise ValueError(
                        "La organización inicializada no es válida: "
                        + details
                    )

            self._status = OrganizationManagerStatus.READY
            self._initialized_at = datetime.now().isoformat()
            self._stopped_at = None

            return self._organization

        except Exception as error:
            self._status = OrganizationManagerStatus.ERROR
            self._last_error = str(error)
            raise

    def shutdown(self) -> None:
        """
        Detiene el administrador y libera la organización activa.
        """
        if self._status == OrganizationManagerStatus.STOPPED:
            return

        self._status = OrganizationManagerStatus.STOPPING
        self._organization = None
        self._status = OrganizationManagerStatus.STOPPED
        self._stopped_at = datetime.now().isoformat()

    def restart(self) -> AtlasOrganization:
        """
        Reinicia completamente la organización.
        """
        self.shutdown()
        return self.initialize(force=True)

    # ============================================================
    # Consultas principales
    # ============================================================

    def get_agent(
        self,
        agent_id: str,
    ) -> AgentProfile:
        return self.organization.get_agent(agent_id)

    def get_planner(self) -> AgentProfile:
        """
        Devuelve el perfil empresarial del Planner Agent.
        """
        return self.get_agent("planner-agent")

    def get_general(self) -> AgentProfile:
        """
        Devuelve el perfil empresarial del General Agent.
        """
        return self.get_agent("general-agent")

    def list_agents(self) -> List[AgentProfile]:
        return self.organization.agents.list_profiles()

    def get_agent_capabilities(
        self,
        agent_id: str,
    ) -> List[Any]:
        return self.organization.get_agent_capabilities(agent_id)

    # ============================================================
    # Selección organizacional
    # ============================================================

    def select_agent(
        self,
        criteria: AgentSelectionCriteria,
    ) -> AgentSelectionResult:
        """
        Selecciona el agente más adecuado.
        """
        return self.organization.select_agent(criteria)

    def select_by_capability(
        self,
        capability_id: str,
    ) -> AgentSelectionResult:
        """
        Selecciona un agente para una capacidad concreta.
        """
        return self.organization.select_by_capability(capability_id)

    def rank_agents(
        self,
        criteria: AgentSelectionCriteria,
    ) -> List[AgentSelectionResult]:
        """
        Devuelve el ranking de agentes elegibles.
        """
        return self.organization.rank_agents(criteria)

    # ============================================================
    # Gestión operativa
    # ============================================================

    def start_agent_task(
        self,
        agent_id: str,
    ) -> AgentProfile:
        return self.organization.start_agent_task(agent_id)

    def finish_agent_task(
        self,
        agent_id: str,
        success: bool = True,
        duration_seconds: Optional[float] = None,
        quality_score: Optional[float] = None,
        confidence_score: Optional[float] = None,
    ) -> AgentProfile:
        return self.organization.finish_agent_task(
            agent_id=agent_id,
            success=success,
            duration_seconds=duration_seconds,
            quality_score=quality_score,
            confidence_score=confidence_score,
        )

    def register_agent(
        self,
        agent: AgentProfile,
        replace: bool = False,
    ) -> None:
        self.organization.register_agent(
            agent=agent,
            replace=replace,
            sync_capabilities=True,
        )

    def remove_agent(
        self,
        agent_id: str,
    ) -> AgentProfile:
        return self.organization.remove_agent(agent_id)

    def assign_agent_capability(
        self,
        agent_id: str,
        capability_id: str,
    ) -> None:
        self.organization.assign_agent_capability(
            agent_id=agent_id,
            capability_id=capability_id,
        )

    def unassign_agent_capability(
        self,
        agent_id: str,
        capability_id: str,
    ) -> bool:
        return self.organization.unassign_agent_capability(
            agent_id=agent_id,
            capability_id=capability_id,
        )

    # ============================================================
    # Diagnóstico
    # ============================================================

    def validate(self) -> Dict[str, Any]:
        """
        Valida la organización activa.
        """
        return self.organization.validate()

    def summary(self) -> Dict[str, Any]:
        """
        Devuelve un resumen seguro del administrador.
        """
        manager_summary = {
            "status": self._status.value,
            "is_ready": self.is_ready,
            "is_initialized": self.is_initialized,
            "created_at": self._created_at,
            "initialized_at": self._initialized_at,
            "stopped_at": self._stopped_at,
            "last_error": self._last_error,
            "organization_name": self.config.organization_name,
        }

        if self._organization is None:
            manager_summary["organization"] = None
            return manager_summary

        manager_summary["organization"] = (
            self._organization.summary()
        )

        return manager_summary

    def health(self) -> Dict[str, Any]:
        """
        Devuelve un diagnóstico operativo simplificado.
        """
        if not self.is_ready:
            return {
                "healthy": False,
                "status": self._status.value,
                "reason": (
                    self._last_error
                    or "La organización no está inicializada."
                ),
            }

        validation = self.validate()

        return {
            "healthy": validation["valid"],
            "status": self._status.value,
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "agents": self.organization.agents.count(),
            "departments": self.organization.departments.count(),
            "capabilities": self.organization.capabilities.count(),
        }

    # ============================================================
    # Utilidades internas
    # ============================================================

    def _ensure_ready(self) -> None:
        if not self.is_ready:
            raise RuntimeError(
                "OrganizationManager no está listo. "
                "Ejecute initialize() antes de utilizarlo."
            )
