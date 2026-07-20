from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentStatus(str, Enum):
    """
    Estados operativos posibles de un agente.
    """

    ONLINE = "online"
    BUSY = "busy"
    IDLE = "idle"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class AgentLevel(str, Enum):
    """
    Nivel profesional u organizacional del agente.
    """

    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    DIRECTOR = "director"
    EXECUTIVE = "executive"


class AuthorityLevel(str, Enum):
    """
    Nivel de autoridad dentro de Atlas AI OS.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AgentMetrics:
    """
    Métricas operativas acumuladas de un agente.
    """

    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0

    total_execution_time_seconds: float = 0.0
    average_execution_time_seconds: float = 0.0

    success_rate: float = 0.0
    confidence_score: float = 0.0
    quality_score: float = 0.0

    last_execution_at: Optional[str] = None
    last_error: Optional[str] = None

    def register_success(
        self,
        execution_time_seconds: float,
        confidence_score: Optional[float] = None,
        quality_score: Optional[float] = None,
    ) -> None:
        """
        Registra una ejecución exitosa.
        """
        self.total_executions += 1
        self.successful_executions += 1

        self._register_execution_time(
            execution_time_seconds
        )

        if confidence_score is not None:
            self.confidence_score = self._normalize_score(
                confidence_score
            )

        if quality_score is not None:
            self.quality_score = self._normalize_score(
                quality_score
            )

        self.last_execution_at = datetime.now().isoformat()
        self.last_error = None

        self._recalculate_success_rate()

    def register_failure(
        self,
        execution_time_seconds: float,
        error: str,
    ) -> None:
        """
        Registra una ejecución fallida.
        """
        self.total_executions += 1
        self.failed_executions += 1

        self._register_execution_time(
            execution_time_seconds
        )

        self.last_execution_at = datetime.now().isoformat()
        self.last_error = str(error)

        self._recalculate_success_rate()

    def _register_execution_time(
        self,
        execution_time_seconds: float,
    ) -> None:
        execution_time = max(
            0.0,
            float(execution_time_seconds),
        )

        self.total_execution_time_seconds += execution_time

        if self.total_executions > 0:
            self.average_execution_time_seconds = (
                self.total_execution_time_seconds
                / self.total_executions
            )

    def _recalculate_success_rate(self) -> None:
        if self.total_executions == 0:
            self.success_rate = 0.0
            return

        self.success_rate = (
            self.successful_executions
            / self.total_executions
        ) * 100

    @staticmethod
    def _normalize_score(
        score: float,
    ) -> float:
        """
        Normaliza una métrica al rango 0-100.
        """
        return max(
            0.0,
            min(100.0, float(score)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte las métricas en un diccionario serializable.
        """
        return {
            "total_executions": self.total_executions,
            "successful_executions": (
                self.successful_executions
            ),
            "failed_executions": self.failed_executions,
            "total_execution_time_seconds": round(
                self.total_execution_time_seconds,
                6,
            ),
            "average_execution_time_seconds": round(
                self.average_execution_time_seconds,
                6,
            ),
            "success_rate": round(
                self.success_rate,
                2,
            ),
            "confidence_score": round(
                self.confidence_score,
                2,
            ),
            "quality_score": round(
                self.quality_score,
                2,
            ),
            "last_execution_at": self.last_execution_at,
            "last_error": self.last_error,
        }


