"""
Atlas AI Platform - Workflow Result

Representa el resultado completo de una ejecución de workflow.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class WorkflowResultStatus(str, Enum):
    """
    Estados posibles del resultado general.
    """

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowResult:
    """
    Resultado completo producido por WorkflowEngine.
    """

    workflow_id: str
    execution_id: str
    request: str

    status: WorkflowResultStatus = (
        WorkflowResultStatus.CREATED
    )

    completed_steps: List[Dict[str, Any]] = field(
        default_factory=list
    )

    failed_steps: List[Dict[str, Any]] = field(
        default_factory=list
    )

    skipped_steps: List[Dict[str, Any]] = field(
        default_factory=list
    )

    blocked_steps: List[Dict[str, Any]] = field(
        default_factory=list
    )

    final_output: Any = None

    context: Dict[str, Any] = field(
        default_factory=dict
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    errors: List[Dict[str, Any]] = field(
        default_factory=list
    )

    started_at: datetime = field(
        default_factory=datetime.now
    )

    finished_at: Optional[datetime] = None

    duration_seconds: float = 0.0

    def __post_init__(self) -> None:
        """
        Valida y normaliza los valores iniciales.
        """

        self.workflow_id = str(
            self.workflow_id
        ).strip()

        self.execution_id = str(
            self.execution_id
        ).strip()

        self.request = str(
            self.request
        ).strip()

        if not self.workflow_id:
            raise ValueError(
                "WorkflowResult requiere workflow_id."
            )

        if not self.execution_id:
            raise ValueError(
                "WorkflowResult requiere execution_id."
            )

        if not self.request:
            raise ValueError(
                "WorkflowResult requiere request."
            )

        if isinstance(self.status, str):
            self.status = WorkflowResultStatus(
                self.status
            )

        self.completed_steps = list(
            self.completed_steps or []
        )

        self.failed_steps = list(
            self.failed_steps or []
        )

        self.skipped_steps = list(
            self.skipped_steps or []
        )

        self.blocked_steps = list(
            self.blocked_steps or []
        )

        self.context = dict(
            self.context or {}
        )

        self.metadata = dict(
            self.metadata or {}
        )

        self.errors = list(
            self.errors or []
        )

        self.duration_seconds = float(
            self.duration_seconds or 0.0
        )

    @property
    def total_steps(self) -> int:
        """
        Total de pasos registrados.
        """

        return (
            len(self.completed_steps)
            + len(self.failed_steps)
            + len(self.skipped_steps)
            + len(self.blocked_steps)
        )

    @property
    def completed_count(self) -> int:
        return len(self.completed_steps)

    @property
    def failed_count(self) -> int:
        return len(self.failed_steps)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped_steps)

    @property
    def blocked_count(self) -> int:
        return len(self.blocked_steps)

    @property
    def success_rate(self) -> float:
        """
        Porcentaje de pasos completados sobre los ejecutados.
        """

        executed = (
            self.completed_count
            + self.failed_count
        )

        if executed <= 0:
            return 0.0

        return round(
            self.completed_count
            / executed
            * 100.0,
            2,
        )

    @property
    def is_successful(self) -> bool:
        """
        Indica si el workflow terminó correctamente.
        """

        return (
            self.status
            == WorkflowResultStatus.COMPLETED
        )

    @property
    def has_errors(self) -> bool:
        """
        Indica si existen errores registrados.
        """

        return bool(
            self.errors
            or self.failed_steps
        )

    def start(self) -> None:
        """
        Marca el resultado como running.
        """

        self.status = WorkflowResultStatus.RUNNING
        self.started_at = datetime.now()
        self.finished_at = None
        self.duration_seconds = 0.0

    def add_completed_step(
        self,
        step_id: str,
        result: Optional[Dict[str, Any]] = None,
        duration_seconds: float = 0.0,
    ) -> None:
        """
        Registra un paso completado.
        """

        self.completed_steps.append(
            self._build_step_record(
                step_id=step_id,
                status="completed",
                result=result,
                duration_seconds=duration_seconds,
            )
        )

    def add_failed_step(
        self,
        step_id: str,
        error: str,
        result: Optional[Dict[str, Any]] = None,
        duration_seconds: float = 0.0,
    ) -> None:
        """
        Registra un paso fallido.
        """

        normalized_error = str(
            error
        ).strip()

        record = self._build_step_record(
            step_id=step_id,
            status="failed",
            result=result,
            duration_seconds=duration_seconds,
        )

        record["error"] = normalized_error

        self.failed_steps.append(record)

        self.add_error(
            message=normalized_error,
            step_id=step_id,
        )

    def add_skipped_step(
        self,
        step_id: str,
        reason: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Registra un paso omitido.
        """

        record = self._build_step_record(
            step_id=step_id,
            status="skipped",
            result=result,
        )

        record["reason"] = str(
            reason
        ).strip()

        self.skipped_steps.append(record)

    def add_blocked_step(
        self,
        step_id: str,
        reason: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Registra un paso bloqueado.
        """

        record = self._build_step_record(
            step_id=step_id,
            status="blocked",
            result=result,
        )

        record["reason"] = str(
            reason
        ).strip()

        self.blocked_steps.append(record)

    def add_error(
        self,
        message: str,
        step_id: Optional[str] = None,
        error_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Registra un error general o asociado a un paso.
        """

        normalized_message = str(
            message
        ).strip()

        if not normalized_message:
            raise ValueError(
                "El mensaje de error no puede estar vacío."
            )

        self.errors.append(
            {
                "message": normalized_message,
                "step_id": (
                    str(step_id).strip()
                    if step_id is not None
                    else None
                ),
                "error_type": (
                    str(error_type).strip()
                    if error_type is not None
                    else None
                ),
                "details": deepcopy(
                    dict(details or {})
                ),
                "created_at": (
                    datetime.now().isoformat()
                ),
            }
        )

    def set_final_output(
        self,
        output: Any,
    ) -> None:
        """
        Guarda la salida final consolidada.
        """

        self.final_output = deepcopy(output)

    def set_context(
        self,
        context: Dict[str, Any],
    ) -> None:
        """
        Guarda el snapshot final del contexto.
        """

        self.context = deepcopy(
            dict(context or {})
        )

    def merge_metadata(
        self,
        metadata: Dict[str, Any],
    ) -> None:
        """
        Incorpora metadata adicional.
        """

        if metadata:
            self.metadata.update(
                deepcopy(dict(metadata))
            )

    def complete(
        self,
        final_output: Any = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Finaliza correctamente el workflow.
        """

        if final_output is not None:
            self.set_final_output(final_output)

        if context is not None:
            self.set_context(context)

        self.status = (
            WorkflowResultStatus.COMPLETED
        )

        self._finish()

    def complete_partial(
        self,
        final_output: Any = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Finaliza con resultados parciales.
        """

        if final_output is not None:
            self.set_final_output(final_output)

        if context is not None:
            self.set_context(context)

        self.status = (
            WorkflowResultStatus.PARTIAL
        )

        self._finish()

    def fail(
        self,
        error: str,
        final_output: Any = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Finaliza el workflow como fallido.
        """

        self.add_error(
            message=error,
            error_type="workflow-error",
        )

        if final_output is not None:
            self.set_final_output(final_output)

        if context is not None:
            self.set_context(context)

        self.status = WorkflowResultStatus.FAILED
        self._finish()

    def cancel(
        self,
        reason: str,
    ) -> None:
        """
        Marca el workflow como cancelado.
        """

        self.add_error(
            message=reason,
            error_type="workflow-cancelled",
        )

        self.status = (
            WorkflowResultStatus.CANCELLED
        )

        self._finish()

    def build_summary(self) -> Dict[str, Any]:
        """
        Devuelve un resumen compacto.
        """

        return {
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "status": self.status.value,
            "total_steps": self.total_steps,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "blocked_count": self.blocked_count,
            "success_rate": self.success_rate,
            "has_errors": self.has_errors,
            "duration_seconds": (
                self.duration_seconds
            ),
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializa el resultado completo.

        Mantiene compatibilidad con consumidores que esperan
        métricas en el primer nivel y además conserva
        el bloque "summary".
        """

        summary = self.build_summary()

        return {
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "request": self.request,
            "status": self.status.value,

            # Compatibilidad
            "total_steps": summary["total_steps"],
            "completed_count": summary["completed_count"],
            "failed_count": summary["failed_count"],
            "skipped_count": summary["skipped_count"],
            "blocked_count": summary["blocked_count"],
            "success_rate": summary["success_rate"],
            "has_errors": summary["has_errors"],

            # Resumen completo
            "summary": summary,

            "completed_steps": deepcopy(
                self.completed_steps
            ),
            "failed_steps": deepcopy(
                self.failed_steps
            ),
            "skipped_steps": deepcopy(
                self.skipped_steps
            ),
            "blocked_steps": deepcopy(
                self.blocked_steps
            ),

            "final_output": deepcopy(
                self.final_output
            ),

            "context": deepcopy(
                self.context
            ),

            "metadata": deepcopy(
                self.metadata
            ),

            "errors": deepcopy(
                self.errors
            ),

            "started_at": (
                self.started_at.isoformat()
            ),

            "finished_at": (
                self.finished_at.isoformat()
                if self.finished_at
                else None
            ),

            "duration_seconds": (
                self.duration_seconds
            ),
        }
    def _build_step_record(
        self,
        step_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        duration_seconds: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Construye el registro estándar de un paso.
        """

        normalized_step_id = str(
            step_id
        ).strip()

        if not normalized_step_id:
            raise ValueError(
                "step_id no puede estar vacío."
            )

        return {
            "step_id": normalized_step_id,
            "status": str(status).strip(),
            "result": deepcopy(
                dict(result or {})
            ),
            "duration_seconds": round(
                float(duration_seconds or 0.0),
                6,
            ),
            "created_at": (
                datetime.now().isoformat()
            ),
        }

    def _finish(self) -> None:
        """
        Registra la finalización y duración.
        """

        self.finished_at = datetime.now()

        self.duration_seconds = round(
            (
                self.finished_at
                - self.started_at
            ).total_seconds(),
            6,
        )

    def __repr__(self) -> str:
        return (
            "WorkflowResult("
            f"workflow_id='{self.workflow_id}', "
            f"execution_id='{self.execution_id}', "
            f"status='{self.status.value}', "
            f"completed={self.completed_count}, "
            f"failed={self.failed_count}, "
            f"skipped={self.skipped_count}, "
            f"blocked={self.blocked_count}"
            ")"
        )