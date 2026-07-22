from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from time import perf_counter
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import uuid4

from atlas.enterprise.agent_selector import (
    AgentSelectionCriteria,
    AgentSelectionResult,
    SelectionStrategy,
)
from atlas.enterprise.department_registry import DepartmentProfile

if TYPE_CHECKING:
    from atlas.kernel.agent_manager import AgentManager
    from atlas.kernel.event_bus import EventBus
    from atlas.kernel.organization_manager import OrganizationManager


class DepartmentRuntimeStatus(str, Enum):
    """
    Estados posibles del runtime departamental.
    """

    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class DepartmentTaskStatus(str, Enum):
    """
    Estados posibles de una tarea departamental.
    """

    CREATED = "created"
    SELECTING_AGENT = "selecting-agent"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DepartmentTask:
    """
    Representa una tarea gestionada por DepartmentRuntime.

    La tarea puede ser texto plano o una estructura compleja,
    por ejemplo un diccionario generado por WorkflowEngine.
    """

    task: Any
    department_id: str

    task_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    required_capabilities: List[str] = field(
        default_factory=list
    )

    required_tools: List[str] = field(
        default_factory=list
    )

    required_permissions: List[str] = field(
        default_factory=list
    )

    preferred_agent_ids: List[str] = field(
        default_factory=list
    )

    excluded_agent_ids: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    status: DepartmentTaskStatus = (
        DepartmentTaskStatus.CREATED
    )

    selected_agent_id: Optional[str] = None
    selection_score: Optional[float] = None

    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    duration_seconds: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def __post_init__(self) -> None:
        self.task = self._normalize_task(
            self.task
        )

        self.department_id = self._normalize_identifier(
            self.department_id
        )

        self.required_capabilities = (
            self._normalize_collection(
                self.required_capabilities
            )
        )

        self.required_tools = self._normalize_collection(
            self.required_tools
        )

        self.required_permissions = (
            self._normalize_collection(
                self.required_permissions
            )
        )

        self.preferred_agent_ids = (
            self._normalize_collection(
                self.preferred_agent_ids
            )
        )

        self.excluded_agent_ids = (
            self._normalize_collection(
                self.excluded_agent_ids
            )
        )

        self.metadata = dict(
            self.metadata or {}
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task": self.task,
            "department_id": self.department_id,
            "required_capabilities": list(
                self.required_capabilities
            ),
            "required_tools": list(
                self.required_tools
            ),
            "required_permissions": list(
                self.required_permissions
            ),
            "preferred_agent_ids": list(
                self.preferred_agent_ids
            ),
            "excluded_agent_ids": list(
                self.excluded_agent_ids
            ),
            "status": self.status.value,
            "selected_agent_id": self.selected_agent_id,
            "selection_score": self.selection_score,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": self.duration_seconds,
            "result": self.result,
            "error": self.error,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def _normalize_task(
        task: Any,
    ) -> Any:
        """
        Valida la tarea sin destruir su estructura original.
        """

        if task is None:
            raise ValueError(
                "La tarea departamental no puede ser None."
            )

        if isinstance(task, str):
            normalized_task = task.strip()

            if not normalized_task:
                raise ValueError(
                    "La tarea departamental no puede estar vacía."
                )

            return normalized_task

        if isinstance(task, dict):
            if not task:
                raise ValueError(
                    "La tarea departamental estructurada "
                    "no puede estar vacía."
                )

            return dict(task)

        return task

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

    @classmethod
    def _normalize_collection(
        cls,
        values: List[str],
    ) -> List[str]:
        return sorted(
            {
                cls._normalize_identifier(value)
                for value in values
                if str(value).strip()
            }
        )


class DepartmentRuntime:
    """
    Motor operativo de departamentos de Atlas AI OS.

    Responsabilidades principales:

    - Validar que el departamento exista y esté operativo.
    - Seleccionar el mejor agente empresarial.
    - Ejecutar la tarea mediante el AgentManager del Kernel.
    - Actualizar la carga y las métricas del AgentProfile.
    - Registrar historial de tareas departamentales.
    - Publicar eventos operativos en el EventBus.
    """

    def __init__(
        self,
        organization_manager: OrganizationManager,
        agent_manager: AgentManager,
        event_bus: Optional[EventBus] = None,
    ) -> None:

        if organization_manager is None:
            raise ValueError(
                "organization_manager no puede ser None."
            )

        if agent_manager is None:
            raise ValueError(
                "agent_manager no puede ser None."
            )

        required_organization_methods = (
            "initialize",
            "select_agent",
            "rank_agents",
            "start_agent_task",
            "finish_agent_task",
        )

        for method_name in required_organization_methods:
            if not hasattr(
                organization_manager,
                method_name,
            ):
                raise TypeError(
                    "organization_manager no implementa "
                    f"el método requerido '{method_name}'."
                )

        if not hasattr(agent_manager, "execute"):
            raise TypeError(
                "agent_manager no implementa el método "
                "requerido 'execute'."
            )

        self.organization_manager = organization_manager
        self.agent_manager = agent_manager
        self.event_bus = event_bus

        self._status = DepartmentRuntimeStatus.CREATED
        self._tasks: Dict[str, DepartmentTask] = {}

        self._created_at = datetime.now().isoformat()
        self._started_at: Optional[str] = None
        self._stopped_at: Optional[str] = None
        self._last_error: Optional[str] = None

    # ============================================================
    # Propiedades
    # ============================================================

    @property
    def status(self) -> DepartmentRuntimeStatus:
        return self._status

    @property
    def is_ready(self) -> bool:
        return self._status in {
            DepartmentRuntimeStatus.READY,
            DepartmentRuntimeStatus.RUNNING,
        }

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    # ============================================================
    # Ciclo de vida
    # ============================================================

    def start(self) -> None:
        """
        Inicia el runtime departamental.
        """

        if self.is_ready:
            return

        if not self.organization_manager.is_ready:
            self.organization_manager.initialize()

        self._status = DepartmentRuntimeStatus.READY
        self._started_at = datetime.now().isoformat()
        self._stopped_at = None
        self._last_error = None

        self._publish(
            "department_runtime.started",
            {
                "status": self._status.value,
                "started_at": self._started_at,
            },
        )

    def stop(self) -> None:
        """
        Detiene el runtime departamental.
        """

        if self._status == DepartmentRuntimeStatus.STOPPED:
            return

        self._status = DepartmentRuntimeStatus.STOPPING

        self._publish(
            "department_runtime.stopping",
            {
                "active_tasks": self.active_task_count(),
            },
        )

        self._status = DepartmentRuntimeStatus.STOPPED
        self._stopped_at = datetime.now().isoformat()

        self._publish(
            "department_runtime.stopped",
            {
                "stopped_at": self._stopped_at,
            },
        )

    # ============================================================
    # Ejecución
    # ============================================================

    def execute(
        self,
        department_id: str,
        task: Any,
        required_capabilities: Optional[List[str]] = None,
        required_tools: Optional[List[str]] = None,
        required_permissions: Optional[List[str]] = None,
        preferred_agent_ids: Optional[List[str]] = None,
        excluded_agent_ids: Optional[List[str]] = None,
        strategy: SelectionStrategy = SelectionStrategy.BALANCED,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta una tarea dentro de un departamento.

        Selecciona automáticamente el mejor agente empresarial y luego
        delega la ejecución al AgentManager del Kernel.

        La tarea puede ser texto plano o una estructura compleja.
        """

        self._ensure_ready()

        department = self._get_operational_department(
            department_id
        )

        department_task = DepartmentTask(
            task=task,
            department_id=department.department_id,
            required_capabilities=(
                required_capabilities or []
            ),
            required_tools=required_tools or [],
            required_permissions=(
                required_permissions or []
            ),
            preferred_agent_ids=(
                preferred_agent_ids or []
            ),
            excluded_agent_ids=(
                excluded_agent_ids or []
            ),
            metadata=metadata or {},
        )

        self._tasks[department_task.task_id] = (
            department_task
        )

        started_counter = perf_counter()

        try:
            self._status = DepartmentRuntimeStatus.RUNNING
            department_task.status = (
                DepartmentTaskStatus.SELECTING_AGENT
            )

            selection = self._select_agent(
                department=department,
                task=department_task,
                strategy=strategy,
            )

            selected_agent = selection.agent

            department_task.selected_agent_id = (
                selected_agent.agent_id
            )

            department_task.selection_score = round(
                selection.score,
                4,
            )

            department_task.status = (
                DepartmentTaskStatus.RUNNING
            )

            department_task.started_at = (
                datetime.now().isoformat()
            )

            self._publish(
                "department.task.started",
                {
                    "task_id": department_task.task_id,
                    "department_id": department.department_id,
                    "agent_id": selected_agent.agent_id,
                    "selection_score": selection.score,
                    "task": self._task_summary(
                        department_task.task
                    ),
                },
            )

            self.organization_manager.start_agent_task(
                selected_agent.agent_id
            )

            execution_result = self.agent_manager.execute(
                agent_name=selected_agent.agent_id,
                task=department_task.task,
            )

            duration_seconds = (
                perf_counter() - started_counter
            )

            success = self._is_successful_result(
                execution_result
            )

            quality_score = self._extract_numeric_score(
                execution_result,
                "quality_score",
            )

            confidence_score = self._extract_numeric_score(
                execution_result,
                "confidence",
            )

            self.organization_manager.finish_agent_task(
                agent_id=selected_agent.agent_id,
                success=success,
                duration_seconds=duration_seconds,
                quality_score=quality_score,
                confidence_score=confidence_score,
            )

            department_task.status = (
                DepartmentTaskStatus.COMPLETED
                if success
                else DepartmentTaskStatus.FAILED
            )

            department_task.result = execution_result

            department_task.duration_seconds = round(
                duration_seconds,
                6,
            )

            department_task.finished_at = (
                datetime.now().isoformat()
            )

            response = {
                "runtime": "department-runtime",
                "task_id": department_task.task_id,
                "status": department_task.status.value,
                "department": department.to_dict(),
                "agent_id": selected_agent.agent_id,
                "selected_agent": selection.to_dict(),
                "execution": execution_result,
                "duration_seconds": (
                    department_task.duration_seconds
                ),
                "metadata": dict(
                    department_task.metadata
                ),
            }

            self._publish(
                "department.task.completed",
                {
                    "task_id": department_task.task_id,
                    "department_id": department.department_id,
                    "agent_id": selected_agent.agent_id,
                    "status": department_task.status.value,
                    "duration_seconds": duration_seconds,
                },
            )

            self._status = DepartmentRuntimeStatus.READY

            return response

        except Exception as error:
            duration_seconds = (
                perf_counter() - started_counter
            )

            department_task.status = (
                DepartmentTaskStatus.FAILED
            )

            department_task.error = str(error)

            department_task.duration_seconds = round(
                duration_seconds,
                6,
            )

            department_task.finished_at = (
                datetime.now().isoformat()
            )

            self._last_error = str(error)
            self._status = DepartmentRuntimeStatus.ERROR

            if department_task.selected_agent_id:
                try:
                    self.organization_manager.finish_agent_task(
                        agent_id=(
                            department_task.selected_agent_id
                        ),
                        success=False,
                        duration_seconds=duration_seconds,
                    )
                except Exception:
                    pass

            self._publish(
                "department.task.failed",
                {
                    "task_id": department_task.task_id,
                    "department_id": (
                        department_task.department_id
                    ),
                    "agent_id": (
                        department_task.selected_agent_id
                    ),
                    "error": str(error),
                    "duration_seconds": duration_seconds,
                },
            )

            raise

    # ============================================================
    # Selección
    # ============================================================

    def select_agent(
        self,
        department_id: str,
        required_capabilities: Optional[List[str]] = None,
        required_tools: Optional[List[str]] = None,
        required_permissions: Optional[List[str]] = None,
        preferred_agent_ids: Optional[List[str]] = None,
        excluded_agent_ids: Optional[List[str]] = None,
        strategy: SelectionStrategy = SelectionStrategy.BALANCED,
    ) -> AgentSelectionResult:
        """
        Selecciona un agente sin ejecutar una tarea.
        """

        self._ensure_ready()

        department = self._get_operational_department(
            department_id
        )

        criteria = AgentSelectionCriteria(
            required_capabilities=(
                required_capabilities or []
            ),
            preferred_department=department.department_id,
            required_tools=required_tools or [],
            required_permissions=(
                required_permissions or []
            ),
            preferred_agent_ids=(
                preferred_agent_ids or []
            ),
            excluded_agent_ids=(
                excluded_agent_ids or []
            ),
            strategy=strategy,
            available_only=True,
            enabled_only=True,
        )

        selection = self.organization_manager.select_agent(
            criteria
        )

        if selection is None:
            raise RuntimeError(
                "No se encontró un agente disponible para el "
                f"departamento '{department.department_id}'."
            )

        if (
            selection.agent.department
            != department.department_id
        ):
            raise RuntimeError(
                "No se encontró un agente disponible perteneciente "
                f"al departamento '{department.department_id}'."
            )

        return selection

    def _select_agent(
        self,
        department: DepartmentProfile,
        task: DepartmentTask,
        strategy: SelectionStrategy,
    ) -> AgentSelectionResult:
        preferred_agents = list(
            task.preferred_agent_ids
        )

        if (
            department.director_agent_id
            and department.director_agent_id
            not in preferred_agents
        ):
            preferred_agents.append(
                department.director_agent_id
            )

        criteria = AgentSelectionCriteria(
            required_capabilities=list(
                task.required_capabilities
            ),
            preferred_department=department.department_id,
            required_tools=list(
                task.required_tools
            ),
            required_permissions=list(
                task.required_permissions
            ),
            preferred_agent_ids=preferred_agents,
            excluded_agent_ids=list(
                task.excluded_agent_ids
            ),
            available_only=True,
            enabled_only=True,
            strategy=strategy,
            metadata={
                "task_id": task.task_id,
                "department_id": department.department_id,
            },
        )

        ranking = self.organization_manager.rank_agents(
            criteria
        )

        department_ranking = [
            candidate
            for candidate in ranking
            if (
                candidate.agent.department
                == department.department_id
            )
        ]

        if not department_ranking:
            raise RuntimeError(
                "No hay agentes disponibles que cumplan los "
                f"requisitos del departamento "
                f"'{department.department_id}'."
            )

        return department_ranking[0]

    # ============================================================
    # Consultas
    # ============================================================

    def get_task(
        self,
        task_id: str,
    ) -> DepartmentTask:
        normalized_id = str(task_id).strip()

        if normalized_id not in self._tasks:
            raise KeyError(
                f"La tarea '{normalized_id}' no está registrada."
            )

        return self._tasks[normalized_id]

    def get_task_data(
        self,
        task_id: str,
    ) -> Dict[str, Any]:
        return self.get_task(task_id).to_dict()

    def list_tasks(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        tasks = sorted(
            self._tasks.values(),
            key=lambda item: item.created_at,
            reverse=True,
        )

        if limit is not None:
            if limit < 1:
                return []

            tasks = tasks[:limit]

        return [
            task.to_dict()
            for task in tasks
        ]

    def active_task_count(self) -> int:
        return sum(
            1
            for task in self._tasks.values()
            if task.status
            in {
                DepartmentTaskStatus.SELECTING_AGENT,
                DepartmentTaskStatus.RUNNING,
            }
        )

    def completed_task_count(self) -> int:
        return sum(
            1
            for task in self._tasks.values()
            if task.status
            == DepartmentTaskStatus.COMPLETED
        )

    def failed_task_count(self) -> int:
        return sum(
            1
            for task in self._tasks.values()
            if task.status
            == DepartmentTaskStatus.FAILED
        )

    def department_summary(
        self,
        department_id: str,
    ) -> Dict[str, Any]:
        department = self._get_department(
            department_id
        )

        department_tasks = [
            task
            for task in self._tasks.values()
            if (
                task.department_id
                == department.department_id
            )
        ]

        return {
            "department": department.to_dict(),
            "total_tasks": len(department_tasks),
            "active_tasks": sum(
                1
                for task in department_tasks
                if task.status
                in {
                    DepartmentTaskStatus.SELECTING_AGENT,
                    DepartmentTaskStatus.RUNNING,
                }
            ),
            "completed_tasks": sum(
                1
                for task in department_tasks
                if task.status
                == DepartmentTaskStatus.COMPLETED
            ),
            "failed_tasks": sum(
                1
                for task in department_tasks
                if task.status
                == DepartmentTaskStatus.FAILED
            ),
        }

    def summary(self) -> Dict[str, Any]:
        return {
            "status": self._status.value,
            "is_ready": self.is_ready,
            "created_at": self._created_at,
            "started_at": self._started_at,
            "stopped_at": self._stopped_at,
            "last_error": self._last_error,
            "total_tasks": self.task_count,
            "active_tasks": self.active_task_count(),
            "completed_tasks": (
                self.completed_task_count()
            ),
            "failed_tasks": self.failed_task_count(),
        }

    # ============================================================
    # Utilidades internas
    # ============================================================

    def _get_department(
        self,
        department_id: str,
    ) -> DepartmentProfile:
        normalized_id = self._normalize_identifier(
            department_id
        )

        return (
            self.organization_manager
            .organization
            .get_department(normalized_id)
        )

    def _get_operational_department(
        self,
        department_id: str,
    ) -> DepartmentProfile:
        department = self._get_department(
            department_id
        )

        if not department.enabled:
            raise RuntimeError(
                f"El departamento '{department.department_id}' "
                "está deshabilitado."
            )

        if not department.is_operational:
            raise RuntimeError(
                f"El departamento '{department.department_id}' "
                "no está operativo."
            )

        return department

    def _ensure_ready(self) -> None:
        if not self.is_ready:
            raise RuntimeError(
                "DepartmentRuntime no está iniciado. "
                "Ejecute start() antes de utilizarlo."
            )

        if not self.organization_manager.is_ready:
            raise RuntimeError(
                "OrganizationManager no está listo."
            )

    def _publish(
        self,
        event_name: str,
        payload: Dict[str, Any],
    ) -> None:
        if self.event_bus is None:
            return

        self.event_bus.publish(
            event_name,
            payload,
        )

    @staticmethod
    def _task_summary(
        task: Any,
    ) -> Dict[str, Any]:
        """
        Genera una representación compacta de la tarea
        para eventos y registros operativos.
        """

        if isinstance(task, dict):
            previous_results = task.get(
                "previous_results",
                {},
            )

            dependency_ids = (
                list(previous_results.keys())
                if isinstance(previous_results, dict)
                else []
            )

            return {
                "type": "structured-task",
                "workflow_id": task.get(
                    "workflow_id"
                ),
                "step_id": task.get(
                    "step_id"
                ),
                "request": str(
                    task.get("request", "")
                )[:500],
                "dependency_ids": dependency_ids,
            }

        return {
            "type": "text-task",
            "content": str(task)[:500],
        }

    @staticmethod
    def _is_successful_result(
        result: Dict[str, Any],
    ) -> bool:
        status = str(
            result.get("status", "completed")
        ).strip().lower()

        return status not in {
            "failed",
            "error",
            "cancelled",
            "canceled",
        }

    @staticmethod
    def _extract_numeric_score(
        result: Dict[str, Any],
        field_name: str,
    ) -> Optional[float]:
        value = result.get(field_name)

        if value is None:
            return None

        try:
            score = float(value)
        except (TypeError, ValueError):
            return None

        return max(
            0.0,
            min(100.0, score),
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