from typing import Any, Dict

from atlas.agents.base_agent import BaseAgent
from atlas.kernel.llm_manager import LLMManager


class ResearchAgent(BaseAgent):
    """
    Agente especializado en investigación, análisis de información,
    contraste de fuentes y elaboración de conclusiones.
    """

    name = "research-agent"

    description = (
        "Agente especializado en investigación estructurada, "
        "análisis de información, comparación de evidencia "
        "y elaboración de conclusiones."
    )

    capabilities = [
        "general_reasoning",
        "research",
        "information_analysis",
    ]

    def __init__(
        self,
        llm_manager: LLMManager,
    ) -> None:
        self.llm_manager = llm_manager

    def execute(
        self,
        task: str,
    ) -> Dict[str, Any]:
        normalized_task = str(task).strip()

        if not normalized_task:
            raise ValueError(
                "La tarea no puede estar vacía."
            )

        llm_response = self.llm_manager.generate(
            system_prompt=(
                "Sos el Research Agent de Atlas AI. "
                "Tu responsabilidad es investigar problemas, "
                "analizar información, comparar evidencia, "
                "detectar contradicciones y producir conclusiones "
                "claras, fundamentadas y ordenadas. "
                "Indicá supuestos, limitaciones y nivel de certeza "
                "cuando corresponda."
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
            "metadata": llm_response.get(
                "metadata",
                {},
            ),
        }