"""
Atlas AI Platform - Workflow Event Bus

Bus de eventos especializado para ejecuciones de workflows.

Permite publicar y escuchar eventos en tiempo real sin acoplar
el WorkflowEngine con la consola, la API, el dashboard o cualquier
otra interfaz.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from threading import RLock
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4


class WorkflowEventType(str, Enum):
    """
    Tipos de eventos emitidos durante la ejecución de workflows.
    """

    WORKFLOW_STARTED = "workflow-started"
    WORKFLOW_FINISHED = "workflow-finished"
    WORKFLOW_FAILED = "workflow-failed"

    STEP_READY = "step-ready"
    STEP_STARTED = "step-started"
    STEP_COMPLETED = "step-completed"
    STEP_FAILED = "step-failed"
    STEP_SKIPPED = "step-skipped"
    STEP_BLOCKED = "step-blocked"

    EXECUTION_PROGRESS = "execution-progress"


class WorkflowEvent:
    """
    Representa un evento individual del sistema de workflows.
    """

    def __init__(
        self,
        event_type: str,
        execution_id: str,
        workflow_id: str,
        step_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        normalized_event_type = str(
            event_type
        ).strip()

        normalized_execution_id = str(
            execution_id
        ).strip()

        normalized_workflow_id = str(
            workflow_id
        ).strip()

        if not normalized_event_type:
            raise ValueError(
                "event_type no puede estar vacío."
            )

        if not normalized_execution_id:
            raise ValueError(
                "execution_id no puede estar vacío."
            )

        if not normalized_workflow_id:
            raise ValueError(
                "workflow_id no puede estar vacío."
            )

        self.event_id = str(uuid4())

        self.event_type = normalized_event_type
        self.execution_id = normalized_execution_id
        self.workflow_id = normalized_workflow_id

        self.step_id = (
            str(step_id).strip()
            if step_id is not None
            else None
        )

        self.data = dict(data or {})
        self.metadata = dict(metadata or {})

        self.created_at = (
            datetime.now().isoformat()
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializa el evento.
        """

        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "step_id": self.step_id,
            "data": dict(self.data),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            "WorkflowEvent("
            f"event_type='{self.event_type}', "
            f"workflow_id='{self.workflow_id}', "
            f"execution_id='{self.execution_id}', "
            f"step_id='{self.step_id}'"
            ")"
        )


WorkflowEventHandler = Callable[
    [WorkflowEvent],
    None,
]


