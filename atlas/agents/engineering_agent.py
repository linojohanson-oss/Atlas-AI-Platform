from __future__ import annotations

from typing import Any, Dict, List

from atlas.agents.base_agent import BaseAgent
from atlas.kernel.llm_manager import LLMManager


class EngineeringAgent(BaseAgent):
    """
    Agente especializado en ingeniería de software.

    Responsable de asistir en:
    - programación
    - depuración
    - arquitectura
    - APIs
    - Python
    - testing

    Puede recibir texto plano o tareas estructuradas
    generadas por WorkflowEngine.
    """

    name = "engineering-agent"

    description = (
        "Agente especializado en ingeniería de software, "
        "arquitectura, APIs, Python y debugging."
    )

    capabilities = [
        "coding",
        "python",
        "debugging",
        "architecture",
        "api",
        "testing",
        "general_reasoning",
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
        Ejecuta una tarea técnica utilizando el proveedor LLM activo.
        """

        user_prompt = self._build_user_prompt(
            task
        )

        llm_response = self.llm_manager.generate(
            system_prompt=(
                "Sos el Engineering Agent de Atlas AI Platform.\n"
                "Sos un ingeniero de software senior.\n"
                "Respondé con soluciones técnicas claras, "
                "explicando arquitectura, código, debugging, "
                "buenas prácticas y alternativas.\n"
                "Usá los resultados previos como contexto técnico, "
                "pero no los repitas literalmente ni reproduzcas "
                "estructuras internas del workflow.\n"
                "Priorizá soluciones concretas, aplicables y seguras."
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
        técnico, compacto y legible.
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

        variables = task.get(
            "variables",
            {},
        )

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

        variables_context = self._format_variables(
            variables
        )

        if variables_context:
            sections.extend(
                [
                    "",
                    "DATOS DE ENTRADA",
                    variables_context,
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
                "INSTRUCCIÓN DE INGENIERÍA",
                (
                    "Proponé una solución técnica concreta para este "
                    "paso. Incluí arquitectura, cambios necesarios, "
                    "código o pseudocódigo cuando corresponda, "
                    "validaciones y pruebas recomendadas. "
                    "No repitas literalmente el contexto anterior "
                    "ni muestres estructuras internas del workflow."
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
    def _format_variables(
        variables: Any,
    ) -> str:
        """
        Formatea variables simples sin serializar estructuras
        excesivamente grandes.
        """

        if not isinstance(
            variables,
            dict,
        ):
            return ""

        lines: List[str] = []

        for key, value in variables.items():
            normalized_value = str(
                value
            ).strip()

            if not normalized_value:
                continue

            if len(normalized_value) > 1000:
                normalized_value = (
                    normalized_value[:1000]
                    + " [truncado]"
                )

            lines.append(
                f"- {key}: {normalized_value}"
            )

        return "\n".join(
            lines
        ).strip()

    @staticmethod
    def _format_previous_results(
        previous_results: Any,
    ) -> str:
        """
        Extrae únicamente las salidas útiles de pasos anteriores.
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

                duration_seconds = result.get(
                    "duration_seconds"
                )
            else:
                output = result
                status = "unknown"
                agent_id = None
                duration_seconds = None

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

            if duration_seconds is not None:
                details.append(
                    f"Duración: {duration_seconds}s"
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