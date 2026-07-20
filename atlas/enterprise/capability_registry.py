from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence


class CapabilityStatus(str, Enum):
    """
    Estados operativos posibles de una capacidad.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


class CapabilityComplexity(str, Enum):
    """
    Nivel de complejidad de una capacidad.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CapabilityCategory(str, Enum):
    """
    Categorías principales de capacidades de Atlas AI OS.
    """

    EXECUTIVE = "executive"
    PLANNING = "planning"
    RESEARCH = "research"
    ENGINEERING = "engineering"
    SECURITY = "security"
    REVIEW = "review"
    OPERATIONS = "operations"
    KNOWLEDGE = "knowledge"
    GENERAL = "general"


@dataclass
class CapabilityProfile:
    """
    Definición empresarial de una capacidad de Atlas AI OS.
    """

    capability_id: str
    name: str
    description: str

    category: CapabilityCategory = CapabilityCategory.GENERAL
    complexity: CapabilityComplexity = CapabilityComplexity.MEDIUM
    status: CapabilityStatus = CapabilityStatus.ACTIVE

    dependencies: List[str] = field(
        default_factory=list
    )

    compatible_tools: List[str] = field(
        default_factory=list
    )

    recommended_llms: List[str] = field(
        default_factory=list
    )

    responsible_departments: List[str] = field(
        default_factory=list
    )

    agent_ids: List[str] = field(
        default_factory=list
    )

    tags: List[str] = field(
        default_factory=list
    )

    priority: int = 100
    enabled: bool = True

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    updated_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    def __post_init__(self) -> None:
        """
        Valida y normaliza la capacidad.
        """
        self.capability_id = self._normalize_identifier(
            self.capability_id
        )

        self.name = self.name.strip()
        self.description = self.description.strip()

        if not self.name:
            raise ValueError(
                "El nombre de la capacidad no puede estar vacío."
            )

        if not self.description:
            raise ValueError(
                "La descripción de la capacidad no puede estar vacía."
            )

        if self.priority < 0:
            raise ValueError(
                "La prioridad no puede ser negativa."
            )

        if not isinstance(
            self.category,
            CapabilityCategory,
        ):
            self.category = CapabilityCategory(
                self.category
            )

        if not isinstance(
            self.complexity,
            CapabilityComplexity,
        ):
            self.complexity = CapabilityComplexity(
                self.complexity
            )

        if not isinstance(
            self.status,
            CapabilityStatus,
        ):
            self.status = CapabilityStatus(
                self.status
            )

        self.dependencies = self._normalize_collection(
            self.dependencies
        )

        self.compatible_tools = self._normalize_collection(
            self.compatible_tools
        )

        self.recommended_llms = self._normalize_collection(
            self.recommended_llms
        )

        self.responsible_departments = self._normalize_collection(
            self.responsible_departments
        )

        self.agent_ids = self._normalize_collection(
            self.agent_ids
        )

        self.tags = self._normalize_collection(
            self.tags
        )

        if self.capability_id in self.dependencies:
            raise ValueError(
                "Una capacidad no puede depender de sí misma."
            )

    @property
    def is_operational(self) -> bool:
        """
        Indica si la capacidad puede utilizarse.
        """
        return (
            self.enabled
            and self.status
            in {
                CapabilityStatus.ACTIVE,
                CapabilityStatus.EXPERIMENTAL,
            }
        )

    @property
    def agent_count(self) -> int:
        """
        Cantidad de agentes que implementan la capacidad.
        """
        return len(
            self.agent_ids
        )

    def add_agent(
        self,
        agent_id: str,
    ) -> None:
        """
        Asigna un agente a la capacidad.
        """
        normalized_id = self._normalize_identifier(
            agent_id
        )

        if normalized_id not in self.agent_ids:
            self.agent_ids.append(
                normalized_id
            )
            self.agent_ids.sort()
            self.touch()

    def remove_agent(
        self,
        agent_id: str,
    ) -> bool:
        """
        Elimina un agente de la capacidad.
        """
        normalized_id = self._normalize_identifier(
            agent_id
        )

        if normalized_id not in self.agent_ids:
            return False

        self.agent_ids.remove(
            normalized_id
        )
        self.touch()

        return True

    def has_agent(
        self,
        agent_id: str,
    ) -> bool:
        """
        Comprueba si un agente implementa la capacidad.
        """
        normalized_id = self._normalize_identifier(
            agent_id
        )

        return normalized_id in self.agent_ids

    def add_dependency(
        self,
        capability_id: str,
    ) -> None:
        """
        Agrega una dependencia.
        """
        normalized_id = self._normalize_identifier(
            capability_id
        )

        if normalized_id == self.capability_id:
            raise ValueError(
                "Una capacidad no puede depender de sí misma."
            )

        if normalized_id not in self.dependencies:
            self.dependencies.append(
                normalized_id
            )
            self.dependencies.sort()
            self.touch()

    def remove_dependency(
        self,
        capability_id: str,
    ) -> bool:
        """
        Elimina una dependencia.
        """
        normalized_id = self._normalize_identifier(
            capability_id
        )

        if normalized_id not in self.dependencies:
            return False

        self.dependencies.remove(
            normalized_id
        )
        self.touch()

        return True

    def enable(self) -> None:
        """
        Habilita la capacidad.
        """
        self.enabled = True

        if self.status == CapabilityStatus.INACTIVE:
            self.status = CapabilityStatus.ACTIVE

        self.touch()

    def disable(self) -> None:
        """
        Deshabilita la capacidad.
        """
        self.enabled = False
        self.status = CapabilityStatus.INACTIVE
        self.touch()

    def set_status(
        self,
        status: CapabilityStatus,
    ) -> None:
        """
        Actualiza el estado operativo.
        """
        if not isinstance(
            status,
            CapabilityStatus,
        ):
            status = CapabilityStatus(
                status
            )

        self.status = status
        self.touch()

    def touch(self) -> None:
        """
        Actualiza la fecha de modificación.
        """
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la capacidad en un diccionario serializable.
        """
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "complexity": self.complexity.value,
            "status": self.status.value,
            "dependencies": list(
                self.dependencies
            ),
            "compatible_tools": list(
                self.compatible_tools
            ),
            "recommended_llms": list(
                self.recommended_llms
            ),
            "responsible_departments": list(
                self.responsible_departments
            ),
            "agent_ids": list(
                self.agent_ids
            ),
            "agent_count": self.agent_count,
            "tags": list(
                self.tags
            ),
            "priority": self.priority,
            "enabled": self.enabled,
            "is_operational": self.is_operational,
            "metadata": dict(
                self.metadata
            ),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "CapabilityProfile":
        """
        Construye una capacidad desde un diccionario.
        """
        return cls(
            capability_id=data["capability_id"],
            name=data["name"],
            description=data["description"],
            category=CapabilityCategory(
                data.get(
                    "category",
                    CapabilityCategory.GENERAL.value,
                )
            ),
            complexity=CapabilityComplexity(
                data.get(
                    "complexity",
                    CapabilityComplexity.MEDIUM.value,
                )
            ),
            status=CapabilityStatus(
                data.get(
                    "status",
                    CapabilityStatus.ACTIVE.value,
                )
            ),
            dependencies=data.get(
                "dependencies",
                [],
            ),
            compatible_tools=data.get(
                "compatible_tools",
                [],
            ),
            recommended_llms=data.get(
                "recommended_llms",
                [],
            ),
            responsible_departments=data.get(
                "responsible_departments",
                [],
            ),
            agent_ids=data.get(
                "agent_ids",
                [],
            ),
            tags=data.get(
                "tags",
                [],
            ),
            priority=data.get(
                "priority",
                100,
            ),
            enabled=data.get(
                "enabled",
                True,
            ),
            metadata=data.get(
                "metadata",
                {},
            ),
            created_at=data.get(
                "created_at",
                datetime.now().isoformat(),
            ),
            updated_at=data.get(
                "updated_at",
                datetime.now().isoformat(),
            ),
        )

    @staticmethod
    def _normalize_identifier(
        value: str,
    ) -> str:
        normalized = str(value).strip().lower()
        normalized = normalized.replace(
            " ",
            "-",
        )
        normalized = normalized.replace(
            "_",
            "-",
        )

        if not normalized:
            raise ValueError(
                "El identificador no puede estar vacío."
            )

        return normalized

    @classmethod
    def _normalize_collection(
        cls,
        values: Sequence[str],
    ) -> List[str]:
        return sorted(
            {
                cls._normalize_identifier(value)
                for value in values
                if str(value).strip()
            }
        )


class CapabilityRegistry:
    """
    Registro central de capacidades de Atlas AI OS.
    """

    def __init__(self) -> None:
        self._capabilities: Dict[
            str,
            CapabilityProfile,
        ] = {}

    def register(
        self,
        capability: CapabilityProfile,
        replace: bool = False,
    ) -> None:
        """
        Registra una capacidad.
        """
        if not isinstance(
            capability,
            CapabilityProfile,
        ):
            raise TypeError(
                "capability debe ser una instancia "
                "de CapabilityProfile."
            )

        capability_id = capability.capability_id

        if (
            capability_id in self._capabilities
            and not replace
        ):
            raise ValueError(
                f"La capacidad '{capability_id}' "
                "ya está registrada."
            )

        self._capabilities[
            capability_id
        ] = capability

    def register_many(
        self,
        capabilities: Sequence[CapabilityProfile],
        replace: bool = False,
    ) -> None:
        """
        Registra varias capacidades.
        """
        for capability in capabilities:
            self.register(
                capability=capability,
                replace=replace,
            )

    def get(
        self,
        capability_id: str,
    ) -> CapabilityProfile:
        """
        Obtiene una capacidad por identificador.
        """
        normalized_id = self._normalize_identifier(
            capability_id
        )

        if normalized_id not in self._capabilities:
            raise KeyError(
                f"La capacidad '{normalized_id}' "
                "no está registrada."
            )

        return self._capabilities[
            normalized_id
        ]

    def find(
        self,
        capability_id: str,
    ) -> Optional[CapabilityProfile]:
        """
        Busca una capacidad sin lanzar excepción.
        """
        normalized_id = self._normalize_identifier(
            capability_id
        )

        return self._capabilities.get(
            normalized_id
        )

    def contains(
        self,
        capability_id: str,
    ) -> bool:
        """
        Indica si una capacidad está registrada.
        """
        normalized_id = self._normalize_identifier(
            capability_id
        )

        return normalized_id in self._capabilities

    def remove(
        self,
        capability_id: str,
    ) -> CapabilityProfile:
        """
        Elimina y devuelve una capacidad.
        """
        normalized_id = self._normalize_identifier(
            capability_id
        )

        if normalized_id not in self._capabilities:
            raise KeyError(
                f"La capacidad '{normalized_id}' "
                "no está registrada."
            )

        for capability in self._capabilities.values():
            if normalized_id in capability.dependencies:
                raise ValueError(
                    f"No se puede eliminar '{normalized_id}' "
                    f"porque '{capability.capability_id}' depende de ella."
                )

        return self._capabilities.pop(
            normalized_id
        )

    def list_capabilities(
        self,
    ) -> List[CapabilityProfile]:
        """
        Devuelve todas las capacidades ordenadas.
        """
        return sorted(
            self._capabilities.values(),
            key=lambda capability: (
                capability.priority,
                capability.capability_id,
            ),
        )

    def list_items(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Devuelve todas las capacidades serializadas.
        """
        return [
            capability.to_dict()
            for capability in self.list_capabilities()
        ]

    def list_ids(self) -> List[str]:
        """
        Devuelve los identificadores registrados.
        """
        return sorted(
            self._capabilities.keys()
        )

    def count(self) -> int:
        """
        Devuelve la cantidad de capacidades.
        """
        return len(
            self._capabilities
        )

    def operational_capabilities(
        self,
    ) -> List[CapabilityProfile]:
        """
        Devuelve las capacidades operativas.
        """
        return [
            capability
            for capability in self.list_capabilities()
            if capability.is_operational
        ]

    def find_by_category(
        self,
        category: CapabilityCategory,
        operational_only: bool = False,
    ) -> List[CapabilityProfile]:
        """
        Busca capacidades por categoría.
        """
        if not isinstance(
            category,
            CapabilityCategory,
        ):
            category = CapabilityCategory(
                category
            )

        capabilities = [
            capability
            for capability in self._capabilities.values()
            if capability.category == category
        ]

        if operational_only:
            capabilities = [
                capability
                for capability in capabilities
                if capability.is_operational
            ]

        return self._sort_capabilities(
            capabilities
        )

    def find_by_department(
        self,
        department_id: str,
        operational_only: bool = False,
    ) -> List[CapabilityProfile]:
        """
        Busca capacidades por departamento responsable.
        """
        normalized_id = self._normalize_identifier(
            department_id
        )

        capabilities = [
            capability
            for capability in self._capabilities.values()
            if normalized_id
            in capability.responsible_departments
        ]

        if operational_only:
            capabilities = [
                capability
                for capability in capabilities
                if capability.is_operational
            ]

        return self._sort_capabilities(
            capabilities
        )

    def find_by_agent(
        self,
        agent_id: str,
        operational_only: bool = False,
    ) -> List[CapabilityProfile]:
        """
        Busca capacidades implementadas por un agente.
        """
        normalized_id = self._normalize_identifier(
            agent_id
        )

        capabilities = [
            capability
            for capability in self._capabilities.values()
            if normalized_id in capability.agent_ids
        ]

        if operational_only:
            capabilities = [
                capability
                for capability in capabilities
                if capability.is_operational
            ]

        return self._sort_capabilities(
            capabilities
        )

    def find_by_tool(
        self,
        tool_id: str,
        operational_only: bool = False,
    ) -> List[CapabilityProfile]:
        """
        Busca capacidades compatibles con una herramienta.
        """
        normalized_id = self._normalize_identifier(
            tool_id
        )

        capabilities = [
            capability
            for capability in self._capabilities.values()
            if normalized_id
            in capability.compatible_tools
        ]

        if operational_only:
            capabilities = [
                capability
                for capability in capabilities
                if capability.is_operational
            ]

        return self._sort_capabilities(
            capabilities
        )

    def assign_agent(
        self,
        capability_id: str,
        agent_id: str,
    ) -> CapabilityProfile:
        """
        Asigna un agente a una capacidad.
        """
        capability = self.get(
            capability_id
        )

        capability.add_agent(
            agent_id
        )

        return capability

    def unassign_agent(
        self,
        capability_id: str,
        agent_id: str,
    ) -> bool:
        """
        Retira un agente de una capacidad.
        """
        capability = self.get(
            capability_id
        )

        return capability.remove_agent(
            agent_id
        )

    def resolve_dependencies(
        self,
        capability_id: str,
    ) -> List[CapabilityProfile]:
        """
        Resuelve todas las dependencias de una capacidad.

        Devuelve las dependencias en orden de ejecución,
        desde las más profundas hasta la capacidad solicitada.
        """
        normalized_id = self._normalize_identifier(
            capability_id
        )

        visited: set[str] = set()
        visiting: set[str] = set()
        ordered: List[CapabilityProfile] = []

        def visit(current_id: str) -> None:
            if current_id in visiting:
                raise ValueError(
                    "Se detectó una dependencia circular "
                    f"en '{current_id}'."
                )

            if current_id in visited:
                return

            capability = self.get(
                current_id
            )

            visiting.add(
                current_id
            )

            for dependency_id in capability.dependencies:
                visit(
                    dependency_id
                )

            visiting.remove(
                current_id
            )
            visited.add(
                current_id
            )
            ordered.append(
                capability
            )

        visit(
            normalized_id
        )

        return ordered

    def validate_dependencies(
        self,
    ) -> Dict[str, Any]:
        """
        Valida dependencias faltantes y ciclos.
        """
        missing: Dict[str, List[str]] = {}
        cycles: List[str] = []

        for capability in self._capabilities.values():
            missing_dependencies = [
                dependency
                for dependency in capability.dependencies
                if dependency not in self._capabilities
            ]

            if missing_dependencies:
                missing[
                    capability.capability_id
                ] = missing_dependencies

        for capability_id in self._capabilities:
            try:
                self.resolve_dependencies(
                    capability_id
                )
            except ValueError as error:
                cycles.append(
                    str(error)
                )

        return {
            "valid": not missing and not cycles,
            "missing_dependencies": missing,
            "cycles": sorted(
                set(cycles)
            ),
        }

    def enable(
        self,
        capability_id: str,
    ) -> CapabilityProfile:
        """
        Habilita una capacidad.
        """
        capability = self.get(
            capability_id
        )

        capability.enable()

        return capability

    def disable(
        self,
        capability_id: str,
    ) -> CapabilityProfile:
        """
        Deshabilita una capacidad.
        """
        capability = self.get(
            capability_id
        )

        capability.disable()

        return capability

    def summary(self) -> Dict[str, Any]:
        """
        Devuelve un resumen del registro.
        """
        capabilities = list(
            self._capabilities.values()
        )

        operational = sum(
            1
            for capability in capabilities
            if capability.is_operational
        )

        experimental = sum(
            1
            for capability in capabilities
            if capability.status
            == CapabilityStatus.EXPERIMENTAL
        )

        deprecated = sum(
            1
            for capability in capabilities
            if capability.status
            == CapabilityStatus.DEPRECATED
        )

        assigned_agents = {
            agent_id
            for capability in capabilities
            for agent_id in capability.agent_ids
        }

        categories = sorted(
            {
                capability.category.value
                for capability in capabilities
            }
        )

        return {
            "total_capabilities": len(
                capabilities
            ),
            "operational_capabilities": operational,
            "experimental_capabilities": experimental,
            "deprecated_capabilities": deprecated,
            "assigned_unique_agents": len(
                assigned_agents
            ),
            "categories": categories,
            "category_count": len(
                categories
            ),
            "dependency_validation": (
                self.validate_dependencies()
            ),
        }

    def clear(self) -> None:
        """
        Elimina todas las capacidades.
        """
        self._capabilities.clear()

    @staticmethod
    def _sort_capabilities(
        capabilities: Sequence[CapabilityProfile],
    ) -> List[CapabilityProfile]:
        return sorted(
            capabilities,
            key=lambda capability: (
                capability.priority,
                capability.capability_id,
            ),
        )

    @staticmethod
    def _normalize_identifier(
        value: str,
    ) -> str:
        normalized = str(value).strip().lower()
        normalized = normalized.replace(
            " ",
            "-",
        )
        normalized = normalized.replace(
            "_",
            "-",
        )

        if not normalized:
            raise ValueError(
                "El identificador no puede estar vacío."
            )

        return normalized


