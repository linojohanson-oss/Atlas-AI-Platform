from __future__ import annotations

from html import escape
from typing import Any, Dict, List, Optional


class WorkflowVisualizerHTML:
    """
    Renderizador HTML para ejecuciones de workflows de Atlas AI.

    Convierte el resultado estructurado de WorkflowEngine en una
    visualización gráfica lista para insertar en el dashboard.
    """

    STATUS_LABELS = {
        "completed": "Completado",
        "failed": "Fallido",
        "skipped": "Omitido",
        "blocked": "Bloqueado",
        "running": "En ejecución",
        "pending": "Pendiente",
        "unknown": "Desconocido",
    }

    STATUS_CLASSES = {
        "completed": "status-completed",
        "failed": "status-failed",
        "skipped": "status-skipped",
        "blocked": "status-blocked",
        "running": "status-running",
        "pending": "status-pending",
        "unknown": "status-unknown",
    }

    def render_execution(
        self,
        execution: Dict[str, Any],
        include_document: bool = True,
        show_outputs: bool = True,
        output_limit: int = 400,
    ) -> str:
        """
        Genera el HTML completo de una ejecución de workflow.
        """

        if not isinstance(execution, dict):
            raise TypeError(
                "execution debe ser un diccionario."
            )

        body = self._render_body(
            execution=execution,
            show_outputs=show_outputs,
            output_limit=output_limit,
        )

        if not include_document:
            return body

        return self._render_document(
            body=body,
            workflow_id=str(
                execution.get(
                    "workflow_id",
                    "workflow",
                )
            ),
        )

    def save_execution(
        self,
        execution: Dict[str, Any],
        output_path: str,
        show_outputs: bool = True,
        output_limit: int = 400,
    ) -> str:
        """
        Guarda la visualización HTML en disco.
        """

        html = self.render_execution(
            execution=execution,
            include_document=True,
            show_outputs=show_outputs,
            output_limit=output_limit,
        )

        with open(
            output_path,
            "w",
            encoding="utf-8",
        ) as file:
            file.write(html)

        return output_path

    # ============================================================
    # Documento
    # ============================================================

    def _render_document(
        self,
        body: str,
        workflow_id: str,
    ) -> str:
        title = escape(
            f"Atlas AI - {workflow_id}"
        )

        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >
    <title>{title}</title>
    {self._styles()}
</head>
<body>
    {body}
</body>
</html>
"""

    def _render_body(
        self,
        execution: Dict[str, Any],
        show_outputs: bool,
        output_limit: int,
    ) -> str:
        workflow_id = escape(
            str(
                execution.get(
                    "workflow_id",
                    "workflow-desconocido",
                )
            )
        )

        execution_id = escape(
            str(
                execution.get(
                    "execution_id",
                    "sin-id",
                )
            )
        )

        request = escape(
            str(
                execution.get(
                    "request",
                    "",
                )
            )
        )

        status = str(
            execution.get(
                "status",
                "unknown",
            )
        ).lower()

        status_label = self.STATUS_LABELS.get(
            status,
            status,
        )

        status_class = self.STATUS_CLASSES.get(
            status,
            "status-unknown",
        )

        total_steps = self._safe_int(
            execution.get(
                "total_steps"
            )
        )

        completed_count = self._safe_int(
            execution.get(
                "completed_count"
            )
        )

        failed_count = self._safe_int(
            execution.get(
                "failed_count"
            )
        )

        skipped_count = self._safe_int(
            execution.get(
                "skipped_count"
            )
        )

        blocked_count = self._safe_int(
            execution.get(
                "blocked_count"
            )
        )

        success_rate = self._safe_float(
            execution.get(
                "success_rate"
            )
        )

        duration_seconds = self._safe_float(
            execution.get(
                "duration_seconds"
            )
        )

        steps = self._collect_steps(
            execution
        )

        step_html = self._render_steps(
            steps=steps,
            show_outputs=show_outputs,
            output_limit=output_limit,
        )

        final_output_html = self._render_final_output(
            execution=execution,
            output_limit=output_limit,
        )

        errors_html = self._render_errors(
            execution.get(
                "errors",
                [],
            )
        )

        progress_width = min(
            max(
                success_rate,
                0.0,
            ),
            100.0,
        )

        request_html = ""

        if request:
            request_html = f"""
            <section class="request-card">
                <div class="section-label">
                    Solicitud
                </div>
                <div class="request-text">
                    {request}
                </div>
            </section>
            """

        return f"""
