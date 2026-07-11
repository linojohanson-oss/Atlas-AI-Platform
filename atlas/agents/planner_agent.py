import re
import unicodedata
from typing import Any, Dict, Optional

from atlas.agents.base_agent import BaseAgent
from atlas.kernel.capability_manager import CapabilityManager
from atlas.kernel.llm_manager import LLMManager
from atlas.kernel.tool_manager import ToolManager


class PlannerAgent(BaseAgent):
    """
    Planificador central de Atlas AI Platform.

    Flujo:
    1. Detecta la intención.
    2. Resuelve la capacidad necesaria.
    3. Obtiene la herramienta asociada.
    4. Ejecuta la herramienta.
    5. Construye una respuesta uniforme.
    """

    name = "planner-agent"

    description = (
        "Analiza tareas, resuelve capacidades y coordina "
        "automáticamente agentes y herramientas."
    )

    capabilities = [
        "intent_detection",
        "capability_resolution",
        "tool_selection",
        "tool_execution",
        "task_planning",
        "general_reasoning",
    ]

    INTENT_CAPABILITIES = {
        "calculation": "mathematics",
        "file_analysis": "filesystem",
        "excel_analysis": "spreadsheet",
    }

    def __init__(
        self,
        llm_manager: LLMManager,
        tool_manager: ToolManager,
        capability_manager: CapabilityManager,
    ) -> None:
        self.llm_manager = llm_manager
        self.tool_manager = tool_manager
        self.capability_manager = capability_manager

    def execute(
        self,
        task: str,
    ) -> Dict[str, Any]:
        """
        Ejecuta el ciclo completo de planificación.
        """
        normalized_task = task.strip()

        if not normalized_task:
            raise ValueError(
                "La tarea no puede estar vacía."
            )

        intent = self._detect_intent(
            normalized_task
        )

        if intent == "general":
            return self._fallback_to_llm(
                normalized_task
            )

        capability = self._resolve_capability(
            intent
        )

        tool_name = self._select_tool(
            capability
        )

        tool_arguments = self._build_tool_arguments(
            intent=intent,
            task=normalized_task,
        )

        tool_result = self._execute_tool(
            tool_name=tool_name,
            tool_arguments=tool_arguments,
        )

        return self._build_response(
            task=normalized_task,
            intent=intent,
            capability=capability,
            tool_name=tool_name,
            tool_arguments=tool_arguments,
            tool_result=tool_result,
        )

    # ======================================================
    # INTENCIÓN
    # ======================================================

    def _detect_intent(
        self,
        task: str,
    ) -> str:
        """
        Detecta la intención principal de la tarea.
        """
        if self._detect_excel_path(task):
            return "excel_analysis"

        if self._detect_calculation(task):
            return "calculation"

        if self._detect_file_path(task):
            return "file_analysis"

        return "general"

    # ======================================================
    # CAPACIDAD Y HERRAMIENTA
    # ======================================================

    def _resolve_capability(
        self,
        intent: str,
    ) -> str:
        """
        Convierte una intención en una capacidad.
        """
        capability = self.INTENT_CAPABILITIES.get(
            intent
        )

        if capability is None:
            raise KeyError(
                f"No existe una capacidad asociada "
                f"a la intención '{intent}'."
            )

        return capability

    def _select_tool(
        self,
        capability: str,
    ) -> str:
        """
        Obtiene la herramienta que implementa una capacidad.
        """
        return self.capability_manager.resolve(
            capability
        )

    # ======================================================
    # ARGUMENTOS
    # ======================================================

    def _build_tool_arguments(
        self,
        intent: str,
        task: str,
    ) -> Dict[str, Any]:
        """
        Construye los argumentos requeridos por la herramienta.
        """
        if intent == "calculation":
            expression = self._detect_calculation(
                task
            )

            if expression is None:
                raise ValueError(
                    "No se pudo obtener la expresión matemática."
                )

            return {
                "expression": expression,
            }

        if intent == "excel_analysis":
            excel_path = self._detect_excel_path(
                task
            )

            if excel_path is None:
                raise ValueError(
                    "No se pudo detectar el archivo Excel."
                )

            arguments: Dict[str, Any] = {
                "file_path": excel_path,
                "preview_rows": 5,
            }

            sheet_name = self._detect_sheet_name(
                task
            )

            if sheet_name:
                arguments["sheet_name"] = sheet_name

            return arguments

        if intent == "file_analysis":
            file_path = self._detect_file_path(
                task
            )

            if file_path is None:
                raise ValueError(
                    "No se pudo detectar el archivo."
                )

            return {
                "file_path": file_path,
            }

        raise ValueError(
            f"No se pueden construir argumentos "
            f"para la intención '{intent}'."
        )

    # ======================================================
    # EJECUCIÓN
    # ======================================================

    def _execute_tool(
        self,
        tool_name: str,
        tool_arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Ejecuta la herramienta seleccionada.
        """
        return self.tool_manager.execute(
            tool_name=tool_name,
            **tool_arguments,
        )

    # ======================================================
    # RESPUESTA
    # ======================================================

    def _build_response(
        self,
        task: str,
        intent: str,
        capability: str,
        tool_name: str,
        tool_arguments: Dict[str, Any],
        tool_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Construye una respuesta uniforme.
        """
        output = self._format_output(
            intent=intent,
            tool_result=tool_result,
        )

        return {
            "agent": self.name,
            "status": "completed",
            "task": task,
            "intent": intent,
            "capability": capability,
            "selected_tool": tool_name,
            "tool_input": tool_arguments,
            "tool_result": tool_result,
            "plan": [
                {
                    "step": 1,
                    "action": "detect_intent",
                    "result": intent,
                },
                {
                    "step": 2,
                    "action": "resolve_capability",
                    "result": capability,
                },
                {
                    "step": 3,
                    "action": "select_tool",
                    "result": tool_name,
                },
                {
                    "step": 4,
                    "action": "execute_tool",
                    "arguments": tool_arguments,
                },
                {
                    "step": 5,
                    "action": "return_result",
                },
            ],
            "output": output,
        }

    def _format_output(
        self,
        intent: str,
        tool_result: Dict[str, Any],
    ) -> str:
        """
        Genera una respuesta legible según la intención.
        """
        if intent == "calculation":
            expression = tool_result["input"]["expression"]
            result = tool_result["result"]

            return (
                f"El resultado de {expression} "
                f"es {result}."
            )

        if intent == "file_analysis":
            file_data = tool_result["result"]

            return (
                f"Archivo analizado: {file_data['name']}. "
                f"Extensión: {file_data['extension']}. "
                f"Tamaño: {file_data['size_bytes']} bytes. "
                f"Líneas: "
                f"{file_data.get('line_count', 'N/D')}."
            )

        if intent == "excel_analysis":
            excel_data = tool_result["result"]

            numeric_summary = excel_data.get(
                "numeric_summary",
                {},
            )

            summary_parts = []

            for column_name, statistics in (
                numeric_summary.items()
            ):
                summary_parts.append(
                    f"{column_name}: "
                    f"promedio {statistics['mean']:.2f}, "
                    f"total {statistics['sum']:.2f}"
                )

            statistics_text = (
                "; ".join(summary_parts)
                if summary_parts
                else "No se detectaron columnas numéricas."
            )

            return (
                f"Excel analizado: "
                f"{excel_data['file_name']}. "
                f"Hoja: {excel_data['selected_sheet']}. "
                f"Filas: {excel_data['row_count']}. "
                f"Columnas: {excel_data['column_count']}. "
                f"Encabezados: "
                f"{', '.join(excel_data['headers'])}. "
                f"Estadísticas: {statistics_text}."
            )

        return str(tool_result)

    # ======================================================
    # FALLBACK LLM
    # ======================================================

    def _fallback_to_llm(
        self,
        task: str,
    ) -> Dict[str, Any]:
        """
        Utiliza el proveedor LLM para tareas generales.
        """
        llm_response = self.llm_manager.generate(
            system_prompt=(
                "Sos el Planner Agent de Atlas AI Platform. "
                "Respondé de forma clara, precisa y estructurada."
            ),
            user_prompt=task,
        )

        return {
            "agent": self.name,
            "status": llm_response["status"],
            "task": task,
            "intent": "general",
            "capability": "general_reasoning",
            "selected_tool": None,
            "provider": llm_response["provider"],
            "model": llm_response["model"],
            "plan": [
                {
                    "step": 1,
                    "action": "detect_intent",
                    "result": "general",
                },
                {
                    "step": 2,
                    "action": "use_llm",
                    "provider": llm_response["provider"],
                    "model": llm_response["model"],
                },
                {
                    "step": 3,
                    "action": "return_result",
                },
            ],
            "output": llm_response["content"],
            "metadata": llm_response.get(
                "metadata",
                {},
            ),
        }

    # ======================================================
    # DETECTORES
    # ======================================================

    def _detect_excel_path(
        self,
        task: str,
    ) -> Optional[str]:
        """
        Detecta archivos Excel.
        """
        match = re.search(
            r"([A-Za-z0-9_\-./\\]+\."
            r"(?:xlsx|xlsm))",
            task,
            re.IGNORECASE,
        )

        return (
            match.group(1)
            if match
            else None
        )

    def _detect_file_path(
        self,
        task: str,
    ) -> Optional[str]:
        """
        Detecta archivos de texto o código.
        """
        normalized_text = self._normalize_text(
            task
        )

        file_words = {
            "analiza",
            "analizar",
            "archivo",
            "lee",
            "leer",
            "revisa",
            "inspecciona",
        }

        if not any(
            word in normalized_text
            for word in file_words
        ):
            return None

        match = re.search(
            r"([A-Za-z0-9_\-./\\]+\."
            r"(?:txt|md|py|json|csv|yaml|yml|"
            r"html|css|js))",
            task,
            re.IGNORECASE,
        )

        return (
            match.group(1)
            if match
            else None
        )

    def _detect_sheet_name(
        self,
        task: str,
    ) -> Optional[str]:
        """
        Detecta frases como: hoja Ventas.
        """
        match = re.search(
            r"(?:hoja|sheet)\s+"
            r"['\"]?([A-Za-z0-9 _\-]+)['\"]?",
            task,
            re.IGNORECASE,
        )

        if not match:
            return None

        return match.group(1).strip()

    def _detect_calculation(
        self,
        task: str,
    ) -> Optional[str]:
        """
        Detecta expresiones matemáticas.
        """
        normalized_text = self._normalize_text(
            task
        )

        percentage_with_extra = re.search(
            r"(\d+(?:[.,]\d+)?)\s*%\s*de\s*"
            r"(\d+(?:[.,]\d+)?)\s*"
            r"(?:mas|\+)\s*"
            r"(\d+(?:[.,]\d+)?)",
            normalized_text,
        )

        if percentage_with_extra:
            percentage = self._normalize_number(
                percentage_with_extra.group(1)
            )
            base = self._normalize_number(
                percentage_with_extra.group(2)
            )
            extra = self._normalize_number(
                percentage_with_extra.group(3)
            )

            return (
                f"({base} * {percentage}) "
                f"/ 100 + {extra}"
            )

        percentage = re.search(
            r"(\d+(?:[.,]\d+)?)\s*%\s*de\s*"
            r"(\d+(?:[.,]\d+)?)",
            normalized_text,
        )

        if percentage:
            percentage_value = self._normalize_number(
                percentage.group(1)
            )
            base = self._normalize_number(
                percentage.group(2)
            )

            return (
                f"({base} * {percentage_value}) "
                "/ 100"
            )

        calculation_words = {
            "calcula",
            "calcular",
            "cuanto es",
            "resultado de",
            "resolve",
        }

        if not any(
            word in normalized_text
            for word in calculation_words
        ):
            return None

        expression_match = re.search(
            r"[-+*/%().\d\s]{3,}",
            normalized_text,
        )

        if not expression_match:
            return None

        expression = expression_match.group(0).strip()

        if any(
            symbol in expression
            for symbol in (
                "+",
                "-",
                "*",
                "/",
                "%",
            )
        ):
            return expression

        return None

    # ======================================================
    # NORMALIZACIÓN
    # ======================================================

    @staticmethod
    def _normalize_text(
        text: str,
    ) -> str:
        normalized = unicodedata.normalize(
            "NFKD",
            text.lower(),
        )

        return "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        )

    @staticmethod
    def _normalize_number(
        value: str,
    ) -> str:
        return value.replace(",", ".")