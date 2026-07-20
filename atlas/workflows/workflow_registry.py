from typing import Dict, List

from atlas.workflows.workflow_models import WorkflowDefinition


class WorkflowRegistry:
    """Registro central de workflows disponibles."""

    def __init__(self) -> None:
        self._workflows: Dict[str, WorkflowDefinition] = {}

    def register(self, workflow: WorkflowDefinition) -> None:
        normalized_name = workflow.name.strip().lower()

        if not normalized_name:
            raise ValueError("El nombre del workflow no puede estar vacío.")

        self._workflows[normalized_name] = workflow

    def get(self, workflow_name: str) -> WorkflowDefinition:
        normalized_name = workflow_name.strip().lower()

        if normalized_name not in self._workflows:
            available = ", ".join(self.list_names()) or "ninguno"
            raise KeyError(
                f"Workflow no registrado: '{workflow_name}'. "
                f"Disponibles: {available}"
            )

        return self._workflows[normalized_name]

    def list_names(self) -> List[str]:
        return sorted(self._workflows.keys())

    def count(self) -> int:
        return len(self._workflows)