<main class="atlas-workflow-page">
    <header class="hero">
        <div>
            <div class="eyebrow">
                ATLAS AI · WORKFLOW VISUALIZER
            </div>

            <h1>
                {workflow_id}
            </h1>

            <div class="execution-id">
                Execution ID: {execution_id}
            </div>
        </div>

        <div class="status-badge {status_class}">
            {escape(status_label)}
        </div>
    </header>

    {request_html}

    <section class="metrics-grid">
        {self._metric_card(
            "Pasos",
            f"{completed_count}/{total_steps}",
            "completados",
        )}

        {self._metric_card(
            "Éxito",
            f"{success_rate:.1f}%",
            "tasa general",
        )}

        {self._metric_card(
            "Duración",
            f"{duration_seconds:.4f}s",
            "tiempo total",
        )}

        {self._metric_card(
            "Errores",
            str(failed_count),
            "pasos fallidos",
        )}
    </section>

    <section class="progress-section">
        <div class="progress-header">
            <span>Progreso del workflow</span>
            <strong>{success_rate:.1f}%</strong>
        </div>

        <div class="progress-track">
            <div
                class="progress-fill"
                style="width: {progress_width:.1f}%"
            ></div>
        </div>

        <div class="progress-summary">
            <span>Completados: {completed_count}</span>
            <span>Fallidos: {failed_count}</span>
            <span>Omitidos: {skipped_count}</span>
            <span>Bloqueados: {blocked_count}</span>
        </div>
    </section>

    <section class="workflow-section">
        <div class="section-title">
            Flujo de ejecución
        </div>

        <div class="workflow-flow">
            {step_html}
        </div>
    </section>

    {final_output_html}

    {errors_html}

    <footer class="footer">
        Atlas AI Platform · Workflow Engine
    </footer>
</main>
"""

    # ============================================================
    # Pasos
    # ============================================================

    def _collect_steps(
        self,
        execution: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        steps: List[Dict[str, Any]] = []

        groups = [
            "completed_steps",
            "failed_steps",
            "skipped_steps",
            "blocked_steps",
        ]

        for group_name in groups:
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
                    steps.append(step)

        return steps

    def _render_steps(
        self,
        steps: List[Dict[str, Any]],
        show_outputs: bool,
        output_limit: int,
    ) -> str:
        if not steps:
            return """
            <div class="empty-state">
                No se encontraron pasos en esta ejecución.
            </div>
            """

        blocks: List[str] = []

        for index, step in enumerate(
            steps,
            start=1,
        ):
            blocks.append(
                self._render_step(
                    index=index,
                    step=step,
                    show_output=show_outputs,
                    output_limit=output_limit,
                )
            )

            if index < len(steps):
                blocks.append(
                    """
                    <div class="workflow-arrow">
                        <div class="arrow-line"></div>
                        <div class="arrow-head">▼</div>
                    </div>
                    """
                )

        return "\n".join(blocks)

    def _render_step(
        self,
        index: int,
        step: Dict[str, Any],
        show_output: bool,
        output_limit: int,
    ) -> str:
        step_id = escape(
            str(
                step.get(
                    "step_id",
                    f"step-{index}",
                )
            )
        )

        status = str(
            step.get(
                "status",
                "unknown",
            )
        ).lower()

        status_label = self.STATUS_LABELS.get(
            status,
            status,
        )

        status_class = self.STATUS_CLASSES.get(
            status,
            "status-unknown",
        )

        duration = self._safe_float(
            step.get(
                "duration_seconds"
            )
        )

        department = escape(
            self._extract_department_id(
                step
            )
            or "no disponible"
        )

        agent = escape(
            self._extract_agent_id(
                step
            )
            or "no disponible"
        )

        output = self._extract_output(
            step
        )

        output_html = ""

        if (
            show_output
            and output
        ):
            output_html = f"""
            <div class="step-output">
                <div class="step-output-label">
                    Resultado
                </div>

                <div class="step-output-text">
                    {escape(
                        self._truncate(
                            output,
                            output_limit,
                        )
                    )}
                </div>
            </div>
            """

        return f"""
        <article class="workflow-step">
            <div class="step-number">
                {index}
            </div>

            <div class="step-main">
                <div class="step-header">
                    <h2>{step_id}</h2>

                    <span class="status-badge {status_class}">
                        {escape(status_label)}
                    </span>
                </div>

                <div class="step-meta">
                    <div class="meta-item">
                        <span>Departamento</span>
                        <strong>{department}</strong>
                    </div>

                    <div class="meta-item">
                        <span>Agente</span>
                        <strong>{agent}</strong>
                    </div>

                    <div class="meta-item">
                        <span>Duración</span>
                        <strong>{duration:.6f}s</strong>
                    </div>
                </div>

                {output_html}
            </div>
        </article>
        """

    # ============================================================
    # Resultado y errores
    # ============================================================

    def _render_final_output(
        self,
        execution: Dict[str, Any],
        output_limit: int,
    ) -> str:
        final_output = execution.get(
            "final_output",
            {},
        )

        if isinstance(
            final_output,
            dict,
        ):
            output = final_output.get(
                "output"
            )
        else:
            output = final_output

        if not output:
            return ""

        text = escape(
            self._truncate(
                output,
                max(
                    output_limit,
                    800,
                ),
            )
        )

        return f"""
        <section class="final-output">
            <div class="section-label">
                Resultado final
            </div>

            <div class="final-output-text">
                {text}
            </div>
        </section>
        """

    def _render_errors(
        self,
        errors: Any,
    ) -> str:
        if not errors:
            return ""

        if not isinstance(
            errors,
            list,
        ):
            errors = [errors]

        items = []

        for error in errors:
            items.append(
                f"<li>{escape(str(error))}</li>"
            )

        return f"""
        <section class="errors-section">
            <div class="section-label">
                Errores
            </div>

            <ul>
                {''.join(items)}
            </ul>
        </section>
        """

    # ============================================================
    # Extracción
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

        return str(output)

    # ============================================================
    # Utilidades
    # ============================================================

    @staticmethod
    def _metric_card(
        label: str,
        value: str,
        description: str,
    ) -> str:
        return f"""
        <div class="metric-card">
            <div class="metric-label">
                {escape(label)}
            </div>

            <div class="metric-value">
                {escape(value)}
            </div>

            <div class="metric-description">
                {escape(description)}
            </div>
        </div>
        """

    @staticmethod
    def _truncate(
        value: Any,
        max_length: int,
    ) -> str:
        text = " ".join(
            str(value).split()
        )

        if len(text) <= max_length:
            return text

        return (
            text[: max_length - 3]
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

    @staticmethod
    def _safe_float(
        value: Any,
    ) -> float:
        try:
            return float(
                value or 0.0
            )
        except (
            TypeError,
            ValueError,
        ):
            return 0.0

    # ============================================================
    # Estilos
    # ============================================================

    @staticmethod
    def _styles() -> str:
        return """
