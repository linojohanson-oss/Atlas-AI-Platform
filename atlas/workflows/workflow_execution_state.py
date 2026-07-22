"""
Atlas AI OS - Workflow Execution State

Mantiene una representación viva y consultable del estado de una
ejecución de workflow a partir de los eventos emitidos por
WorkflowEventBus.

Este componente:

- No ejecuta workflows.
- No publica eventos.
- No imprime información.
- No depende de consola, HTML ni API.
- Solamente consume eventos y mantiene el estado actualizado.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime
from threading import RLock
from typing import Any, Dict, List, Optional


# ============================================================
# Estado de un paso
# ============================================================


@dataclass
class StepExecutionState:
    """
    Estado observable de un paso individual del workflow.
    """

    step_id: str
    step_name: Optional[str] = None
    department_id: Optional[str] = None
    agent_id: Optional[str] = None

    status: str = "pending"

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    error: Optional[str] = None
    reason: Optional[str] = None
    output: Any = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Devuelve una representación serializable del paso.
        """

        data = asdict(self)

        data["started_at"] = self._serialize_datetime(
            self.started_at
        )
        data["completed_at"] = self._serialize_datetime(
            self.completed_at
        )

        return data

    @staticmethod
    def _serialize_datetime(
        value: Optional[datetime],
    ) -> Optional[str]:
        if value is None:
            return None

        return value.isoformat()


# ============================================================
# Estado completo de una ejecución
# ============================================================