@dataclass
class AgentProfile:
    """
    Perfil empresarial de un agente de Atlas AI OS.

    Representa su identidad, posición organizacional,
    capacidades, permisos, estado y métricas.
    """

    agent_id: str
    name: str
    description: str

    department: str
    role: str

    level: AgentLevel = AgentLevel.MID
    authority: AuthorityLevel = AuthorityLevel.MEDIUM
    status: AgentStatus = AgentStatus.ONLINE

    capabilities: List[str] = field(
        default_factory=list
    )

    tools: List[str] = field(
        default_factory=list
    )

    llm_providers: List[str] = field(
        default_factory=list
    )

    permissions: List[str] = field(
        default_factory=list
    )

    tags: List[str] = field(
        default_factory=list
    )

    priority: int = 100
    enabled: bool = True

    current_load: int = 0
    max_concurrent_tasks: int = 1

    metrics: AgentMetrics = field(
        default_factory=AgentMetrics
    )

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
        Valida y normaliza el perfil después de crearlo.
        """
        self.agent_id = self._normalize_identifier(
            self.agent_id
        )

        self.name = self.name.strip()
        self.description = self.description.strip()
        self.department = self._normalize_text(
            self.department
        )
        self.role = self._normalize_text(
            self.role
        )

        if not self.name:
            raise ValueError(
                "El nombre del agente no puede estar vacío."
            )

        if not self.description:
            raise ValueError(
                "La descripción del agente no puede estar vacía."
            )

        if not self.department:
            raise ValueError(
                "El departamento del agente no puede estar vacío."
            )

        if not self.role:
            raise ValueError(
                "El rol del agente no puede estar vacío."
            )

        if self.priority < 0:
            raise ValueError(
                "La prioridad no puede ser negativa."
            )

        if self.max_concurrent_tasks < 1:
            raise ValueError(
                "max_concurrent_tasks debe ser mayor o igual a 1."
            )

        self.capabilities = self._normalize_collection(
            self.capabilities
        )

        self.tools = self._normalize_collection(
            self.tools
        )

        self.llm_providers = self._normalize_collection(
            self.llm_providers
        )

        self.permissions = self._normalize_collection(
            self.permissions
        )

        self.tags = self._normalize_collection(
            self.tags
        )

    @property
    def is_available(self) -> bool:
        """
        Indica si el agente puede aceptar una nueva tarea.
        """
        return (
            self.enabled
            and self.status
            in {
                AgentStatus.ONLINE,
                AgentStatus.IDLE,
            }
            and self.current_load
            < self.max_concurrent_tasks
        )

    @property
    def load_percentage(self) -> float:
        """
        Devuelve el porcentaje de carga operativa.
        """
        if self.max_concurrent_tasks <= 0:
            return 100.0

        percentage = (
            self.current_load
            / self.max_concurrent_tasks
        ) * 100

        return min(
            100.0,
            max(0.0, percentage),
        )

    def has_capability(
        self,
        capability: str,
    ) -> bool:
        """
        Comprueba si el agente posee una capacidad.
        """
        normalized_capability = self._normalize_identifier(
            capability
        )

        return normalized_capability in self.capabilities

    def has_tool(
        self,
        tool_name: str,
    ) -> bool:
        """
        Comprueba si el agente tiene acceso a una herramienta.
        """
        normalized_tool = self._normalize_identifier(
            tool_name
        )

        return normalized_tool in self.tools

    def has_permission(
        self,
        permission: str,
    ) -> bool:
        """
        Comprueba si el agente posee un permiso.
        """
        normalized_permission = self._normalize_identifier(
            permission
        )

        return normalized_permission in self.permissions

    def start_task(self) -> None:
        """
        Incrementa la carga y marca al agente como ocupado.
        """
        if not self.enabled:
            raise RuntimeError(
                f"El agente '{self.agent_id}' está deshabilitado."
            )

        if self.current_load >= self.max_concurrent_tasks:
            raise RuntimeError(
                f"El agente '{self.agent_id}' alcanzó "
                "su carga máxima."
            )

        self.current_load += 1
        self.status = AgentStatus.BUSY
        self.touch()

    def finish_task(self) -> None:
        """
        Libera una tarea activa.
        """
        self.current_load = max(
            0,
            self.current_load - 1,
        )

        if self.current_load == 0:
            self.status = AgentStatus.IDLE

        self.touch()

    def set_status(
        self,
        status: AgentStatus,
    ) -> None:
        """
        Modifica el estado operativo.
        """
        self.status = status
        self.touch()

    def enable(self) -> None:
        """
        Habilita el agente.
        """
        self.enabled = True

        if self.status == AgentStatus.OFFLINE:
            self.status = AgentStatus.IDLE

        self.touch()

    def disable(self) -> None:
        """
        Deshabilita el agente.
        """
        self.enabled = False
        self.status = AgentStatus.OFFLINE
        self.touch()

    def touch(self) -> None:
        """
        Actualiza la fecha de modificación.
        """
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte el perfil en un diccionario serializable.
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "department": self.department,
            "role": self.role,
            "level": self.level.value,
            "authority": self.authority.value,
            "status": self.status.value,
            "capabilities": list(self.capabilities),
            "tools": list(self.tools),
            "llm_providers": list(self.llm_providers),
            "permissions": list(self.permissions),
            "tags": list(self.tags),
            "priority": self.priority,
            "enabled": self.enabled,
            "current_load": self.current_load,
            "max_concurrent_tasks": (
                self.max_concurrent_tasks
            ),
            "is_available": self.is_available,
            "load_percentage": round(
                self.load_percentage,
                2,
            ),
            "metrics": self.metrics.to_dict(),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "AgentProfile":
        """
        Crea un perfil a partir de un diccionario.
        """
        metrics_data = data.get(
            "metrics",
            {},
        )

        metrics = AgentMetrics(
            total_executions=metrics_data.get(
                "total_executions",
                0,
            ),
            successful_executions=metrics_data.get(
                "successful_executions",
                0,
            ),
            failed_executions=metrics_data.get(
                "failed_executions",
                0,
            ),
            total_execution_time_seconds=metrics_data.get(
                "total_execution_time_seconds",
                0.0,
            ),
            average_execution_time_seconds=metrics_data.get(
                "average_execution_time_seconds",
                0.0,
            ),
            success_rate=metrics_data.get(
                "success_rate",
                0.0,
            ),
            confidence_score=metrics_data.get(
                "confidence_score",
                0.0,
            ),
            quality_score=metrics_data.get(
                "quality_score",
                0.0,
            ),
            last_execution_at=metrics_data.get(
                "last_execution_at"
            ),
            last_error=metrics_data.get(
                "last_error"
            ),
        )

        return cls(
            agent_id=data["agent_id"],
            name=data["name"],
            description=data["description"],
            department=data["department"],
            role=data["role"],
            level=AgentLevel(
                data.get(
                    "level",
                    AgentLevel.MID.value,
                )
            ),
            authority=AuthorityLevel(
                data.get(
                    "authority",
                    AuthorityLevel.MEDIUM.value,
                )
            ),
            status=AgentStatus(
                data.get(
                    "status",
                    AgentStatus.ONLINE.value,
                )
            ),
            capabilities=data.get(
                "capabilities",
                [],
            ),
            tools=data.get(
                "tools",
                [],
            ),
            llm_providers=data.get(
                "llm_providers",
                [],
            ),
            permissions=data.get(
                "permissions",
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
            current_load=data.get(
                "current_load",
                0,
            ),
            max_concurrent_tasks=data.get(
                "max_concurrent_tasks",
                1,
            ),
            metrics=metrics,
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
        normalized = normalized.replace(" ", "-")
        normalized = normalized.replace("_", "-")

        if not normalized:
            raise ValueError(
                "El identificador no puede estar vacío."
            )

        return normalized

    @staticmethod
    def _normalize_text(
        value: str,
    ) -> str:
        return str(value).strip()

    @classmethod
    def _normalize_collection(
        cls,
        values: List[str],
    ) -> List[str]:
        normalized_values = {
            cls._normalize_identifier(value)
            for value in values
            if str(value).strip()
        }

        return sorted(normalized_values)