<style>
    :root {
        --background: #08111f;
        --panel: #101c2f;
        --panel-soft: #16243a;
        --border: #263957;
        --text: #edf4ff;
        --muted: #93a7c5;
        --accent: #4f8cff;
        --success: #3ddc97;
        --danger: #ff647c;
        --warning: #f2c94c;
        --blocked: #c084fc;
        --neutral: #94a3b8;
    }

    * {
        box-sizing: border-box;
    }

    body {
        margin: 0;
        background:
            radial-gradient(
                circle at top,
                #142746 0%,
                var(--background) 45%
            );
        color: var(--text);
        font-family:
            Inter,
            Segoe UI,
            Arial,
            sans-serif;
    }

    .atlas-workflow-page {
        width: min(
            1120px,
            calc(100% - 32px)
        );
        margin: 0 auto;
        padding: 40px 0 60px;
    }

    .hero {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 24px;
        margin-bottom: 24px;
    }

    .eyebrow {
        color: var(--accent);
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.12em;
        margin-bottom: 10px;
    }

    h1 {
        margin: 0;
        font-size: clamp(
            30px,
            5vw,
            48px
        );
        line-height: 1.1;
    }

    .execution-id {
        color: var(--muted);
        margin-top: 12px;
        font-family:
            Consolas,
            monospace;
        font-size: 13px;
    }

    .status-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 999px;
        padding: 7px 12px;
        font-size: 12px;
        font-weight: 700;
        white-space: nowrap;
        border: 1px solid transparent;
    }

    .status-completed {
        background: rgba(
            61,
            220,
            151,
            0.12
        );
        border-color: rgba(
            61,
            220,
            151,
            0.4
        );
        color: var(--success);
    }

    .status-failed {
        background: rgba(
            255,
            100,
            124,
            0.12
        );
        border-color: rgba(
            255,
            100,
            124,
            0.4
        );
        color: var(--danger);
    }

    .status-running,
    .status-pending {
        background: rgba(
            242,
            201,
            76,
            0.12
        );
        border-color: rgba(
            242,
            201,
            76,
            0.4
        );
        color: var(--warning);
    }

    .status-blocked {
        background: rgba(
            192,
            132,
            252,
            0.12
        );
        border-color: rgba(
            192,
            132,
            252,
            0.4
        );
        color: var(--blocked);
    }

    .status-skipped,
    .status-unknown {
        background: rgba(
            148,
            163,
            184,
            0.12
        );
        border-color: rgba(
            148,
            163,
            184,
            0.35
        );
        color: var(--neutral);
    }

    .request-card,
    .progress-section,
    .workflow-section,
    .final-output,
    .errors-section {
        background: rgba(
            16,
            28,
            47,
            0.92
        );
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 22px;
        margin-bottom: 20px;
    }

    .section-label,
    .section-title {
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .request-text,
    .final-output-text {
        line-height: 1.7;
    }

    .metrics-grid {
        display: grid;
        grid-template-columns:
            repeat(
                4,
                minmax(0, 1fr)
            );
        gap: 14px;
        margin-bottom: 20px;
    }

    .metric-card {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 18px;
    }

    .metric-label {
        color: var(--muted);
        font-size: 13px;
    }

    .metric-value {
        font-size: 28px;
        font-weight: 750;
        margin: 8px 0 4px;
    }

    .metric-description {
        color: var(--muted);
        font-size: 12px;
    }

    .progress-header {
        display: flex;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 12px;
    }

    .progress-track {
        width: 100%;
        height: 12px;
        border-radius: 999px;
        background: #091323;
        overflow: hidden;
        border: 1px solid var(--border);
    }

    .progress-fill {
        height: 100%;
        background:
            linear-gradient(
                90deg,
                var(--accent),
                var(--success)
            );
        border-radius: inherit;
    }

    .progress-summary {
        display: flex;
        flex-wrap: wrap;
        gap: 14px;
        color: var(--muted);
        font-size: 13px;
        margin-top: 12px;
    }

    .workflow-flow {
        display: flex;
        flex-direction: column;
        align-items: stretch;
    }

    .workflow-step {
        display: grid;
        grid-template-columns:
            48px
            minmax(0, 1fr);
        gap: 16px;
        background: var(--panel-soft);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 20px;
    }

    .step-number {
        width: 48px;
        height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--accent);
        color: white;
        border-radius: 14px;
        font-size: 18px;
        font-weight: 800;
    }

    .step-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 14px;
    }

    .step-header h2 {
        margin: 0;
        font-size: 20px;
    }

    .step-meta {
        display: grid;
        grid-template-columns:
            repeat(
                3,
                minmax(0, 1fr)
            );
        gap: 12px;
        margin-top: 18px;
    }

    .meta-item {
        background: rgba(
            8,
            17,
            31,
            0.55
        );
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 12px;
    }

    .meta-item span {
        display: block;
        color: var(--muted);
        font-size: 12px;
        margin-bottom: 5px;
    }

    .meta-item strong {
        font-size: 14px;
    }

    .step-output {
        margin-top: 16px;
        background: rgba(
            8,
            17,
            31,
            0.65
        );
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 14px;
    }

    .step-output-label {
        color: var(--muted);
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 7px;
    }

    .step-output-text {
        line-height: 1.6;
        font-size: 14px;
    }

    .workflow-arrow {
        display: flex;
        flex-direction: column;
        align-items: center;
        color: var(--accent);
        min-height: 52px;
    }

    .arrow-line {
        width: 2px;
        flex: 1;
        background: var(--border);
    }

    .arrow-head {
        line-height: 1;
    }

    .errors-section {
        border-color: rgba(
            255,
            100,
            124,
            0.45
        );
    }

    .errors-section ul {
        margin: 0;
        padding-left: 22px;
        color: var(--danger);
    }

    .footer {
        text-align: center;
        color: var(--muted);
        font-size: 12px;
        padding-top: 10px;
    }

    .empty-state {
        color: var(--muted);
        text-align: center;
        padding: 30px;
    }

    @media (
        max-width: 800px
    ) {
        .metrics-grid {
            grid-template-columns:
                repeat(
                    2,
                    minmax(0, 1fr)
                );
        }

        .step-meta {
            grid-template-columns:
                1fr;
        }
    }

    @media (
        max-width: 520px
    ) {
        .atlas-workflow-page {
            width:
                calc(100% - 20px);
            padding-top: 24px;
        }

        .hero {
            flex-direction: column;
        }

        .metrics-grid {
            grid-template-columns:
                1fr;
        }

        .workflow-step {
            grid-template-columns:
                1fr;
        }

        .step-header {
            align-items: flex-start;
            flex-direction: column;
        }
    }
</style>
"""