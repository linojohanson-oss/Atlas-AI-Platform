import json
import urllib.request
from typing import Any, Dict

from atlas.llm.base_provider import BaseLLMProvider


class OllamaLLMProvider(BaseLLMProvider):
    """
    Proveedor LLM local mediante Ollama.
    """

    name = "ollama"
    model = "qwen3:1.7b"

    def __init__(self, base_url: str = "http://127.0.0.1:11434") -> None:
        self.base_url = base_url.rstrip("/")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        normalized_prompt = user_prompt.strip()

        if not normalized_prompt:
            raise ValueError(
                "El mensaje del usuario no puede estar vacÃ­o."
            )

        payload = {
            "model": self.model,
            "prompt": normalized_prompt,
            "system": system_prompt,
            "stream": False,
            "think": False,
        }

        request = urllib.request.Request(
            url=f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=800) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )
        except Exception as exc:
            raise RuntimeError(
                f"Error conectando con Ollama: {exc}"
            ) from exc

        content = str(result.get("response", "")).strip()

        if not content:
            raise RuntimeError(
                "Ollama devolviÃ³ una respuesta sin contenido."
            )

        return {
            "provider": self.name,
            "model": self.model,
            "status": "completed",
            "content": content,
            "system_prompt": system_prompt,
            "metadata": {
                "done": result.get("done"),
                "done_reason": result.get("done_reason"),
                "total_duration": result.get("total_duration"),
                "eval_count": result.get("eval_count"),
            },
        }