class WorkflowExecutionState:
    """
    Mantiene el estado vivo de una ejecución de workflow.

    El método principal es ``on_event``. Puede registrarse
    directamente como listener de WorkflowEventBus:

        state = WorkflowExecutionState()
        event_bus.subscribe(state.on_event)
    """

    TERMINAL_STEP_STATUSES = {
        "completed",
        "failed",
        "skipped",
        "blocked",
        "cancelled",
    }

    SUCCESS_STEP_STATUSES = {
        "completed",
        "skipped",
    }

    TERMINAL_WORKFLOW_STATUSES = {
        "completed",
        "failed",
        "cancelled",
        "partial",
    }

    def __init__(self) -> None:
        self._lock = RLock()

        self.execution_id: Optional[str] = None
        self.workflow_id: Optional[str] = None
        self.workflow_name: Optional[str] = None

        self.workflow_status: str = "created"

        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.duration_seconds: Optional[float] = None

        self.input_data: Any = None
        self.final_output: Any = None
        self.error: Optional[str] = None

        self.steps: Dict[
            str,
            StepExecutionState,
        ] = {}

        self.expected_step_ids: List[str] = []

        self.last_event_type: Optional[str] = None
        self.last_event_at: Optional[datetime] = None
        self.last_event_data: Dict[str, Any] = {}

        self.event_count: int = 0

    # ========================================================
    # Consumo de eventos
    # ========================================================

    def on_event(self, event: Any) -> None:
        """
        Procesa un evento publicado por WorkflowEventBus.

        El método es defensivo para tolerar pequeñas diferencias
        entre versiones del modelo WorkflowEvent.
        """

        with self._lock:
            event_type = self._event_type(event)
            event_time = self._event_timestamp(event)
            event_data = self._event_data(event)
            step_id = self._event_step_id(event)

            self.event_count += 1
            self.last_event_type = event_type
            self.last_event_at = event_time
            self.last_event_data = deepcopy(event_data)

            self._capture_event_identity(
                event=event,
                data=event_data,
            )

            if event_type == "workflow-started":
                self._handle_workflow_started(
                    event_time=event_time,
                    data=event_data,
                )

            elif event_type == "step-started":
                self._handle_step_started(
                    step_id=step_id,
                    event_time=event_time,
                    data=event_data,
                )

            elif event_type == "step-completed":
                self._handle_step_completed(
                    step_id=step_id,
                    event_time=event_time,
                    data=event_data,
                )

            elif event_type == "step-failed":
                self._handle_step_failed(
                    step_id=step_id,
                    event_time=event_time,
                    data=event_data,
                )

            elif event_type == "step-skipped":
                self._handle_step_skipped(
                    step_id=step_id,
                    event_time=event_time,
                    data=event_data,
                )

            elif event_type == "step-blocked":
                self._handle_step_blocked(
                    step_id=step_id,
                    event_time=event_time,
                    data=event_data,
                )

            elif event_type == "workflow-finished":
                self._handle_workflow_finished(
                    event_time=event_time,
                    data=event_data,
                )

            elif event_type == "workflow-failed":
                self._handle_workflow_failed(
                    event_time=event_time,
                    data=event_data,
                )

    # ========================================================
    # Handlers de workflow
    # ========================================================

    def _handle_workflow_started(
        self,
        event_time: datetime,
        data: Dict[str, Any],
    ) -> None:
        self.workflow_status = data.get(
            "status",
            "running",
        )

        self.started_at = event_time
        self.completed_at = None
        self.duration_seconds = None
        self.error = None
        self.final_output = None

        self.workflow_name = (
            data.get("workflow_name")
            or self.workflow_name
        )

        self.input_data = data.get(
            "input",
            data.get(
                "input_data",
                self.input_data,
            ),
        )

        expected_steps = data.get(
            "expected_steps",
            [],
        )

        self.expected_step_ids = []

        if isinstance(expected_steps, list):
            for step_data in expected_steps:
                if not isinstance(step_data, dict):
                    continue

                step_id = step_data.get(
                    "step_id"
                )

                if not step_id:
                    continue

                step_id = str(step_id)

                self.expected_step_ids.append(
                    step_id
                )

                step_state = (
                    self._get_or_create_step(
                        step_id=step_id,
                    )
                )

                step_state.step_name = (
                    step_data.get("step_name")
                    or step_id
                )

                step_state.department_id = (
                    step_data.get(
                        "department_id"
                    )
                )

                step_state.agent_id = (
                    step_data.get(
                        "agent_id"
                    )
                )

                step_state.status = "pending"

                step_state.metadata.update(
                    {
                        "step_type": (
                            step_data.get(
                                "step_type"
                            )
                        ),
                    }
                )

        else:
            step_ids = data.get(
                "step_ids",
                [],
            )

            if isinstance(step_ids, list):
                self.expected_step_ids = [
                    str(step_id)
                    for step_id in step_ids
                ]

                for step_id in (
                    self.expected_step_ids
                ):
                    step_state = (
                        self._get_or_create_step(
                            step_id=step_id,
                        )
                    )

                    step_state.status = "pending"
    def _handle_workflow_finished(
        self,
        event_time: datetime,
        data: Dict[str, Any],
    ) -> None:
        self.workflow_status = data.get(
            "status",
            "completed",
        )

        self.completed_at = event_time
        self.final_output = data.get(
            "final_output",
            self.final_output,
        )

        self._calculate_workflow_duration()

    def _handle_workflow_failed(
        self,
        event_time: datetime,
        data: Dict[str, Any],
    ) -> None:
        self.workflow_status = "failed"
        self.completed_at = event_time

        self.error = (
            data.get("error")
            or data.get("message")
            or data.get("reason")
        )

        self.final_output = data.get(
            "final_output",
            self.final_output,
        )

        self._calculate_workflow_duration()

    # ========================================================
    # Handlers de pasos
    # ========================================================

    def _handle_step_started(
        self,
        step_id: Optional[str],
        event_time: datetime,
        data: Dict[str, Any],
    ) -> None:
        if not step_id:
            return

        step = self._get_or_create_step(
            step_id=step_id,
            data=data,
        )

        step.status = data.get(
            "status",
            "running",
        )

        step.started_at = event_time
        step.completed_at = None
        step.duration_seconds = None
        step.error = None
        step.reason = None

        self._update_step_metadata(
            step=step,
            data=data,
        )

    def _handle_step_completed(
        self,
        step_id: Optional[str],
        event_time: datetime,
        data: Dict[str, Any],
    ) -> None:
        if not step_id:
            return

        step = self._get_or_create_step(
            step_id=step_id,
            data=data,
        )

        step.status = data.get(
            "status",
            "completed",
        )

        step.completed_at = event_time
        step.output = data.get(
            "output",
            data.get(
                "result",
                step.output,
            ),
        )

        self._calculate_step_duration(step)

        self._update_step_metadata(
            step=step,
            data=data,
        )

    def _handle_step_failed(
        self,
        step_id: Optional[str],
        event_time: datetime,
        data: Dict[str, Any],
    ) -> None:
        if not step_id:
            return

        step = self._get_or_create_step(
            step_id=step_id,
            data=data,
        )

        step.status = "failed"
        step.completed_at = event_time

        step.error = (
            data.get("error")
            or data.get("message")
            or data.get("reason")
        )

        self._calculate_step_duration(step)

        self._update_step_metadata(
            step=step,
            data=data,
        )

    def _handle_step_skipped(
        self,
        step_id: Optional[str],
        event_time: datetime,
        data: Dict[str, Any],
    ) -> None:
        if not step_id:
            return

        step = self._get_or_create_step(
            step_id=step_id,
            data=data,
        )

        step.status = "skipped"
        step.completed_at = event_time
        step.reason = data.get("reason")

        self._calculate_step_duration(step)

        self._update_step_metadata(
            step=step,
            data=data,
        )

    def _handle_step_blocked(
        self,
        step_id: Optional[str],
        event_time: datetime,
        data: Dict[str, Any],
    ) -> None:
        if not step_id:
            return

        step = self._get_or_create_step(
            step_id=step_id,
            data=data,
        )

        step.status = "blocked"
        step.completed_at = event_time
        step.reason = data.get("reason")

        self._calculate_step_duration(step)

        self._update_step_metadata(
            step=step,
            data=data,
        )

    # ========================================================
    # Gestión interna de pasos
    # ========================================================

    def _get_or_create_step(
        self,
        step_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> StepExecutionState:
        if step_id not in self.steps:
            self.steps[step_id] = StepExecutionState(
                step_id=step_id,
            )

        step = self.steps[step_id]

        if data:
            step.step_name = (
                data.get("step_name")
                or step.step_name
            )

            step.department_id = (
                data.get("department_id")
                or step.department_id
            )

            step.agent_id = (
                data.get("agent_id")
                or step.agent_id
            )

        return step

    def _update_step_metadata(
        self,
        step: StepExecutionState,
        data: Dict[str, Any],
    ) -> None:
        excluded_keys = {
            "status",
            "step_name",
            "department_id",
            "agent_id",
            "output",
            "result",
            "error",
            "reason",
        }

        for key, value in data.items():
            if key not in excluded_keys:
                step.metadata[key] = deepcopy(value)

    # ========================================================
    # Identidad y lectura de eventos
    # ========================================================

    def _capture_event_identity(
        self,
        event: Any,
        data: Dict[str, Any],
    ) -> None:
        execution_id = (
            getattr(
                event,
                "execution_id",
                None,
            )
            or data.get("execution_id")
        )

        workflow_id = (
            getattr(
                event,
                "workflow_id",
                None,
            )
            or data.get("workflow_id")
        )

        if execution_id:
            self.execution_id = str(execution_id)

        if workflow_id:
            self.workflow_id = str(workflow_id)

    @staticmethod
    def _event_type(event: Any) -> str:
        value = getattr(
            event,
            "event_type",
            "",
        )

        if hasattr(value, "value"):
            value = value.value

        return str(value)

    @staticmethod
    def _event_timestamp(event: Any) -> datetime:
        value = getattr(
            event,
            "timestamp",
            None,
        )

        if isinstance(value, datetime):
            return value

        return datetime.now()

    @staticmethod
    def _event_data(
        event: Any,
    ) -> Dict[str, Any]:
        value = getattr(
            event,
            "data",
            {},
        )

        if isinstance(value, dict):
            return value

        return {}

    @staticmethod
    def _event_step_id(
        event: Any,
    ) -> Optional[str]:
        value = getattr(
            event,
            "step_id",
            None,
        )

        if value is None:
            return None

        return str(value)

    # ========================================================
    # Duraciones
    # ========================================================

    @staticmethod
    def _calculate_step_duration(
        step: StepExecutionState,
    ) -> None:
        if (
            step.started_at is None
            or step.completed_at is None
        ):
            return

        duration = (
            step.completed_at
            - step.started_at
        ).total_seconds()

        step.duration_seconds = max(
            0.0,
            round(duration, 6),
        )

    def _calculate_workflow_duration(
        self,
    ) -> None:
        if (
            self.started_at is None
            or self.completed_at is None
        ):
            return

        duration = (
            self.completed_at
            - self.started_at
        ).total_seconds()

        self.duration_seconds = max(
            0.0,
            round(duration, 6),
        )

    # ========================================================
    # Consultas públicas
    # ========================================================

    def progress(self) -> float:
        """
        Devuelve el porcentaje de progreso entre 0 y 100.
        """

        with self._lock:
            total = self.total_steps()

            if total == 0:
                if (
                    self.workflow_status
                    in self.TERMINAL_WORKFLOW_STATUSES
                ):
                    return 100.0

                return 0.0

            finished = sum(
                1
                for step in self.steps.values()
                if step.status
                in self.TERMINAL_STEP_STATUSES
            )

            return round(
                finished / total * 100,
                2,
            )

    def total_steps(self) -> int:
        with self._lock:
            if self.expected_step_ids:
                return len(
                    set(self.expected_step_ids)
                )

            return len(self.steps)

    def running_steps(
        self,
    ) -> List[Dict[str, Any]]:
        return self._steps_by_status(
            {"running"}
        )

    def completed_steps(
        self,
    ) -> List[Dict[str, Any]]:
        return self._steps_by_status(
            {"completed"}
        )

    def failed_steps(
        self,
    ) -> List[Dict[str, Any]]:
        return self._steps_by_status(
            {"failed"}
        )

    def pending_steps(
        self,
    ) -> List[Dict[str, Any]]:
        return self._steps_by_status(
            {"pending"}
        )

    def skipped_steps(
        self,
    ) -> List[Dict[str, Any]]:
        return self._steps_by_status(
            {"skipped"}
        )

    def blocked_steps(
        self,
    ) -> List[Dict[str, Any]]:
        return self._steps_by_status(
            {"blocked"}
        )

    def _steps_by_status(
        self,
        statuses: set,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                step.to_dict()
                for step in self.steps.values()
                if step.status in statuses
            ]

    def snapshot(self) -> Dict[str, Any]:
        """
        Devuelve una copia completa y serializable del estado.
        """

        with self._lock:
            return {
                "execution_id": self.execution_id,
                "workflow_id": self.workflow_id,
                "workflow_name": self.workflow_name,
                "status": self.workflow_status,
                "progress": self.progress(),
                "started_at": self._serialize_datetime(
                    self.started_at
                ),
                "completed_at": self._serialize_datetime(
                    self.completed_at
                ),
                "duration_seconds": (
                    self.duration_seconds
                ),
                "input_data": deepcopy(
                    self.input_data
                ),
                "final_output": deepcopy(
                    self.final_output
                ),
                "error": self.error,
                "total_steps": self.total_steps(),
                "running_count": len(
                    self.running_steps()
                ),
                "completed_count": len(
                    self.completed_steps()
                ),
                "failed_count": len(
                    self.failed_steps()
                ),
                "pending_count": len(
                    self.pending_steps()
                ),
                "skipped_count": len(
                    self.skipped_steps()
                ),
                "blocked_count": len(
                    self.blocked_steps()
                ),
                "steps": {
                    step_id: step.to_dict()
                    for step_id, step
                    in self.steps.items()
                },
                "last_event": {
                    "event_type": (
                        self.last_event_type
                    ),
                    "timestamp": (
                        self._serialize_datetime(
                            self.last_event_at
                        )
                    ),
                    "data": deepcopy(
                        self.last_event_data
                    ),
                },
                "event_count": self.event_count,
            }

    def reset(self) -> None:
        """
        Limpia todo el estado para reutilizar la instancia.
        """

        with self._lock:
            self.execution_id = None
            self.workflow_id = None
            self.workflow_name = None

            self.workflow_status = "created"

            self.started_at = None
            self.completed_at = None
            self.duration_seconds = None

            self.input_data = None
            self.final_output = None
            self.error = None

            self.steps.clear()
            self.expected_step_ids.clear()

            self.last_event_type = None
            self.last_event_at = None
            self.last_event_data = {}

            self.event_count = 0

    @staticmethod
    def _serialize_datetime(
        value: Optional[datetime],
    ) -> Optional[str]:
        if value is None:
            return None

        return value.isoformat()

    def __repr__(self) -> str:
        return (
            "WorkflowExecutionState("
            f"workflow_id={self.workflow_id!r}, "
            f"status={self.workflow_status!r}, "
            f"progress={self.progress():.2f}, "
            f"steps={self.total_steps()}"
            ")"
        )