"""
Atlas AI OS - Enterprise Layer

Componentes empresariales para organizar agentes, departamentos,
capacidades y selección inteligente.
"""

from atlas.enterprise.department import Department

from atlas.enterprise.agent_profile import (
    AgentLevel,
    AgentMetrics,
    AgentProfile,
    AgentStatus,
    AuthorityLevel,
)

from atlas.enterprise.enterprise_agent_registry import (
    EnterpriseAgentRegistry,
)

from atlas.enterprise.department_registry import (
    DepartmentProfile,
    DepartmentRegistry,
    DepartmentStatus,
    build_default_departments,
)

from atlas.enterprise.agent_selector import (
    AgentScoreBreakdown,
    AgentSelectionCriteria,
    AgentSelectionResult,
    AgentSelector,
    SelectionStrategy,
)

from atlas.enterprise.capability_registry import (
    CapabilityCategory,
    CapabilityComplexity,
    CapabilityProfile,
    CapabilityRegistry,
    CapabilityStatus,
    build_default_capabilities,
)

from atlas.enterprise.organization import (
    AtlasOrganization,
)

from atlas.enterprise.organization_builder import (
    AtlasOrganizationBuilder,
    BuilderConfig,
)
from atlas.enterprise.department_runtime import (
    DepartmentRuntime,
    DepartmentRuntimeStatus,
    DepartmentTask,
    DepartmentTaskStatus,
)

__all__ = [
    # Agent Profile
    "AgentLevel",
    "AgentMetrics",
    "AgentProfile",
    "AgentStatus",
    "AuthorityLevel",

    # Agent Registry
    "EnterpriseAgentRegistry",

    # Departments
    "DepartmentProfile",
    "DepartmentRegistry",
    "DepartmentStatus",
    "build_default_departments",
    # Department Runtime
    "DepartmentRuntime",
    "DepartmentRuntimeStatus",
    "DepartmentTask",
    "DepartmentTaskStatus",

    # Agent Selector
    "AgentScoreBreakdown",
    "AgentSelectionCriteria",
    "AgentSelectionResult",
    "AgentSelector",
    "SelectionStrategy",

    # Capabilities
    "CapabilityCategory",
    "CapabilityComplexity",
    "CapabilityProfile",
    "CapabilityRegistry",
    "CapabilityStatus",
    "build_default_capabilities",

    # Organization
    "AtlasOrganization",
    "AtlasOrganizationBuilder",
    "BuilderConfig",

    "Department",


]