from typing import Any, Dict

from atlas.llm.base_provider import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """
    Proveedor simulado para probar Atlas sin APIs externas.
    """

    name = "mock"
    model = "atlas-mock-1"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Devuelve una respuesta simulada y estructurada.
        """
        normalized_system_prompt = system_prompt.strip()
        normalized_user_prompt = user_prompt.strip()

        if not normalized_user_prompt:
            raise ValueError(
                "El mensaje del usuario no puede estar vacío."
            )

        return {
            "provider": self.name,
            "model": self.model,
            "status": "completed",
            "content": (
                "Respuesta generada por Atlas AI mediante el "
                "proveedor simulado. "
                f"Tarea recibida: {normalized_user_prompt}"
            ),
            "system_prompt": (
                normalized_system_prompt
                or "Sin instrucciones de sistema."
            ),
            "metadata": {
                "simulation": True,
                "options": kwargs,
            },
        }