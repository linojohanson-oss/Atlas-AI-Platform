"""
Atlas AI OS - Workflow Performance Profiler

Recolecta y calcula métricas de rendimiento a partir de los eventos
publicados por WorkflowEventBus.

Responsabilidades:
- Medir la duración total del workflow.
- Medir la duración de cada paso.
- Agrupar tiempos por departamento.
- Agrupar tiempos por agente.
- Detectar pasos lentos.
- Generar resúmenes serializables.

Este componente no ejecuta workflows ni modifica su estado.
Únicamente consume eventos de observabilidad.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Any, Dict, List, Optional


# ============================================================
# Utilidades
# ============================================================

def _normalize_event_type(event_type: Any) -> str:
    """
    Convierte un tipo de evento enum o string en un string normalizado.
    """

    if hasattr(event_type, "value"):
        event_type = event_type.value

    return str(event_type or "")


def _normalize_timestamp(timestamp: Any) -> datetime:
    """
    Convierte el timestamp recibido en datetime.

    Si el evento no contiene timestamp válido, utiliza datetime.now().
    """

    if isinstance(timestamp, datetime):
        return timestamp

    if isinstance(timestamp, str):
        try:
            return datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            )
        except ValueError:
            pass

    return datetime.now()


def _duration_seconds(
    started_at: Optional[datetime],
    completed_at: Optional[datetime],
) -> Optional[float]:
    """
    Calcula una duración en segundos.
    """

    if started_at is None or completed_at is None:
        return None

    try:
        return max(
            0.0,
            (completed_at - started_at).total_seconds(),
        )
    except (TypeError, ValueError):
        return None


# ============================================================
# Métrica por paso
# ============================================================

@dataclass
class StepPerformanceMetric:
    """
    Métricas de rendimiento de un paso individual.
    """

    step_id: str

    step_name: Optional[str] = None
    department_id: Optional[str] = None
    agent_id: Optional[str] = None
    step_type: Optional[str] = None

    status: str = "pending"

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    duration_seconds: Optional[float] = None

    error: Optional[str] = None
    reason: Optional[str] = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def start(
        self,
        timestamp: datetime,
    ) -> None:
        """
        Marca el inicio del paso.
        """

        if self.started_at is None:
            self.started_at = timestamp

        self.status = "running"

    def finish(
        self,
        timestamp: datetime,
        status: str,
    ) -> None:
        """
        Marca la finalización del paso y calcula su duración.
        """

        self.completed_at = timestamp
        self.status = status

        self.duration_seconds = _duration_seconds(
            self.started_at,
            self.completed_at,
        )

    @property
    def duration_ms(self) -> Optional[float]:
        """
        Duración del paso en milisegundos.
        """

        if self.duration_seconds is None:
            return None

        return self.duration_seconds * 1000.0

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la métrica en un diccionario serializable.
        """

        return {
            "step_id": self.step_id,
            "step_name": self.step_name,
            "department_id": self.department_id,
            "agent_id": self.agent_id,
            "step_type": self.step_type,
            "status": self.status,
            "started_at": (
                self.started_at.isoformat()
                if self.started_at
                else None
            ),
            "completed_at": (
                self.completed_at.isoformat()
                if self.completed_at
                else None
            ),
            "duration_seconds": self.duration_seconds,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }


# ============================================================
# Performance Profiler
# ============================================================

