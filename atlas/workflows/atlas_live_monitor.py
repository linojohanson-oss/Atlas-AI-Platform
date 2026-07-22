"""
Atlas AI OS - Atlas Live Monitor

Monitor de consola para visualizar en tiempo real el estado de una
ejecución de workflow.

Responsabilidades:

- Consultar WorkflowExecutionState.
- Representar visualmente el progreso.
- Mostrar pasos, departamentos y eventos.
- Actualizar la pantalla cuando recibe una notificación.

No ejecuta workflows ni modifica su lógica.
"""

from __future__ import annotations

import os
from datetime import datetime
from threading import RLock
from typing import Any, Dict, Optional

from atlas.workflows.workflow_execution_state import (
    WorkflowExecutionState,
)


class AtlasLiveMonitor:
    """
    Monitor de consola para ejecuciones de workflows.

    Ejemplo:

        state = WorkflowExecutionState()
        monitor = AtlasLiveMonitor(state)

        event_bus.subscribe(state.on_event)
        event_bus.subscribe(monitor.on_event)
    """

    STATUS_ICONS = {
        "created": "[ ]",
        "pending": "[ ]",
        "waiting": "[ ]",
        "running": "[>]",
        "completed": "[OK]",
        "failed": "[ERROR]",
        "blocked": "[BLOCKED]",
        "skipped": "[SKIP]",
        "cancelled": "[CANCEL]",
        "partial": "[PARTIAL]",
    }

    STATUS_LABELS = {
        "created": "CREADO",
        "pending": "PENDIENTE",
        "waiting": "ESPERANDO",
        "running": "EJECUTANDO",
        "completed": "COMPLETADO",
        "failed": "FALLIDO",
        "blocked": "BLOQUEADO",
        "skipped": "OMITIDO",
        "cancelled": "CANCELADO",
        "partial": "PARCIAL",
    }

    def __init__(
        self,
        state: WorkflowExecutionState,
        auto_clear: bool = True,
        progress_width: int = 40,
        show_outputs: bool = False,
    ) -> None:
        """
        Inicializa el monitor.

        Args:
            state:
                Estado vivo que será representado.

            auto_clear:
                Limpia la consola antes de cada actualización.

            progress_width:
                Ancho de la barra de progreso.

            show_outputs:
                Muestra una vista resumida de la salida de cada paso.
        """

        if not isinstance(
            state,
            WorkflowExecutionState,
        ):
            raise TypeError(
                "state debe ser una instancia de "
                "WorkflowExecutionState."
            )

        self.state = state
        self.auto_clear = auto_clear
        self.progress_width = max(
            10,
            int(progress_width),
        )
        self.show_outputs = show_outputs

        self._lock = RLock()
        self._render_count = 0
        self._last_rendered_event: Optional[str] = None

    # ========================================================
    # Integración con EventBus
    # ========================================================

    def on_event(self, event: Any) -> None:
        """
        Listener para WorkflowEventBus.

        El estado debe estar suscrito antes que el monitor:

            bus.subscribe(state.on_event)
            bus.subscribe(monitor.on_event)
        """

        event_type = getattr(
            event,
            "event_type",
            None,
        )

        if hasattr(event_type, "value"):
            event_type = event_type.value

        self._last_rendered_event = (
            str(event_type)
            if event_type is not None
            else None
        )

        self.render()

    # ========================================================
    # Render principal
    # ========================================================

    def render(self) -> None:
        """
        Dibuja el estado actual en la consola.
        """

        with self._lock:
            snapshot = self.state.snapshot()

            self._clear_console()
            self._render_count += 1

            print("=" * 72)
            print("                        ATLAS LIVE MONITOR")
            print("=" * 72)

            self._render_workflow_header(snapshot)
            self._render_progress(snapshot)
            self._render_steps(snapshot)
            self._render_last_event(snapshot)
            self._render_footer(snapshot)

    # ========================================================
    # Secciones visuales
    # ========================================================

    def _render_workflow_header(
        self,
        snapshot: Dict[str, Any],
    ) -> None:
        workflow_name = (
            snapshot.get("workflow_name")
            or snapshot.get("workflow_id")
            or "Workflow sin identificar"
        )

        workflow_id = (
            snapshot.get("workflow_id")
            or "-"
        )

        execution_id = (
            snapshot.get("execution_id")
            or "-"
        )

        status = snapshot.get(
            "status",
            "created",
        )

        started_at = self._format_datetime(
            snapshot.get("started_at")
        )

        duration = self._format_duration(
            snapshot.get("duration_seconds")
        )

        print()
        print(f"Workflow      : {workflow_name}")
        print(f"Workflow ID   : {workflow_id}")
        print(f"Ejecucion ID  : {execution_id}")
        print(
            f"Estado        : "
            f"{self._status_label(status)}"
        )
        print(f"Inicio        : {started_at}")
        print(f"Duracion      : {duration}")

    def _render_progress(
        self,
        snapshot: Dict[str, Any],
    ) -> None:
        progress = float(
            snapshot.get(
                "progress",
                0.0,
            )
        )

        progress = max(
            0.0,
            min(100.0, progress),
        )

        completed = snapshot.get(
            "completed_count",
            0,
        )
        total = snapshot.get(
            "total_steps",
            0,
        )

        bar = self._progress_bar(progress)

        print()
        print("-" * 72)
        print("PROGRESO")
        print("-" * 72)
        print(
            f"{bar} "
            f"{progress:6.2f}%"
        )
        print(
            f"Pasos completados: "
            f"{completed}/{total}"
        )

    def _render_steps(
        self,
        snapshot: Dict[str, Any],
    ) -> None:
        steps = snapshot.get(
            "steps",
            {},
        )

        print()
        print("-" * 72)
        print("EJECUCION")
        print("-" * 72)

        if not steps:
            print("Todavia no se registraron pasos.")
            return

        for index, step in enumerate(
            steps.values(),
            start=1,
        ):
            self._render_step(
                index=index,
                step=step,
            )

    def _render_step(
        self,
        index: int,
        step: Dict[str, Any],
    ) -> None:
        status = step.get(
            "status",
            "pending",
        )

        icon = self.STATUS_ICONS.get(
            status,
            "[?]",
        )

        name = (
            step.get("step_name")
            or step.get("step_id")
            or "Paso sin nombre"
        )

        department = (
            step.get("department_id")
            or "sin departamento"
        )

        agent = (
            step.get("agent_id")
            or self._agent_from_output(
                step.get("output")
            )
            or "sin agente"
        )

        duration = self._step_duration(step)

        print()
        print(
            f"{index:02d}. {icon:<9} {name}"
        )
        print(
            f"    Estado       : "
            f"{self._status_label(status)}"
        )
        print(
            f"    Departamento : {department}"
        )
        print(
            f"    Agente       : {agent}"
        )
        print(
            f"    Duracion     : {duration}"
        )

        reason = step.get("reason")
        error = step.get("error")

        if reason:
            print(f"    Motivo       : {reason}")

        if error:
            print(f"    Error        : {error}")

        if self.show_outputs:
            output_text = self._extract_output_text(
                step.get("output")
            )

            if output_text:
                print(
                    "    Salida       : "
                    f"{self._truncate(output_text, 100)}"
                )

    def _render_last_event(
        self,
        snapshot: Dict[str, Any],
    ) -> None:
        last_event = snapshot.get(
            "last_event",
            {},
        )

        event_type = (
            last_event.get("event_type")
            or self._last_rendered_event
            or "-"
        )

        timestamp = self._format_datetime(
            last_event.get("timestamp")
        )

        event_count = snapshot.get(
            "event_count",
            0,
        )

        print()
        print("-" * 72)
        print("ACTIVIDAD")
        print("-" * 72)
        print(f"Ultimo evento : {event_type}")
        print(f"Hora          : {timestamp}")
        print(f"Eventos       : {event_count}")

    def _render_footer(
        self,
        snapshot: Dict[str, Any],
    ) -> None:
        status = snapshot.get(
            "status",
            "created",
        )

        print()
        print("=" * 72)

        if status == "completed":
            print(
                "              WORKFLOW COMPLETADO CORRECTAMENTE"
            )

        elif status == "failed":
            print(
                "                    WORKFLOW FALLIDO"
            )

        elif status == "running":
            print(
                "                     ATLAS TRABAJANDO"
            )

        elif status == "partial":
            print(
                "              WORKFLOW COMPLETADO PARCIALMENTE"
            )

        else:
            print(
                f"                     "
                f"{self._status_label(status)}"
            )

        print("=" * 72)

    # ========================================================
    # Barra de progreso
    # ========================================================

    def _progress_bar(
        self,
        progress: float,
    ) -> str:
        filled = int(
            self.progress_width
            * progress
            / 100
        )

        empty = (
            self.progress_width
            - filled
        )

        return (
            "["
            + "#" * filled
            + "-" * empty
            + "]"
        )

    # ========================================================
    # Utilidades
    # ========================================================

    def _clear_console(self) -> None:
        if not self.auto_clear:
            return

        os.system(
            "cls"
            if os.name == "nt"
            else "clear"
        )

    def _status_label(
        self,
        status: Optional[str],
    ) -> str:
        normalized = (
            str(status).lower()
            if status
            else "unknown"
        )

        return self.STATUS_LABELS.get(
            normalized,
            normalized.upper(),
        )

    @staticmethod
    def _format_datetime(
        value: Optional[Any],
    ) -> str:
        if value is None:
            return "-"

        if isinstance(value, datetime):
            return value.strftime(
                "%Y-%m-%d %H:%M:%S.%f"
            )[:-3]

        text = str(value)

        try:
            parsed = datetime.fromisoformat(
                text
            )

            return parsed.strftime(
                "%Y-%m-%d %H:%M:%S.%f"
            )[:-3]

        except ValueError:
            return text

    @staticmethod
    def _format_duration(
        value: Optional[Any],
    ) -> str:
        if value is None:
            return "-"

        try:
            seconds = float(value)
        except (TypeError, ValueError):
            return str(value)

        if seconds < 1:
            return f"{seconds * 1000:.3f} ms"

        return f"{seconds:.3f} s"

    def _step_duration(
        self,
        step: Dict[str, Any],
    ) -> str:
        duration = step.get(
            "duration_seconds"
        )

        if duration is None:
            metadata = step.get(
                "metadata",
                {},
            )

            if isinstance(metadata, dict):
                duration = metadata.get(
                    "duration_seconds"
                )

        return self._format_duration(duration)

    @staticmethod
    def _agent_from_output(
        output: Any,
    ) -> Optional[str]:
        if not isinstance(output, dict):
            return None

        agent_id = output.get(
            "agent_id"
        )

        if agent_id is None:
            return None

        return str(agent_id)

    @staticmethod
    def _extract_output_text(
        output: Any,
    ) -> Optional[str]:
        if output is None:
            return None

        if isinstance(output, str):
            return output

        if isinstance(output, dict):
            value = (
                output.get("output")
                or output.get("result")
                or output.get("message")
            )

            if value is not None:
                return str(value)

        return str(output)

    @staticmethod
    def _truncate(
        text: str,
        max_length: int,
    ) -> str:
        normalized = " ".join(
            str(text).split()
        )

        if len(normalized) <= max_length:
            return normalized

        return (
            normalized[
                : max_length - 3
            ]
            + "..."
        )

    # ========================================================
    # Información del monitor
    # ========================================================

    def summary(self) -> Dict[str, Any]:
        """
        Devuelve información operativa del monitor.
        """

        with self._lock:
            return {
                "render_count": self._render_count,
                "last_rendered_event": (
                    self._last_rendered_event
                ),
                "auto_clear": self.auto_clear,
                "progress_width": (
                    self.progress_width
                ),
                "show_outputs": (
                    self.show_outputs
                ),
            }

    def __repr__(self) -> str:
        return (
            "AtlasLiveMonitor("
            f"auto_clear={self.auto_clear}, "
            f"progress_width={self.progress_width}, "
            f"render_count={self._render_count}"
            ")"
        )