class WorkflowEventBus:
    """
    Bus de eventos para WorkflowEngine.

    Características:

    - Suscripción global.
    - Suscripción por tipo de evento.
    - Historial de eventos.
    - Consulta por ejecución.
    - Manejo seguro de múltiples hilos.
    - Aislamiento de errores en listeners.
    """

    def __init__(
        self,
        history_limit: int = 1000,
    ) -> None:
        if history_limit < 1:
            raise ValueError(
                "history_limit debe ser mayor que cero."
            )

        self.history_limit = history_limit

        self._global_subscribers: Dict[
            str,
            WorkflowEventHandler,
        ] = {}

        self._typed_subscribers: Dict[
            str,
            Dict[
                str,
                WorkflowEventHandler,
            ],
        ] = {}

        self._history: List[
            WorkflowEvent
        ] = []

        self._listener_errors: List[
            Dict[str, Any]
        ] = []

        self._published_count = 0
        self._lock = RLock()

    # ============================================================
    # Suscripciones
    # ============================================================

    def subscribe(
        self,
        handler: WorkflowEventHandler,
        event_type: Optional[str] = None,
    ) -> str:
        """
        Registra un listener.

        Si event_type es None, recibe todos los eventos.
        Devuelve un subscription_id para cancelar la suscripción.
        """

        if not callable(handler):
            raise TypeError(
                "handler debe ser callable."
            )

        subscription_id = str(uuid4())

        with self._lock:
            if event_type is None:
                self._global_subscribers[
                    subscription_id
                ] = handler

                return subscription_id

            normalized_event_type = str(
                event_type
            ).strip()

            if not normalized_event_type:
                raise ValueError(
                    "event_type no puede estar vacío."
                )

            subscribers = (
                self._typed_subscribers
                .setdefault(
                    normalized_event_type,
                    {},
                )
            )

            subscribers[
                subscription_id
            ] = handler

        return subscription_id

    def unsubscribe(
        self,
        subscription_id: str,
    ) -> bool:
        """
        Elimina una suscripción.

        Devuelve True si fue encontrada.
        """

        normalized_id = str(
            subscription_id
        ).strip()

        if not normalized_id:
            return False

        with self._lock:
            if (
                normalized_id
                in self._global_subscribers
            ):
                del self._global_subscribers[
                    normalized_id
                ]

                return True

            for subscribers in (
                self._typed_subscribers.values()
            ):
                if normalized_id in subscribers:
                    del subscribers[
                        normalized_id
                    ]

                    return True

        return False

    def clear_subscribers(self) -> None:
        """
        Elimina todos los listeners registrados.
        """

        with self._lock:
            self._global_subscribers.clear()
            self._typed_subscribers.clear()

    # ============================================================
    # Publicación
    # ============================================================

    def publish(
        self,
        event_type: str,
        execution_id: str,
        workflow_id: str,
        step_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowEvent:
        """
        Crea y publica un evento.
        """

        event = WorkflowEvent(
            event_type=event_type,
            execution_id=execution_id,
            workflow_id=workflow_id,
            step_id=step_id,
            data=data,
            metadata=metadata,
        )

        self.publish_event(event)

        return event

    def publish_event(
        self,
        event: WorkflowEvent,
    ) -> None:
        """
        Publica una instancia WorkflowEvent existente.
        """

        if not isinstance(
            event,
            WorkflowEvent,
        ):
            raise TypeError(
                "event debe ser WorkflowEvent."
            )

        with self._lock:
            self._history.append(event)
            self._published_count += 1

            if (
                len(self._history)
                > self.history_limit
            ):
                excess = (
                    len(self._history)
                    - self.history_limit
                )

                del self._history[:excess]

            global_handlers = list(
                self._global_subscribers.values()
            )

            typed_handlers = list(
                self._typed_subscribers.get(
                    event.event_type,
                    {},
                ).values()
            )

        handlers = (
            global_handlers
            + typed_handlers
        )

        for handler in handlers:
            try:
                handler(event)

            except Exception as error:
                self._record_listener_error(
                    event=event,
                    handler=handler,
                    error=error,
                )

    # ============================================================
    # Historial
    # ============================================================

    def history(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Devuelve el historial global serializado.
        """

        with self._lock:
            events = list(self._history)

        if limit is not None:
            if limit < 1:
                return []

            events = events[-limit:]

        return [
            event.to_dict()
            for event in events
        ]

    def execution_history(
        self,
        execution_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Devuelve los eventos de una ejecución específica.
        """

        normalized_execution_id = str(
            execution_id
        ).strip()

        if not normalized_execution_id:
            return []

        with self._lock:
            events = [
                event
                for event in self._history
                if (
                    event.execution_id
                    == normalized_execution_id
                )
            ]

        if limit is not None:
            if limit < 1:
                return []

            events = events[-limit:]

        return [
            event.to_dict()
            for event in events
        ]

    def workflow_history(
        self,
        workflow_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Devuelve los eventos de un workflow específico.
        """

        normalized_workflow_id = str(
            workflow_id
        ).strip()

        if not normalized_workflow_id:
            return []

        with self._lock:
            events = [
                event
                for event in self._history
                if (
                    event.workflow_id
                    == normalized_workflow_id
                )
            ]

        if limit is not None:
            if limit < 1:
                return []

            events = events[-limit:]

        return [
            event.to_dict()
            for event in events
        ]

    def latest_event(
        self,
        execution_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Devuelve el último evento global o de una ejecución.
        """

        with self._lock:
            if execution_id is None:
                if not self._history:
                    return None

                return self._history[
                    -1
                ].to_dict()

            normalized_execution_id = str(
                execution_id
            ).strip()

            for event in reversed(
                self._history
            ):
                if (
                    event.execution_id
                    == normalized_execution_id
                ):
                    return event.to_dict()

        return None

    def clear_history(self) -> None:
        """
        Elimina el historial almacenado.
        """

        with self._lock:
            self._history.clear()
            self._listener_errors.clear()

    # ============================================================
    # Errores de listeners
    # ============================================================

    def _record_listener_error(
        self,
        event: WorkflowEvent,
        handler: WorkflowEventHandler,
        error: Exception,
    ) -> None:
        handler_name = getattr(
            handler,
            "__name__",
            handler.__class__.__name__,
        )

        error_data = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "execution_id": (
                event.execution_id
            ),
            "handler": handler_name,
            "error": str(error),
            "created_at": (
                datetime.now().isoformat()
            ),
        }

        with self._lock:
            self._listener_errors.append(
                error_data
            )

            if (
                len(self._listener_errors)
                > self.history_limit
            ):
                excess = (
                    len(self._listener_errors)
                    - self.history_limit
                )

                del self._listener_errors[
                    :excess
                ]

    def listener_errors(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Devuelve los errores producidos por listeners.
        """

        with self._lock:
            errors = [
                dict(item)
                for item
                in self._listener_errors
            ]

        if limit is not None:
            if limit < 1:
                return []

            errors = errors[-limit:]

        return errors

    # ============================================================
    # Información operativa
    # ============================================================

    @property
    def published_count(self) -> int:
        return self._published_count

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            typed_count = sum(
                len(subscribers)
                for subscribers
                in self._typed_subscribers.values()
            )

            return (
                len(self._global_subscribers)
                + typed_count
            )

    def summary(self) -> Dict[str, Any]:
        """
        Devuelve un resumen del bus.
        """

        with self._lock:
            return {
                "published_count": (
                    self._published_count
                ),
                "history_count": (
                    len(self._history)
                ),
                "history_limit": (
                    self.history_limit
                ),
                "subscriber_count": (
                    self.subscriber_count
                ),
                "global_subscribers": (
                    len(
                        self._global_subscribers
                    )
                ),
                "typed_event_groups": (
                    len(
                        self._typed_subscribers
                    )
                ),
                "listener_error_count": (
                    len(
                        self._listener_errors
                    )
                ),
            }

    def __repr__(self) -> str:
        return (
            "WorkflowEventBus("
            f"events={self._published_count}, "
            f"subscribers="
            f"{self.subscriber_count}"
            ")"
        )