class WorkflowPerformanceProfiler:
    """
    Analizador de rendimiento de una ejecución de workflow.

    Está diseñado para registrarse como subscriber de
    WorkflowEventBus:

        bus.subscribe(profiler.on_event)
    """

    TERMINAL_STEP_EVENTS = {
        "step-completed": "completed",
        "step-failed": "failed",
        "step-skipped": "skipped",
        "step-blocked": "blocked",
    }

    TERMINAL_WORKFLOW_EVENTS = {
        "workflow-finished": "completed",
        "workflow-failed": "failed",
    }

    def __init__(
        self,
        slow_step_threshold_seconds: float = 1.0,
    ) -> None:

        self._lock = RLock()

        self.slow_step_threshold_seconds = max(
            0.0,
            float(slow_step_threshold_seconds),
        )

        self.workflow_id: Optional[str] = None
        self.workflow_name: Optional[str] = None
        self.execution_id: Optional[str] = None
        self.workflow_version: Optional[str] = None

        self.status: str = "created"

        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.duration_seconds: Optional[float] = None

        self.steps: Dict[str, StepPerformanceMetric] = {}

        self.event_count: int = 0
        self.first_event_type: Optional[str] = None
        self.last_event_type: Optional[str] = None

        self.error: Optional[str] = None

    # ========================================================
    # EventBus
    # ========================================================

    def on_event(
        self,
        event: Any,
    ) -> None:
        """
        Recibe un evento publicado por WorkflowEventBus.
        """

        with self._lock:

            event_type = _normalize_event_type(
                getattr(
                    event,
                    "event_type",
                    None,
                )
            )

            timestamp = _normalize_timestamp(
                getattr(
                    event,
                    "timestamp",
                    None,
                )
            )

            data = getattr(
                event,
                "data",
                {},
            )

            if not isinstance(data, dict):
                data = {}

            self.event_count += 1

            if self.first_event_type is None:
                self.first_event_type = event_type

            self.last_event_type = event_type

            self._update_execution_identity(
                event=event,
                data=data,
            )

            if event_type == "workflow-started":
                self._handle_workflow_started(
                    timestamp=timestamp,
                    data=data,
                )

            elif event_type == "step-started":
                self._handle_step_started(
                    event=event,
                    timestamp=timestamp,
                    data=data,
                )

            elif event_type in self.TERMINAL_STEP_EVENTS:
                self._handle_step_finished(
                    event=event,
                    event_type=event_type,
                    timestamp=timestamp,
                    data=data,
                )

            elif event_type in self.TERMINAL_WORKFLOW_EVENTS:
                self._handle_workflow_finished(
                    event_type=event_type,
                    timestamp=timestamp,
                    data=data,
                )

    # ========================================================
    # Manejo de eventos
    # ========================================================

    def _update_execution_identity(
        self,
        event: Any,
        data: Dict[str, Any],
    ) -> None:
        """
        Actualiza los identificadores generales de la ejecución.
        """

        self.workflow_id = (
            getattr(event, "workflow_id", None)
            or data.get("workflow_id")
            or self.workflow_id
        )

        self.workflow_name = (
            getattr(event, "workflow_name", None)
            or data.get("workflow_name")
            or self.workflow_name
        )

        self.execution_id = (
            getattr(event, "execution_id", None)
            or data.get("execution_id")
            or self.execution_id
        )

    def _handle_workflow_started(
        self,
        timestamp: datetime,
        data: Dict[str, Any],
    ) -> None:
        """
        Registra el comienzo del workflow y crea las métricas
        preliminares de todos los pasos esperados.
        """

        self.status = "running"
        self.started_at = timestamp
        self.completed_at = None
        self.duration_seconds = None
        self.error = None

        self.workflow_name = (
            data.get("workflow_name")
            or self.workflow_name
        )

        self.workflow_version = data.get(
            "workflow_version"
        )

        expected_steps = data.get(
            "expected_steps",
            [],
        )

        if isinstance(expected_steps, list):

            for position, step_data in enumerate(
                expected_steps,
                start=1,
            ):

                if not isinstance(step_data, dict):
                    continue

                step_id = (
                    step_data.get("step_id")
                    or f"step-{position}"
                )

                metric = self._get_or_create_step(
                    step_id=str(step_id)
                )

                metric.step_name = (
                    step_data.get("step_name")
                    or metric.step_name
                )

                metric.department_id = (
                    step_data.get("department_id")
                    or metric.department_id
                )

                metric.agent_id = (
                    step_data.get("agent_id")
                    or metric.agent_id
                )

                metric.step_type = (
                    step_data.get("step_type")
                    or metric.step_type
                )

                metric.metadata["position"] = position

    def _handle_step_started(
        self,
        event: Any,
        timestamp: datetime,
        data: Dict[str, Any],
    ) -> None:
        """
        Registra el inicio de un paso.
        """

        step_id = self._extract_step_id(
            event=event,
            data=data,
        )

        metric = self._get_or_create_step(
            step_id=step_id
        )

        self._update_step_metadata(
            metric=metric,
            event=event,
            data=data,
        )

        metric.start(timestamp)

    def _handle_step_finished(
        self,
        event: Any,
        event_type: str,
        timestamp: datetime,
        data: Dict[str, Any],
    ) -> None:
        """
        Registra la finalización de un paso.
        """

        step_id = self._extract_step_id(
            event=event,
            data=data,
        )

        metric = self._get_or_create_step(
            step_id=step_id
        )

        self._update_step_metadata(
            metric=metric,
            event=event,
            data=data,
        )

        # Compatibilidad defensiva:
        # si no llegó step-started, usamos el timestamp final como inicio.
        if metric.started_at is None:
            metric.started_at = timestamp

        status = self.TERMINAL_STEP_EVENTS[
            event_type
        ]

        metric.finish(
            timestamp=timestamp,
            status=status,
        )

        metric.error = (
            data.get("error")
            or data.get("exception")
            or metric.error
        )

        metric.reason = (
            data.get("reason")
            or metric.reason
        )

        reported_duration = self._extract_reported_duration(
            data
        )

        if reported_duration is not None:
            metric.duration_seconds = reported_duration

    def _handle_workflow_finished(
        self,
        event_type: str,
        timestamp: datetime,
        data: Dict[str, Any],
    ) -> None:
        """
        Registra la finalización total del workflow.
        """

        self.completed_at = timestamp

        self.status = self.TERMINAL_WORKFLOW_EVENTS[
            event_type
        ]

        self.duration_seconds = _duration_seconds(
            self.started_at,
            self.completed_at,
        )

        reported_duration = self._extract_reported_duration(
            data
        )

        if reported_duration is not None:
            self.duration_seconds = reported_duration

        if self.status == "failed":
            self.error = (
                data.get("error")
                or data.get("exception")
                or data.get("reason")
                or self.error
            )

    # ========================================================
    # Pasos
    # ========================================================

    def _get_or_create_step(
        self,
        step_id: str,
    ) -> StepPerformanceMetric:
        """
        Obtiene una métrica existente o crea una nueva.
        """

        normalized_step_id = str(
            step_id or "unknown-step"
        )

        if normalized_step_id not in self.steps:
            self.steps[normalized_step_id] = (
                StepPerformanceMetric(
                    step_id=normalized_step_id
                )
            )

        return self.steps[normalized_step_id]

    @staticmethod
    def _extract_step_id(
        event: Any,
        data: Dict[str, Any],
    ) -> str:
        """
        Extrae el identificador del paso.
        """

        step_id = (
            getattr(event, "step_id", None)
            or data.get("step_id")
            or data.get("id")
        )

        if step_id:
            return str(step_id)

        step_name = data.get("step_name")

        if step_name:
            return str(step_name)

        return "unknown-step"

    @staticmethod
    def _update_step_metadata(
        metric: StepPerformanceMetric,
        event: Any,
        data: Dict[str, Any],
    ) -> None:
        """
        Actualiza los datos descriptivos del paso.
        """

        metric.step_name = (
            data.get("step_name")
            or getattr(event, "step_name", None)
            or metric.step_name
        )

        metric.department_id = (
            data.get("department_id")
            or getattr(event, "department_id", None)
            or metric.department_id
        )

        metric.agent_id = (
            data.get("agent_id")
            or getattr(event, "agent_id", None)
            or metric.agent_id
        )

        metric.step_type = (
            data.get("step_type")
            or metric.step_type
        )

    @staticmethod
    def _extract_reported_duration(
        data: Dict[str, Any],
    ) -> Optional[float]:
        """
        Obtiene una duración publicada explícitamente por el motor.

        Reconoce:
        - duration_seconds
        - duration_ms
        """

        duration_seconds = data.get(
            "duration_seconds"
        )

        if duration_seconds is not None:
            try:
                return max(
                    0.0,
                    float(duration_seconds),
                )
            except (TypeError, ValueError):
                pass

        duration_ms = data.get(
            "duration_ms"
        )

        if duration_ms is not None:
            try:
                return max(
                    0.0,
                    float(duration_ms) / 1000.0,
                )
            except (TypeError, ValueError):
                pass

        return None

    # ========================================================
    # Consultas generales
    # ========================================================

    @property
    def duration_ms(self) -> Optional[float]:
        """
        Duración total del workflow en milisegundos.
        """

        if self.duration_seconds is None:
            return None

        return self.duration_seconds * 1000.0

    def total_steps(self) -> int:
        """
        Cantidad total de pasos conocidos.
        """

        with self._lock:
            return len(self.steps)

    def completed_steps(self) -> int:
        """
        Cantidad de pasos completados correctamente.
        """

        with self._lock:
            return sum(
                1
                for metric in self.steps.values()
                if metric.status == "completed"
            )

    def failed_steps(self) -> int:
        """
        Cantidad de pasos fallidos.
        """

        with self._lock:
            return sum(
                1
                for metric in self.steps.values()
                if metric.status == "failed"
            )

    def measured_steps(self) -> int:
        """
        Cantidad de pasos con duración disponible.
        """

        with self._lock:
            return sum(
                1
                for metric in self.steps.values()
                if metric.duration_seconds is not None
            )

    def average_step_duration_seconds(
        self,
    ) -> float:
        """
        Duración promedio de los pasos medidos.
        """

        with self._lock:

            durations = [
                metric.duration_seconds
                for metric in self.steps.values()
                if metric.duration_seconds is not None
            ]

            if not durations:
                return 0.0

            return sum(durations) / len(durations)

    def average_step_duration_ms(
        self,
    ) -> float:
        """
        Duración promedio de los pasos en milisegundos.
        """

        return (
            self.average_step_duration_seconds()
            * 1000.0
        )

    def slowest_step(
        self,
    ) -> Optional[StepPerformanceMetric]:
        """
        Devuelve el paso más lento.
        """

        with self._lock:

            measured = [
                metric
                for metric in self.steps.values()
                if metric.duration_seconds is not None
            ]

            if not measured:
                return None

            return max(
                measured,
                key=lambda metric: (
                    metric.duration_seconds or 0.0
                ),
            )

    def fastest_step(
        self,
    ) -> Optional[StepPerformanceMetric]:
        """
        Devuelve el paso más rápido.
        """

        with self._lock:

            measured = [
                metric
                for metric in self.steps.values()
                if metric.duration_seconds is not None
            ]

            if not measured:
                return None

            return min(
                measured,
                key=lambda metric: (
                    metric.duration_seconds or 0.0
                ),
            )

    def slow_steps(
        self,
    ) -> List[StepPerformanceMetric]:
        """
        Devuelve los pasos que superan el umbral configurado.
        """

        with self._lock:

            return [
                metric
                for metric in self.steps.values()
                if (
                    metric.duration_seconds is not None
                    and metric.duration_seconds
                    >= self.slow_step_threshold_seconds
                )
            ]

    # ========================================================
    # Agregaciones
    # ========================================================

    def duration_by_department(
        self,
    ) -> Dict[str, float]:
        """
        Tiempo acumulado por departamento, en segundos.
        """

        with self._lock:

            totals: Dict[str, float] = {}

            for metric in self.steps.values():

                if metric.duration_seconds is None:
                    continue

                department_id = (
                    metric.department_id
                    or "unassigned"
                )

                totals[department_id] = (
                    totals.get(department_id, 0.0)
                    + metric.duration_seconds
                )

            return dict(
                sorted(
                    totals.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            )

    def duration_by_agent(
        self,
    ) -> Dict[str, float]:
        """
        Tiempo acumulado por agente, en segundos.
        """

        with self._lock:

            totals: Dict[str, float] = {}

            for metric in self.steps.values():

                if metric.duration_seconds is None:
                    continue

                agent_id = (
                    metric.agent_id
                    or "unassigned"
                )

                totals[agent_id] = (
                    totals.get(agent_id, 0.0)
                    + metric.duration_seconds
                )

            return dict(
                sorted(
                    totals.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            )

    def duration_by_department_ms(
        self,
    ) -> Dict[str, float]:
        """
        Tiempo acumulado por departamento, en milisegundos.
        """

        return {
            department: seconds * 1000.0
            for department, seconds
            in self.duration_by_department().items()
        }

    def duration_by_agent_ms(
        self,
    ) -> Dict[str, float]:
        """
        Tiempo acumulado por agente, en milisegundos.
        """

        return {
            agent: seconds * 1000.0
            for agent, seconds
            in self.duration_by_agent().items()
        }

    # ========================================================
    # Serialización
    # ========================================================

    def steps_list(
        self,
    ) -> List[StepPerformanceMetric]:
        """
        Devuelve los pasos respetando su posición original.
        """

        with self._lock:

            return sorted(
                self.steps.values(),
                key=lambda metric: (
                    metric.metadata.get(
                        "position",
                        999999,
                    ),
                    metric.step_id,
                ),
            )

    def to_dict(self) -> Dict[str, Any]:
        """
        Genera una representación completa y serializable.
        """

        with self._lock:

            slowest = self.slowest_step()
            fastest = self.fastest_step()

            return {
                "workflow_id": self.workflow_id,
                "workflow_name": self.workflow_name,
                "workflow_version": self.workflow_version,
                "execution_id": self.execution_id,
                "status": self.status,
                "started_at": (
                    self.started_at.isoformat()
                    if self.started_at
                    else None
                ),
                "completed_at": (
                    self.completed_at.isoformat()
                    if self.completed_at
                    else None
                ),
                "duration_seconds": self.duration_seconds,
                "duration_ms": self.duration_ms,
                "event_count": self.event_count,
                "first_event_type": self.first_event_type,
                "last_event_type": self.last_event_type,
                "total_steps": len(self.steps),
                "completed_steps": self.completed_steps(),
                "failed_steps": self.failed_steps(),
                "measured_steps": self.measured_steps(),
                "average_step_duration_seconds": (
                    self.average_step_duration_seconds()
                ),
                "average_step_duration_ms": (
                    self.average_step_duration_ms()
                ),
                "slowest_step": (
                    slowest.to_dict()
                    if slowest
                    else None
                ),
                "fastest_step": (
                    fastest.to_dict()
                    if fastest
                    else None
                ),
                "slow_step_threshold_seconds": (
                    self.slow_step_threshold_seconds
                ),
                "slow_steps": [
                    metric.to_dict()
                    for metric in self.slow_steps()
                ],
                "duration_by_department_seconds": (
                    self.duration_by_department()
                ),
                "duration_by_department_ms": (
                    self.duration_by_department_ms()
                ),
                "duration_by_agent_seconds": (
                    self.duration_by_agent()
                ),
                "duration_by_agent_ms": (
                    self.duration_by_agent_ms()
                ),
                "steps": [
                    metric.to_dict()
                    for metric in self.steps_list()
                ],
                "error": self.error,
            }

    def summary(self) -> Dict[str, Any]:
        """
        Devuelve un resumen compacto de rendimiento.
        """

        with self._lock:

            slowest = self.slowest_step()

            return {
                "workflow_id": self.workflow_id,
                "execution_id": self.execution_id,
                "status": self.status,
                "duration_ms": self.duration_ms,
                "total_steps": len(self.steps),
                "completed_steps": self.completed_steps(),
                "failed_steps": self.failed_steps(),
                "average_step_duration_ms": (
                    self.average_step_duration_ms()
                ),
                "slowest_step": (
                    slowest.step_name
                    or slowest.step_id
                    if slowest
                    else None
                ),
                "slowest_step_duration_ms": (
                    slowest.duration_ms
                    if slowest
                    else None
                ),
                "event_count": self.event_count,
            }

    # ========================================================
    # Reinicio
    # ========================================================

    def reset(self) -> None:
        """
        Reinicia completamente el profiler.
        """

        with self._lock:

            self.workflow_id = None
            self.workflow_name = None
            self.execution_id = None
            self.workflow_version = None

            self.status = "created"

            self.started_at = None
            self.completed_at = None
            self.duration_seconds = None

            self.steps.clear()

            self.event_count = 0
            self.first_event_type = None
            self.last_event_type = None

            self.error = None

    def __repr__(self) -> str:

        return (
            "WorkflowPerformanceProfiler("
            f"status={self.status!r}, "
            f"steps={len(self.steps)}, "
            f"events={self.event_count}"
            ")"
        )


# Alias breve y cómodo para uso público.
PerformanceProfiler = WorkflowPerformanceProfiler