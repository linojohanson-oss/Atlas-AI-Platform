"""
Atlas AI Platform - WebSocket Manager

Administra las conexiones WebSocket de Atlas Studio y actúa
como adaptador entre WorkflowEventBus y los clientes web.

El WorkflowEventBus publica eventos de forma síncrona.
FastAPI envía mensajes WebSocket de forma asíncrona.

Este componente conecta ambos modelos sin acoplar el motor
de workflows con la interfaz web.
"""

from __future__ import annotations

import asyncio
from threading import RLock
from typing import Any, Dict, List, Optional

from fastapi import WebSocket

from atlas.workflows.workflow_event_bus import (
    WorkflowEvent,
    WorkflowEventBus,
)


class WebSocketManager:
    """
    Administra clientes WebSocket conectados a Atlas Studio.

    Responsabilidades:

    - Registrar y eliminar clientes.
    - Enviar mensajes a todos los clientes conectados.
    - Recibir eventos de WorkflowEventBus.
    - Transferir eventos síncronos al event loop asíncrono.
    - Eliminar conexiones que hayan quedado cerradas.
    """

    def __init__(self) -> None:
        self._connections: List[WebSocket] = []
        self._lock = RLock()

        self._event_loop: Optional[
            asyncio.AbstractEventLoop
        ] = None

        self._event_bus: Optional[
            WorkflowEventBus
        ] = None

        self._subscription_id: Optional[
            str
        ] = None

        self._received_events = 0
        self._broadcast_count = 0
        self._failed_deliveries = 0

    # ============================================================
    # Ciclo de vida
    # ============================================================

    def start(
        self,
        event_bus: WorkflowEventBus,
        event_loop: asyncio.AbstractEventLoop,
    ) -> None:
        """
        Conecta el manager con WorkflowEventBus.

        Debe llamarse durante el inicio de FastAPI, cuando ya existe
        un event loop activo.
        """

        if not isinstance(
            event_bus,
            WorkflowEventBus,
        ):
            raise TypeError(
                "event_bus debe ser WorkflowEventBus."
            )

        if event_loop is None:
            raise ValueError(
                "event_loop no puede ser None."
            )

        if event_loop.is_closed():
            raise RuntimeError(
                "El event loop está cerrado."
            )

        with self._lock:
            if self._subscription_id is not None:
                return

            self._event_bus = event_bus
            self._event_loop = event_loop

            self._subscription_id = (
                event_bus.subscribe(
                    self.on_workflow_event
                )
            )

    def stop(self) -> None:
        """
        Cancela la suscripción al EventBus y limpia el estado.
        """

        with self._lock:
            event_bus = self._event_bus
            subscription_id = (
                self._subscription_id
            )

            self._event_bus = None
            self._subscription_id = None
            self._event_loop = None

        if (
            event_bus is not None
            and subscription_id is not None
        ):
            event_bus.unsubscribe(
                subscription_id
            )

    # ============================================================
    # Conexiones
    # ============================================================

    async def connect(
        self,
        websocket: WebSocket,
    ) -> None:
        """
        Acepta y registra una conexión WebSocket.
        """

        await websocket.accept()

        with self._lock:
            if websocket not in self._connections:
                self._connections.append(
                    websocket
                )

        await websocket.send_json(
            {
                "type": "atlas-studio-connected",
                "data": {
                    "message": (
                        "Conexión en tiempo real establecida."
                    ),
                    "connected_clients": (
                        self.connection_count
                    ),
                },
            }
        )

    def disconnect(
        self,
        websocket: WebSocket,
    ) -> bool:
        """
        Elimina una conexión registrada.
        """

        with self._lock:
            if websocket not in self._connections:
                return False

            self._connections.remove(
                websocket
            )

        return True

    # ============================================================
    # Eventos
    # ============================================================

    def on_workflow_event(
        self,
        event: WorkflowEvent,
    ) -> None:
        """
        Listener síncrono registrado en WorkflowEventBus.

        Transfiere el envío al event loop de FastAPI para no bloquear
        la ejecución del workflow.
        """

        if not isinstance(
            event,
            WorkflowEvent,
        ):
            return

        with self._lock:
            self._received_events += 1
            event_loop = self._event_loop

        if (
            event_loop is None
            or event_loop.is_closed()
        ):
            return

        message = {
            "type": "workflow-event",
            "data": event.to_dict(),
        }

        try:
            asyncio.run_coroutine_threadsafe(
                self.broadcast(message),
                event_loop,
            )

        except RuntimeError:
            with self._lock:
                self._failed_deliveries += 1

    async def broadcast(
        self,
        message: Dict[str, Any],
    ) -> None:
        """
        Envía un mensaje a todos los clientes conectados.
        """

        with self._lock:
            connections = list(
                self._connections
            )

        if not connections:
            return

        disconnected: List[
            WebSocket
        ] = []

        delivered = 0

        for websocket in connections:
            try:
                await websocket.send_json(
                    message
                )

                delivered += 1

            except Exception:
                disconnected.append(
                    websocket
                )

                with self._lock:
                    self._failed_deliveries += 1

        for websocket in disconnected:
            self.disconnect(
                websocket
            )

        with self._lock:
            self._broadcast_count += (
                delivered
            )

    # ============================================================
    # Información operativa
    # ============================================================

    @property
    def connection_count(self) -> int:
        with self._lock:
            return len(
                self._connections
            )

    @property
    def is_started(self) -> bool:
        with self._lock:
            return (
                self._subscription_id
                is not None
            )

    def summary(self) -> Dict[str, Any]:
        """
        Devuelve el estado operativo del manager.
        """

        with self._lock:
            return {
                "started": (
                    self._subscription_id
                    is not None
                ),
                "connected_clients": len(
                    self._connections
                ),
                "received_events": (
                    self._received_events
                ),
                "broadcast_count": (
                    self._broadcast_count
                ),
                "failed_deliveries": (
                    self._failed_deliveries
                ),
                "subscription_id": (
                    self._subscription_id
                ),
            }

    def __repr__(self) -> str:
        return (
            "WebSocketManager("
            f"started={self.is_started}, "
            f"connections={self.connection_count}"
            ")"
        )


websocket_manager = WebSocketManager()