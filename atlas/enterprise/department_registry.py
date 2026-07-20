from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class DepartmentStatus(str, Enum):
    """Estados operativos posibles de un departamento."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    RESTRICTED = "restricted"


@dataclass
class DepartmentProfile:
    """Perfil organizacional de un departamento de Atlas AI OS."""

    department_id: str
    name: str
    description: str
    director_agent_id: Optional[str] = None
    responsibilities: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    agent_ids: List[str] = field(default_factory=list)
    status: DepartmentStatus = DepartmentStatus.ACTIVE
    priority: int = 100
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self) -> None:
        self.department_id = self._normalize_identifier(self.department_id)
        self.name = self.name.strip()
        self.description = self.description.strip()

        if not self.name:
            raise ValueError("El nombre del departamento no puede estar vacío.")
        if not self.description:
            raise ValueError("La descripción del departamento no puede estar vacía.")
        if self.priority < 0:
            raise ValueError("La prioridad no puede ser negativa.")

        if self.director_agent_id:
            self.director_agent_id = self._normalize_identifier(self.director_agent_id)

        self.responsibilities = self._normalize_collection(self.responsibilities)
        self.capabilities = self._normalize_collection(self.capabilities)
        self.agent_ids = self._normalize_collection(self.agent_ids)

    @property
    def agent_count(self) -> int:
        return len(self.agent_ids)

    @property
    def is_operational(self) -> bool:
        return self.enabled and self.status == DepartmentStatus.ACTIVE

    def add_agent(self, agent_id: str) -> None:
        normalized_id = self._normalize_identifier(agent_id)
        if normalized_id not in self.agent_ids:
            self.agent_ids.append(normalized_id)
            self.agent_ids.sort()
            self.touch()

    def remove_agent(self, agent_id: str) -> bool:
        normalized_id = self._normalize_identifier(agent_id)
        if normalized_id not in self.agent_ids:
            return False

        self.agent_ids.remove(normalized_id)
        if self.director_agent_id == normalized_id:
            self.director_agent_id = None
        self.touch()
        return True

    def has_agent(self, agent_id: str) -> bool:
        return self._normalize_identifier(agent_id) in self.agent_ids

    def has_capability(self, capability: str) -> bool:
        return self._normalize_identifier(capability) in self.capabilities

    def set_director(self, agent_id: Optional[str], auto_assign: bool = True) -> None:
        if agent_id is None:
            self.director_agent_id = None
            self.touch()
            return

        normalized_id = self._normalize_identifier(agent_id)
        self.director_agent_id = normalized_id
        if auto_assign:
            self.add_agent(normalized_id)
        self.touch()

    def enable(self) -> None:
        self.enabled = True
        if self.status == DepartmentStatus.INACTIVE:
            self.status = DepartmentStatus.ACTIVE
        self.touch()

    def disable(self) -> None:
        self.enabled = False
        self.status = DepartmentStatus.INACTIVE
        self.touch()

    def set_status(self, status: DepartmentStatus) -> None:
        if not isinstance(status, DepartmentStatus):
            status = DepartmentStatus(status)
        self.status = status
        self.touch()

    def touch(self) -> None:
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "department_id": self.department_id,
            "name": self.name,
            "description": self.description,
            "director_agent_id": self.director_agent_id,
            "responsibilities": list(self.responsibilities),
            "capabilities": list(self.capabilities),
            "agent_ids": list(self.agent_ids),
            "agent_count": self.agent_count,
            "status": self.status.value,
            "enabled": self.enabled,
            "is_operational": self.is_operational,
            "priority": self.priority,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DepartmentProfile":
        return cls(
            department_id=data["department_id"],
            name=data["name"],
            description=data["description"],
            director_agent_id=data.get("director_agent_id"),
            responsibilities=data.get("responsibilities", []),
            capabilities=data.get("capabilities", []),
            agent_ids=data.get("agent_ids", []),
            status=DepartmentStatus(data.get("status", DepartmentStatus.ACTIVE.value)),
            priority=data.get("priority", 100),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )

    @staticmethod
    def _normalize_identifier(value: str) -> str:
        normalized = str(value).strip().lower().replace(" ", "-").replace("_", "-")
        if not normalized:
            raise ValueError("El identificador no puede estar vacío.")
        return normalized

    @classmethod
    def _normalize_collection(cls, values: List[str]) -> List[str]:
        return sorted(
            {
                cls._normalize_identifier(value)
                for value in values
                if str(value).strip()
            }
        )


class DepartmentRegistry:
    """Registro central de departamentos de Atlas AI OS."""

    def __init__(self) -> None:
        self._departments: Dict[str, DepartmentProfile] = {}

    def register(self, department: DepartmentProfile, replace: bool = False) -> None:
        if not isinstance(department, DepartmentProfile):
            raise TypeError("department debe ser una instancia de DepartmentProfile.")

        department_id = department.department_id
        if department_id in self._departments and not replace:
            raise ValueError(f"El departamento '{department_id}' ya está registrado.")
        self._departments[department_id] = department

    def register_many(self, departments: List[DepartmentProfile], replace: bool = False) -> None:
        for department in departments:
            self.register(department=department, replace=replace)

    def get(self, department_id: str) -> DepartmentProfile:
        normalized_id = self._normalize_identifier(department_id)
        if normalized_id not in self._departments:
            raise KeyError(f"El departamento '{normalized_id}' no está registrado.")
        return self._departments[normalized_id]

    def find(self, department_id: str) -> Optional[DepartmentProfile]:
        return self._departments.get(self._normalize_identifier(department_id))

    def contains(self, department_id: str) -> bool:
        return self._normalize_identifier(department_id) in self._departments

    def remove(self, department_id: str) -> DepartmentProfile:
        normalized_id = self._normalize_identifier(department_id)
        if normalized_id not in self._departments:
            raise KeyError(f"El departamento '{normalized_id}' no está registrado.")
        return self._departments.pop(normalized_id)

    def list_departments(self) -> List[DepartmentProfile]:
        return sorted(
            self._departments.values(),
            key=lambda department: (department.priority, department.department_id),
        )

    def list_items(self) -> List[Dict[str, Any]]:
        return [department.to_dict() for department in self.list_departments()]

    def list_ids(self) -> List[str]:
        return sorted(self._departments.keys())

    def count(self) -> int:
        return len(self._departments)

    def operational_departments(self) -> List[DepartmentProfile]:
        return [department for department in self.list_departments() if department.is_operational]

    def find_by_capability(
        self,
        capability: str,
        operational_only: bool = False,
    ) -> List[DepartmentProfile]:
        normalized_capability = self._normalize_identifier(capability)
        departments = [
            department
            for department in self._departments.values()
            if department.has_capability(normalized_capability)
        ]
        if operational_only:
            departments = [department for department in departments if department.is_operational]
        return sorted(
            departments,
            key=lambda department: (department.priority, department.department_id),
        )

    def find_by_agent(self, agent_id: str) -> List[DepartmentProfile]:
        normalized_id = self._normalize_identifier(agent_id)
        return sorted(
            [
                department
                for department in self._departments.values()
                if department.has_agent(normalized_id)
            ],
            key=lambda department: (department.priority, department.department_id),
        )

    def assign_agent(self, department_id: str, agent_id: str) -> DepartmentProfile:
        department = self.get(department_id)
        department.add_agent(agent_id)
        return department

    def unassign_agent(self, department_id: str, agent_id: str) -> bool:
        return self.get(department_id).remove_agent(agent_id)

    def set_director(
        self,
        department_id: str,
        agent_id: Optional[str],
        auto_assign: bool = True,
    ) -> DepartmentProfile:
        department = self.get(department_id)
        department.set_director(agent_id=agent_id, auto_assign=auto_assign)
        return department

    def enable(self, department_id: str) -> DepartmentProfile:
        department = self.get(department_id)
        department.enable()
        return department

    def disable(self, department_id: str) -> DepartmentProfile:
        department = self.get(department_id)
        department.disable()
        return department

    def summary(self) -> Dict[str, Any]:
        departments = list(self._departments.values())
        total_agents = len(
            {
                agent_id
                for department in departments
                for agent_id in department.agent_ids
            }
        )
        capabilities = sorted(
            {
                capability
                for department in departments
                for capability in department.capabilities
            }
        )
        active = sum(
            1 for department in departments if department.status == DepartmentStatus.ACTIVE
        )
        operational = sum(1 for department in departments if department.is_operational)
        with_director = sum(1 for department in departments if department.director_agent_id)

        return {
            "total_departments": len(departments),
            "active_departments": active,
            "operational_departments": operational,
            "departments_with_director": with_director,
            "assigned_unique_agents": total_agents,
            "capabilities": capabilities,
            "capability_count": len(capabilities),
        }

    def clear(self) -> None:
        self._departments.clear()

    @staticmethod
    def _normalize_identifier(value: str) -> str:
        normalized = str(value).strip().lower().replace(" ", "-").replace("_", "-")
        if not normalized:
            raise ValueError("El identificador no puede estar vacío.")
        return normalized


def build_default_departments() -> List[DepartmentProfile]:
    """Construye la estructura departamental inicial de Atlas AI OS."""

    return [
        DepartmentProfile(
            department_id="executive",
            name="Executive",
            description="Dirección estratégica y gobierno general de Atlas AI OS.",
            responsibilities=["strategic-governance", "policy-definition", "executive-decisions"],
            capabilities=["governance", "decision-making", "organization-control"],
            priority=10,
        ),
        DepartmentProfile(
            department_id="planning",
            name="Planning",
            description="Planificación de tareas, resolución de intención y diseño de flujos de trabajo.",
            responsibilities=["task-planning", "workflow-design", "intent-analysis"],
            capabilities=["task-planning", "workflow-planning", "general-reasoning"],
            priority=20,
        ),
        DepartmentProfile(
            department_id="research",
            name="Research",
            description="Investigación, análisis de fuentes y generación de conocimiento.",
            responsibilities=["research", "source-analysis", "knowledge-discovery"],
            capabilities=["research", "information-analysis", "knowledge-synthesis"],
            priority=30,
        ),
        DepartmentProfile(
            department_id="engineering",
            name="Engineering",
            description="Diseño, construcción, prueba y mantenimiento de componentes de software.",
            responsibilities=["software-development", "system-design", "testing"],
            capabilities=["coding", "debugging", "architecture-design"],
            priority=40,
        ),
        DepartmentProfile(
            department_id="security",
            name="Security",
            description="Control de permisos, riesgos, políticas y seguridad operativa.",
            responsibilities=["security-control", "risk-analysis", "permission-review"],
            capabilities=["security-analysis", "risk-management", "policy-enforcement"],
            priority=50,
        ),
        DepartmentProfile(
            department_id="review",
            name="Review",
            description="Validación de calidad, revisión crítica y aprobación de resultados.",
            responsibilities=["quality-review", "result-validation", "compliance-check"],
            capabilities=["review", "quality-control", "validation"],
            priority=60,
        ),
        DepartmentProfile(
            department_id="operations",
            name="Operations",
            description="Ejecución operativa, monitoreo y continuidad de servicios.",
            responsibilities=["task-execution", "system-monitoring", "service-continuity"],
            capabilities=["operations", "monitoring", "incident-response"],
            priority=70,
        ),
        DepartmentProfile(
            department_id="knowledge",
            name="Knowledge",
            description="Administración de memoria, contexto y activos de conocimiento.",
            responsibilities=["knowledge-management", "memory-management", "context-maintenance"],
            capabilities=["knowledge-management", "memory-retrieval", "context-analysis"],
            priority=80,
        ),
    ]
