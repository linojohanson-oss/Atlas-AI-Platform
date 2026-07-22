from __future__ import annotations

from typing import Any, Dict, List, Optional


class WorkflowVisualizer:
    """
    Visualizador textual de workflows de Atlas AI.

    Permite representar:

    - Definición del workflow.
    - Dependencias entre pasos.
    - Estado de una ejecución.
    - Departamento y agente seleccionado.
    - Resultado compacto de cada paso.
    """

    STATUS_ICONS = {
        "completed": "[OK]",
        "failed": "[ERROR]",
        "skipped": "[SKIP]",
        "blocked": "[BLOCKED]",
        "running": "[RUNNING]",
        "pending": "[PENDING]",
    }

    def render_execution(
        self,
        execution: Dict[str, Any],
        show_outputs: bool = True,
        output_limit: int = 180,
    ) -> str:
        """
        Genera una visualización textual de una ejecución.
        """

        if not isinstance(execution, dict):
            raise TypeError(
                "execution debe ser un diccionario."
            )

        workflow_id = execution.get(
            "workflow_id",
            "workflow-desconocido",
        )

        execution_id = execution.get(
            "execution_id",
            "sin-id",
        )

        status = str(
            execution.get(
                "status",
                "unknown",
            )
        ).lower()

        total_steps = self._safe_int(
            execution.get("total_steps")
        )

        completed_count = self._safe_int(
            execution.get("completed_count")
        )

        failed_count = self._safe_int(
            execution.get("failed_count")
        )

        skipped_count = self._safe_int(
            execution.get("skipped_count")
        )

        blocked_count = self._safe_int(
            execution.get("blocked_count")
        )

        success_rate = execution.get(
            "success_rate",
            0.0,
        )

        duration_seconds = execution.get(
            "duration_seconds",
            0.0,
        )

        lines: List[str] = []

        lines.append("")
        lines.append("=" * 78)
        lines.append("ATLAS AI - WORKFLOW VISUALIZER")
        lines.append("=" * 78)

        lines.append(
            f"Workflow       : {workflow_id}"
        )

        lines.append(
            f"Execution ID   : {execution_id}"
        )

        lines.append(
            f"Estado         : "
            f"{self._status_icon(status)} "
            f"{status.upper()}"
        )

        lines.append(
            f"Pasos          : "
            f"{completed_count}/{total_steps}"
        )

        lines.append(
            f"Tasa de éxito  : {success_rate}%"
        )

        lines.append(
            f"Duración       : {duration_seconds} segundos"
        )

        request = execution.get(
            "request"
        )

        if request:
            lines.append(
                f"Solicitud      : {request}"
            )

        lines.append("-" * 78)

        progress = self._progress_bar(
            completed=completed_count,
            total=total_steps,
        )

        lines.append(
            f"Progreso       : {progress}"
        )

        lines.append(
            "Resumen        : "
            f"OK={completed_count} | "
            f"ERROR={failed_count} | "
            f"SKIP={skipped_count} | "
            f"BLOCKED={blocked_count}"
        )

        lines.append("-" * 78)
        lines.append("FLUJO DE EJECUCIÓN")
        lines.append("-" * 78)

        steps = self._collect_steps(
            execution
        )

        if not steps:
            lines.append(
                "No se encontraron pasos en la ejecución."
            )
        else:
            for index, step in enumerate(
                steps,
                start=1,
            ):
                if index > 1:
                    lines.append(
                        " " * 7 + "|"
                    )
                    lines.append(
                        " " * 7 + "v"
                    )

                lines.extend(
                    self._render_step(
                        index=index,
                        step=step,
                        show_output=show_outputs,
                        output_limit=output_limit,
                    )
                )

        final_output = execution.get(
            "final_output",
            {},
        )

        if isinstance(
            final_output,
            dict,
        ):
            final_text = final_output.get(
                "output"
            )
        else:
            final_text = final_output

        if final_text:
            lines.append("-" * 78)
            lines.append("RESULTADO FINAL")
            lines.append("-" * 78)
            lines.append(
                self._truncate(
                    final_text,
                    max_length=500,
                )
            )

        errors = execution.get(
            "errors",
            [],
        )

        if errors:
            lines.append("-" * 78)
            lines.append("ERRORES")
            lines.append("-" * 78)

            for error in errors:
                lines.append(
                    f"- {self._truncate(error, 300)}"
                )

        lines.append("=" * 78)

        return "\n".join(
            lines
        )

    def print_execution(
        self,
        execution: Dict[str, Any],
        show_outputs: bool = True,
        output_limit: int = 180,
    ) -> None:
        """
        Imprime una ejecución visualizada.
        """

        print(
            self.render_execution(
                execution=execution,
                show_outputs=show_outputs,
                output_limit=output_limit,
            )
        )

    # ============================================================
    # Pasos
    # ============================================================

    def _collect_steps(
        self,
        execution: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Reúne todos los pasos respetando su clasificación.
        """

        step_groups = [
            "completed_steps",
            "failed_steps",
            "skipped_steps",
            "blocked_steps",
        ]

        steps: List[
            Dict[str, Any]
        ] = []

        for group_name in step_groups:
            group = execution.get(
                group_name,
                [],
            )

            if not isinstance(
                group,
                list,
            ):
                continue

            for step in group:
                if isinstance(
                    step,
                    dict,
                ):
                    steps.append(
                        step
                    )

        return steps

    def _render_step(
        self,
        index: int,
        step: Dict[str, Any],
        show_output: bool,
        output_limit: int,
    ) -> List[str]:
        """
        Renderiza un paso individual.
        """

        step_id = step.get(
            "step_id",
            f"step-{index}",
        )

        status = str(
            step.get(
                "status",
                "unknown",
            )
        ).lower()

        duration = step.get(
            "duration_seconds",
            0.0,
        )

        department_id = self._extract_department_id(
            step
        )

        agent_id = self._extract_agent_id(
            step
        )

        output = self._extract_output(
            step
        )

        icon = self._status_icon(
            status
        )

        lines = [
            (
                f"[{index}] {icon} "
                f"{step_id}"
            ),
            (
                f"    Estado       : "
                f"{status}"
            ),
            (
                f"    Departamento : "
                f"{department_id or 'no disponible'}"
            ),
            (
                f"    Agente       : "
                f"{agent_id or 'no disponible'}"
            ),
            (
                f"    Duración     : "
                f"{duration} segundos"
            ),
        ]

        if (
            show_output
            and output
        ):
            lines.append(
                "    Resultado    : "
                + self._truncate(
                    output,
                    max_length=output_limit,
                )
            )

        return lines

    # ============================================================
    # Extracción de información
    # ============================================================

    @staticmethod
    def _extract_department_id(
        step: Dict[str, Any],
    ) -> Optional[str]:
        result = step.get(
            "result",
            {},
        )

        if not isinstance(
            result,
            dict,
        ):
            return None

        department = result.get(
            "department",
            {},
        )

        if isinstance(
            department,
            str,
        ):
            return department

        if isinstance(
            department,
            dict,
        ):
            return (
                department.get(
                    "department_id"
                )
                or department.get(
                    "id"
                )
                or department.get(
                    "name"
                )
            )

        return None

    @staticmethod
    def _extract_agent_id(
        step: Dict[str, Any],
    ) -> Optional[str]:
        result = step.get(
            "result",
            {},
        )

        if not isinstance(
            result,
            dict,
        ):
            return None

        selected_agent = result.get(
            "selected_agent",
            {},
        )

        if isinstance(
            selected_agent,
            str,
        ):
            return selected_agent

        if not isinstance(
            selected_agent,
            dict,
        ):
            return None

        agent = selected_agent.get(
            "agent",
            selected_agent,
        )

        if isinstance(
            agent,
            str,
        ):
            return agent

        if isinstance(
            agent,
            dict,
        ):
            return (
                agent.get(
                    "agent_id"
                )
                or agent.get(
                    "name"
                )
            )

        return None

    @staticmethod
    def _extract_output(
        step: Dict[str, Any],
    ) -> Optional[str]:
        result = step.get(
            "result",
            {},
        )

        if not isinstance(
            result,
            dict,
        ):
            return None

        execution = result.get(
            "execution",
            {},
        )

        if not isinstance(
            execution,
            dict,
        ):
            return None

        output = (
            execution.get(
                "output"
            )
            or execution.get(
                "content"
            )
            or execution.get(
                "result"
            )
        )

        if output is None:
            return None

        if isinstance(
            output,
            dict,
        ):
            output = (
                output.get(
                    "content"
                )
                or output.get(
                    "output"
                )
                or str(output)
            )

        return str(
            output
        )

    # ============================================================
    # Utilidades visuales
    # ============================================================

    def _status_icon(
        self,
        status: str,
    ) -> str:
        return self.STATUS_ICONS.get(
            status,
            "[?]",
        )

    @staticmethod
    def _progress_bar(
        completed: int,
        total: int,
        width: int = 30,
    ) -> str:
        if total <= 0:
            return (
                "[" + "-" * width + "] 0%"
            )

        ratio = min(
            max(
                completed / total,
                0.0,
            ),
            1.0,
        )

        filled = round(
            width * ratio
        )

        empty = width - filled

        percentage = round(
            ratio * 100
        )

        return (
            "["
            + "#" * filled
            + "-" * empty
            + f"] {percentage}%"
        )

    @staticmethod
    def _truncate(
        value: Any,
        max_length: int,
    ) -> str:
        text = " ".join(
            str(
                value
            ).split()
        )

        if len(text) <= max_length:
            return text

        return (
            text[
                : max_length - 3
            ]
            + "..."
        )

    @staticmethod
    def _safe_int(
        value: Any,
    ) -> int:
        try:
            return int(
                value or 0
            )
        except (
            TypeError,
            ValueError,
        ):
            return 0