from __future__ import annotations

from typing import Any, Dict, Optional

from atlas.llm.base_provider import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """
    Proveedor simulado para probar Atlas sin APIs externas.

    Genera respuestas compactas y deterministas sin repetir
    íntegramente los prompts recibidos.
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

        El contenido no replica el prompt completo para evitar
        crecimiento recursivo durante la ejecución de workflows.
        """

        normalized_system_prompt = str(
            system_prompt or ""
        ).strip()

        normalized_user_prompt = str(
            user_prompt or ""
        ).strip()

        if not normalized_user_prompt:
            raise ValueError(
                "El mensaje del usuario no puede estar vacío."
            )

        request = self._extract_request(
            normalized_user_prompt
        )

        step_name = self._extract_field(
            normalized_user_prompt,
            labels=(
                "Paso actual",
                "Paso",
                "Etapa",
                "Tarea",
            ),
        )

        content = self._build_simulated_content(
            request=request,
            step_name=step_name,
        )

        return {
            "provider": self.name,
            "model": self.model,
            "status": "completed",
            "content": content,
            "metadata": {
                "simulation": True,
                "system_prompt_length": len(
                    normalized_system_prompt
                ),
                "user_prompt_length": len(
                    normalized_user_prompt
                ),
                "request_preview": request[:300],
                "options": dict(kwargs),
            },
        }

    # ============================================================
    # Construcción de respuesta
    # ============================================================

    @staticmethod
    def _build_simulated_content(
        request: str,
        step_name: Optional[str],
    ) -> str:
        """
        Construye una respuesta compacta para pruebas.
        """

        parts = [
            "Atlas AI completó la ejecución simulada.",
        ]

        if step_name:
            parts.append(
                f"Etapa procesada: {step_name}."
            )

        if request:
            parts.append(
                f"Solicitud analizada: {request[:300]}"
            )

        parts.append(
            "Resultado: análisis generado correctamente "
            "por el proveedor local de pruebas."
        )

        return " ".join(parts)

    # ============================================================
    # Extracción compacta de contexto
    # ============================================================

    @classmethod
    def _extract_request(
        cls,
        prompt: str,
    ) -> str:
        """
        Busca la solicitud principal dentro del prompt.

        Nunca devuelve el prompt completo.
        """

        value = cls._extract_field(
            prompt,
            labels=(
                "Solicitud original",
                "Solicitud principal",
                "Solicitud",
                "Requerimiento",
                "Objetivo",
                "Petición",
            ),
        )

        if value:
            return value[:500]

        for line in prompt.splitlines():
            normalized_line = line.strip()

            if normalized_line:
                return normalized_line[:500]

        return "Solicitud no identificada."

    @staticmethod
    def _extract_field(
        prompt: str,
        labels: tuple[str, ...],
    ) -> Optional[str]:
        """
        Extrae el contenido de una línea etiquetada.

        Ejemplo:
            Solicitud original: Revisar una API
        """

        normalized_labels = tuple(
            label.strip().lower()
            for label in labels
        )

        lines = prompt.splitlines()

        for index, line in enumerate(lines):
            stripped_line = line.strip()

            if not stripped_line:
                continue

            lowered_line = (
                stripped_line.lower()
            )

            for label in normalized_labels:
                prefix = f"{label}:"

                if lowered_line.startswith(
                    prefix
                ):
                    value = stripped_line[
                        len(prefix):
                    ].strip()

                    if value:
                        return value[:500]

                    # Permite formatos donde el valor está
                    # en la línea inmediatamente siguiente.
                    for next_line in lines[
                        index + 1:
                    ]:
                        next_value = (
                            next_line.strip()
                        )

                        if next_value:
                            return next_value[:500]

        return None