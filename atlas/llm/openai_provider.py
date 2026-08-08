import os
from typing import Any, Dict

from openai import OpenAI

from atlas.llm.base_provider import BaseLLMProvider


class OpenAILLMProvider(BaseLLMProvider):
    """
    Proveedor LLM real de OpenAI para Atlas AI Platform.
    """

    name = "openai"
    model = "gpt-5.5"

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "No se encontró la variable de entorno OPENAI_API_KEY."
            )

        self.client = OpenAI(api_key=api_key)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        """
        Genera una respuesta real mediante OpenAI Responses API.
        """
        normalized_prompt = user_prompt.strip()

        if not normalized_prompt:
            raise ValueError(
                "El mensaje del usuario no puede estar vacío."
            )

        response = self.client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=normalized_prompt,
        )

        content = response.output_text

        if not content:
            raise RuntimeError(
                "OpenAI devolvió una respuesta sin contenido."
            )

        return {
            "provider": self.name,
            "model": self.model,
            "status": "completed",
            "content": content,
            "system_prompt": system_prompt,
            "metadata": {
                "response_id": response.id,
            },
        }
