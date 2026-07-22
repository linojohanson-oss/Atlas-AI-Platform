"""
Atlas AI OS - Execution Timeline

Registro cronológico de eventos de ejecución de workflows.

Este componente escucha el WorkflowEventBus y construye una
línea de tiempo estructurada de cada ejecución.

No modifica el estado del workflow.
No ejecuta lógica.
Únicamente registra eventos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Any, Dict, List, Optional


@dataclass
class TimelineEvent:
    """
    Evento individual dentro de la línea de tiempo.
    """

    timestamp: datetime
    event_type: str

    workflow_id: Optional[str] = None
    workflow_name: Optional[str] = None
    execution_id: Optional[str] = None

    step_id: Optional[str] = None
    step_name: Optional[str] = None

    department_id: Optional[str] = None
    agent_id: Optional[str] = None

    status: Optional[str] = None

    message: Optional[str] = None

    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:

        return {

            "timestamp": self.timestamp.isoformat(),

            "event_type": self.event_type,

            "workflow_id": self.workflow_id,

            "workflow_name": self.workflow_name,

            "execution_id": self.execution_id,

            "step_id": self.step_id,

            "step_name": self.step_name,

            "department_id": self.department_id,

            "agent_id": self.agent_id,

            "status": self.status,

            "message": self.message,

            "data": dict(self.data),
        }

    def __repr__(self) -> str:

        return (

            f"TimelineEvent("

            f"{self.timestamp.strftime('%H:%M:%S.%f')[:-3]} "

            f"{self.event_type}"

            f")"

        )


class ExecutionTimeline:
    """
    Historial cronológico de una ejecución.
    """

    def __init__(self):

        self._lock = RLock()

        self.events: List[TimelineEvent] = []

    # =====================================================
    # EventBus
    # =====================================================

    def on_event(self, event) -> None:

        with self._lock:

            event_type = getattr(
                event,
                "event_type",
                None,
            )

            if hasattr(event_type, "value"):
                event_type = event_type.value

            timestamp = getattr(
                event,
                "timestamp",
                None,
            )

            if timestamp is None:
                timestamp = datetime.now()

            data = getattr(
                event,
                "data",
                {},
            )

            timeline_event = TimelineEvent(

                timestamp=timestamp,

                event_type=str(event_type),

                workflow_id=getattr(
                    event,
                    "workflow_id",
                    None,
                ),

                workflow_name=getattr(
                    event,
                    "workflow_name",
                    None,
                ),

                execution_id=getattr(
                    event,
                    "execution_id",
                    None,
                ),

                step_id=getattr(
                    event,
                    "step_id",
                    None,
                ),

                step_name=data.get(
                    "step_name",
                ),

                department_id=data.get(
                    "department_id",
                ),

                agent_id=data.get(
                    "agent_id",
                ),

                status=data.get(
                    "status",
                ),

                message=self._build_message(
                    str(event_type),
                    data,
                ),

                data=dict(data),
            )

            self.events.append(
                timeline_event
            )

    # =====================================================
    # Timeline
    # =====================================================

    def events_count(self) -> int:

        with self._lock:
            return len(self.events)

    def clear(self) -> None:

        with self._lock:
            self.events.clear()

    def latest(
        self,
        limit: int = 10,
    ) -> List[TimelineEvent]:

        with self._lock:

            return self.events[-limit:]

    def to_dict(self) -> List[Dict[str, Any]]:

        with self._lock:

            return [

                event.to_dict()

                for event in self.events

            ]

    # =====================================================
    # Mensajes
    # =====================================================

    @staticmethod
    def _build_message(
        event_type: str,
        data: Dict[str, Any],
    ) -> str:

        mapping = {

            "workflow-started":
                "Workflow iniciado",

            "workflow-finished":
                "Workflow completado",

            "workflow-failed":
                "Workflow falló",

            "step-started":
                f"Paso iniciado: {data.get('step_name')}",

            "step-completed":
                f"Paso completado: {data.get('step_name')}",

            "step-failed":
                f"Paso falló: {data.get('step_name')}",

            "step-skipped":
                f"Paso omitido: {data.get('step_name')}",

            "step-blocked":
                f"Paso bloqueado: {data.get('step_name')}",
        }

        return mapping.get(
            event_type,
            event_type,
        )

    # =====================================================
    # Resumen
    # =====================================================

    def summary(self) -> Dict[str, Any]:

        with self._lock:

            return {

                "events": len(
                    self.events
                ),

                "first_event": (

                    self.events[0].event_type

                    if self.events

                    else None

                ),

                "last_event": (

                    self.events[-1].event_type

                    if self.events

                    else None

                ),
            }

    def __repr__(self):

        return (

            "ExecutionTimeline("

            f"events={len(self.events)}"

            ")"

        )