def build_default_capabilities() -> List[CapabilityProfile]:
    """
    Construye el catálogo inicial de capacidades de Atlas AI OS.
    """
    return [
        CapabilityProfile(
            capability_id="general-reasoning",
            name="General Reasoning",
            description=(
                "Razonamiento general para interpretar "
                "y resolver tareas diversas."
            ),
            category=CapabilityCategory.GENERAL,
            complexity=CapabilityComplexity.MEDIUM,
            responsible_departments=[
                "planning",
                "operations",
            ],
            recommended_llms=[
                "mock",
            ],
            priority=10,
        ),
        CapabilityProfile(
            capability_id="intent-analysis",
            name="Intent Analysis",
            description=(
                "Identificación de la intención principal "
                "de una solicitud."
            ),
            category=CapabilityCategory.PLANNING,
            complexity=CapabilityComplexity.MEDIUM,
            dependencies=[
                "general-reasoning",
            ],
            responsible_departments=[
                "planning",
            ],
            priority=20,
        ),
        CapabilityProfile(
            capability_id="task-planning",
            name="Task Planning",
            description=(
                "Descomposición de objetivos en tareas "
                "y pasos ejecutables."
            ),
            category=CapabilityCategory.PLANNING,
            complexity=CapabilityComplexity.HIGH,
            dependencies=[
                "intent-analysis",
            ],
            responsible_departments=[
                "planning",
            ],
            priority=30,
        ),
        CapabilityProfile(
            capability_id="workflow-planning",
            name="Workflow Planning",
            description=(
                "Diseño y organización de flujos "
                "multiagente."
            ),
            category=CapabilityCategory.PLANNING,
            complexity=CapabilityComplexity.HIGH,
            dependencies=[
                "task-planning",
            ],
            responsible_departments=[
                "planning",
            ],
            priority=40,
        ),
        CapabilityProfile(
            capability_id="research",
            name="Research",
            description=(
                "Investigación estructurada de fuentes "
                "y evidencia."
            ),
            category=CapabilityCategory.RESEARCH,
            complexity=CapabilityComplexity.HIGH,
            dependencies=[
                "general-reasoning",
            ],
            responsible_departments=[
                "research",
            ],
            priority=50,
        ),
        CapabilityProfile(
            capability_id="information-analysis",
            name="Information Analysis",
            description=(
                "Evaluación y comparación de información "
                "procedente de múltiples fuentes."
            ),
            category=CapabilityCategory.RESEARCH,
            complexity=CapabilityComplexity.HIGH,
            dependencies=[
                "research",
            ],
            responsible_departments=[
                "research",
            ],
            priority=60,
        ),
        CapabilityProfile(
            capability_id="coding",
            name="Coding",
            description=(
                "Implementación de componentes de software."
            ),
            category=CapabilityCategory.ENGINEERING,
            complexity=CapabilityComplexity.HIGH,
            compatible_tools=[
                "file-info",
                "calculator",
            ],
            responsible_departments=[
                "engineering",
            ],
            priority=70,
        ),
        CapabilityProfile(
            capability_id="debugging",
            name="Debugging",
            description=(
                "Diagnóstico y corrección de errores "
                "de software."
            ),
            category=CapabilityCategory.ENGINEERING,
            complexity=CapabilityComplexity.HIGH,
            dependencies=[
                "coding",
            ],
            responsible_departments=[
                "engineering",
            ],
            priority=80,
        ),
        CapabilityProfile(
            capability_id="quality-control",
            name="Quality Control",
            description=(
                "Evaluación de calidad y consistencia "
                "de resultados."
            ),
            category=CapabilityCategory.REVIEW,
            complexity=CapabilityComplexity.MEDIUM,
            dependencies=[
                "general-reasoning",
            ],
            responsible_departments=[
                "review",
            ],
            priority=90,
        ),
        CapabilityProfile(
            capability_id="security-analysis",
            name="Security Analysis",
            description=(
                "Análisis de riesgos y controles "
                "de seguridad."
            ),
            category=CapabilityCategory.SECURITY,
            complexity=CapabilityComplexity.CRITICAL,
            dependencies=[
                "information-analysis",
            ],
            responsible_departments=[
                "security",
            ],
            priority=100,
        ),
        CapabilityProfile(
            capability_id="monitoring",
            name="Monitoring",
            description=(
                "Seguimiento del estado operativo "
                "de servicios y procesos."
            ),
            category=CapabilityCategory.OPERATIONS,
            complexity=CapabilityComplexity.MEDIUM,
            responsible_departments=[
                "operations",
            ],
            priority=110,
        ),
        CapabilityProfile(
            capability_id="knowledge-management",
            name="Knowledge Management",
            description=(
                "Administración de memoria, contexto "
                "y activos de conocimiento."
            ),
            category=CapabilityCategory.KNOWLEDGE,
            complexity=CapabilityComplexity.HIGH,
            dependencies=[
                "information-analysis",
            ],
            responsible_departments=[
                "knowledge",
            ],
            priority=120,
        ),
    ]
