from typing import Any, Dict, List

from atlas.kernel.event_bus import EventBus
from atlas.tools.base_tool import BaseTool


class ToolManager:
    """Registra, administra y ejecuta herramientas de Atlas."""

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        tool_name = self._normalize_name(tool.name)

        if tool_name in self._tools:
            raise ValueError(
                f"La herramienta '{tool_name}' ya está registrada."
            )

        self._tools[tool_name] = tool

        self.event_bus.publish(
            "tool.registered",
            tool.information(),
        )

    def get(self, tool_name: str) -> BaseTool:
        normalized_name = self._normalize_name(tool_name)

        if normalized_name not in self._tools:
            raise KeyError(
                f"La herramienta '{normalized_name}' no está registrada."
            )

        return self._tools[normalized_name]

    def execute(
        self,
        tool_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        tool = self.get(tool_name)

        self.event_bus.publish(
            "tool.execution.started",
            {
                "tool": tool.name,
                "arguments": kwargs,
            },
        )

        try:
            result = tool.execute(**kwargs)

            self.event_bus.publish(
                "tool.execution.completed",
                result,
            )

            return result

        except Exception as exc:
            self.event_bus.publish(
                "tool.execution.failed",
                {
                    "tool": tool.name,
                    "error": str(exc),
                },
            )
            raise

    def list_names(self) -> List[str]:
        return sorted(self._tools.keys())

    def count(self) -> int:
        return len(self._tools)

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized_name = name.strip().lower()

        if not normalized_name:
            raise ValueError(
                "El nombre de la herramienta no puede estar vacío."
            )

        return normalized_name
