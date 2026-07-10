from typing import Any, Dict

from atlas.agents.base_agent import BaseAgent
from atlas.kernel.llm_manager import LLMManager


class GeneralAgent(BaseAgent):
    """
    Agente general de Atlas AI Platform.

    Utiliza el LLM Manager para procesar tareas generales.
    """

    name = "general-agent"

    description = (
        "Agente generalista para consultas, razonamiento "
        "y asistencia básica."
    )

    capabilities = [
        "general_reasoning",
        "task_assistance",
        "question_answering",
    ]

    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm_manager = llm_manager

    def execute(self, task: str) -> Dict[str, Any]:
        """
        Ejecuta una tarea utilizando el proveedor LLM activo.
        """
        normalized_task = task.strip()

        if not normalized_task:
            raise ValueError(
                "La tarea no puede estar vacía."
            )

        llm_response = self.llm_manager.generate(
            system_prompt=(
                "Sos el agente general de Atlas AI Platform. "
                "Respondé de forma clara, precisa y estructurada."
            ),
            user_prompt=normalized_task,
        )

        return {
            "agent": self.name,
            "status": llm_response["status"],
            "task": normalized_task,
            "output": llm_response["content"],
            "provider": llm_response["provider"],
            "model": llm_response["model"],
            "metadata": llm_response.get("metadata", {}),
        }