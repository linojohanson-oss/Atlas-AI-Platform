from __future__ import annotations

from typing import Any, Dict, List

from atlas.agents.base_agent import BaseAgent
from atlas.kernel.llm_manager import LLMManager


class SecurityAgent(BaseAgent):
    """
    Agente especializado en seguridad, evaluación de riesgos,
    cumplimiento y análisis de vulnerabilidades.

    Puede procesar tanto tareas de texto plano como tareas
    estructuradas generadas por WorkflowEngine.
    """

    name = "security-agent"

    description = (
        "Agente especializado en seguridad informática, "
        "evaluación de riesgos, cumplimiento normativo "
        "y análisis de vulnerabilidades."
    )

    capabilities = [
        "general_reasoning",
        "security_analysis",
    ]

    def __init__(
        self,
        llm_manager: LLMManager,
    ) -> None:
        self.llm_manager = llm_manager

    def execute(
        self,
        task: Any,
    ) -> Dict[str, Any]:
        """
        Ejecuta un análisis de seguridad utilizando el proveedor
        LLM activo.
        """

        user_prompt = self._build_user_prompt(
            task
        )

        llm_response = self.llm_manager.generate(
            system_prompt=(
                "Sos el Security Agent de Atlas AI. "
                "Tu responsabilidad es detectar riesgos, "
                "vulnerabilidades, problemas de seguridad, "
                "aspectos de cumplimiento y emitir recomendaciones "
                "concretas para mitigarlos. "
                "Priorizá los hallazgos según su severidad. "
                "Usá los resultados previos como contexto, pero no "
                "los repitas literalmente ni reproduzcas estructuras "
                "internas del workflow."
            ),
            user_prompt=user_prompt,
        )

        return {
            "agent": self.name,
            "status": llm_response["status"],
            "task": self._build_task_summary(
                task
            ),
            "output": llm_response["content"],
            "provider": llm_response["provider"],
            "model": llm_response["model"],
            "metadata": llm_response.get(
                "metadata",
                {},
            ),
        }

    def _build_user_prompt(
        self,
        task: Any,
    ) -> str:
        """
        Convierte una tarea de texto o estructurada en un prompt
        legible y compacto para el agente de seguridad.
        """

        if isinstance(task, str):
            normalized_task = task.strip()

            if not normalized_task:
                raise ValueError(
                    "La tarea no puede estar vacía."
                )

            return normalized_task

        if not isinstance(task, dict):
            normalized_task = str(task).strip()

            if not normalized_task:
                raise ValueError(
                    "La tarea no puede estar vacía."
                )

            return normalized_task

        request = str(
            task.get("request", "")
        ).strip()

        prompt = str(
            task.get("prompt") or ""
        ).strip()

        objective = str(
            task.get("objective") or ""
        ).strip()

        previous_results = task.get(
            "previous_results",
            {},
        )

        sections: List[str] = []

        if request:
            sections.extend(
                [
                    "SOLICITUD PRINCIPAL",
                    request,
                ]
            )

        if objective:
            sections.extend(
                [
                    "",
                    "OBJETIVO",
                    objective,
                ]
            )

        if prompt:
            sections.extend(
                [
                    "",
                    "OBJETIVO DEL PASO",
                    prompt,
                ]
            )

        previous_context = (
            self._format_previous_results(
                previous_results
            )
        )

        if previous_context:
            sections.extend(
                [
                    "",
                    "RESULTADOS DE PASOS ANTERIORES",
                    previous_context,
                ]
            )

        sections.extend(
            [
                "",
                "INSTRUCCIÓN DE SEGURIDAD",
                (
                    "Analizá la solicitud desde la perspectiva de "
                    "seguridad. Identificá riesgos, vulnerabilidades, "
                    "impacto, nivel de severidad y recomendaciones de "
                    "mitigación. No repitas literalmente el contexto "
                    "anterior ni muestres estructuras internas."
                ),
            ]
        )

        final_prompt = "\n".join(
            sections
        ).strip()

        if not final_prompt:
            raise ValueError(
                "La tarea estructurada no contiene información útil."
            )

        return final_prompt

    @staticmethod
    def _format_previous_results(
        previous_results: Any,
    ) -> str:
        """
        Extrae únicamente las salidas útiles de los pasos anteriores.
        """

        if not isinstance(
            previous_results,
            dict,
        ):
            return ""

        sections: List[str] = []

        for step_id, result in previous_results.items():
            if isinstance(result, dict):
                output = result.get(
                    "output",
                    "",
                )

                status = result.get(
                    "status",
                    "unknown",
                )

                agent_id = result.get(
                    "agent_id"
                )
            else:
                output = result
                status = "unknown"
                agent_id = None

            normalized_output = str(
                output
            ).strip()

            if not normalized_output:
                continue

            if len(normalized_output) > 4000:
                normalized_output = (
                    normalized_output[:4000]
                    + "\n[contenido anterior truncado]"
                )

            sections.append(
                f"Paso: {step_id}"
            )

            details = [
                f"Estado: {status}"
            ]

            if agent_id:
                details.append(
                    f"Agente: {agent_id}"
                )

            sections.append(
                " | ".join(details)
            )

            sections.append(
                normalized_output
            )

            sections.append("")

        return "\n".join(
            sections
        ).strip()

    @staticmethod
    def _build_task_summary(
        task: Any,
    ) -> Dict[str, Any]:
        """
        Devuelve una representación compacta de la tarea ejecutada.
        """

        if isinstance(task, dict):
            previous_results = task.get(
                "previous_results",
                {},
            )

            dependency_ids = (
                list(previous_results.keys())
                if isinstance(
                    previous_results,
                    dict,
                )
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
                    task.get(
                        "request",
                        "",
                    )
                )[:500],
                "dependency_ids": dependency_ids,
            }

        return {
            "type": "text-task",
            "content": str(task)[:500],
        }