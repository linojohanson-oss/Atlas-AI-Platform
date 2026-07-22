"""
Atlas AI Platform - Workflow Step

Define una etapa individual dentro de un workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class WorkflowStepStatus(str, Enum):
    """
    Estados posibles de un paso.
    """

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class WorkflowStepType(str, Enum):
    """
    Tipos de pasos soportados.
    """

    DEPARTMENT = "department"
    AGENT = "agent"
    EXECUTIVE = "executive"
    CUSTOM = "custom"


@dataclass
class WorkflowStep:
    """
    Representa una etapa ejecutable dentro de un workflow.
    """

    step_id: str
    name: str
    step_type: WorkflowStepType = (
        WorkflowStepType.DEPARTMENT
    )

    description: str = ""
    department_id: Optional[str] = None
    preferred_agent_id: Optional[str] = None

    required_capabilities: List[str] = field(
        default_factory=list
    )
    required_tools: List[str] = field(
        default_factory=list
    )
    required_permissions: List[str] = field(
        default_factory=list
    )

    depends_on: List[str] = field(
        default_factory=list
    )

    continue_on_error: bool = False
    optional: bool = False
    enabled: bool = True
    priority: int = 50

    input_template: Optional[str] = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    status: WorkflowStepStatus = (
        WorkflowStepStatus.PENDING
    )

    def __post_init__(self) -> None:
        """
        Valida y normaliza la definición.
        """

        self.step_id = str(self.step_id).strip()
        self.name = str(self.name).strip()
        self.description = str(
            self.description or ""
        ).strip()

        if not self.step_id:
            raise ValueError(
                "WorkflowStep requiere step_id."
            )

        if not self.name:
            raise ValueError(
                "WorkflowStep requiere name."
            )

        if isinstance(self.step_type, str):
            self.step_type = WorkflowStepType(
                self.step_type
            )

        if isinstance(self.status, str):
            self.status = WorkflowStepStatus(
                self.status
            )

        if self.department_id is not None:
            self.department_id = str(
                self.department_id
            ).strip() or None

        if self.preferred_agent_id is not None:
            self.preferred_agent_id = str(
                self.preferred_agent_id
            ).strip() or None

        self.required_capabilities = (
            self._normalize_string_list(
                self.required_capabilities
            )
        )

        self.required_tools = (
            self._normalize_string_list(
                self.required_tools
            )
        )

        self.required_permissions = (
            self._normalize_string_list(
                self.required_permissions
            )
        )

        self.depends_on = (
            self._normalize_string_list(
                self.depends_on
            )
        )

        self.metadata = dict(self.metadata or {})

        self.priority = int(self.priority)

        if self.step_id in self.depends_on:
            raise ValueError(
                "Un paso no puede depender de sí mismo."
            )

        if (
            self.step_type
            == WorkflowStepType.DEPARTMENT
            and not self.department_id
        ):
            raise ValueError(
                "Un paso de tipo department requiere "
                "department_id."
            )

        if (
            self.step_type
            == WorkflowStepType.AGENT
            and not self.preferred_agent_id
        ):
            raise ValueError(
                "Un paso de tipo agent requiere "
                "preferred_agent_id."
            )

    @property
    def is_terminal(self) -> bool:
        """
        Indica si el paso ya finalizó.
        """

        return self.status in {
            WorkflowStepStatus.COMPLETED,
            WorkflowStepStatus.FAILED,
            WorkflowStepStatus.SKIPPED,
            WorkflowStepStatus.BLOCKED,
        }

    @property
    def is_successful(self) -> bool:
        """
        Indica si el paso terminó correctamente.
        """

        return (
            self.status
            == WorkflowStepStatus.COMPLETED
        )

    @property
    def is_pending(self) -> bool:
        """
        Indica si todavía no comenzó.
        """

        return self.status in {
            WorkflowStepStatus.PENDING,
            WorkflowStepStatus.READY,
        }

    def can_run(
        self,
        completed_step_ids: List[str],
    ) -> bool:
        """
        Indica si todas las dependencias están completas.
        """

        if not self.enabled:
            return False

        completed = set(
            self._normalize_string_list(
                completed_step_ids
            )
        )

        return all(
            dependency in completed
            for dependency in self.depends_on
        )

    def mark_ready(self) -> None:
        self.status = WorkflowStepStatus.READY

    def mark_running(self) -> None:
        self.status = WorkflowStepStatus.RUNNING

    def mark_completed(self) -> None:
        self.status = WorkflowStepStatus.COMPLETED

    def mark_failed(self) -> None:
        self.status = WorkflowStepStatus.FAILED

    def mark_skipped(self) -> None:
        self.status = WorkflowStepStatus.SKIPPED

    def mark_blocked(self) -> None:
        self.status = WorkflowStepStatus.BLOCKED

    def reset(self) -> None:
        """
        Devuelve el paso al estado inicial.
        """

        self.status = WorkflowStepStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializa el paso.
        """

        return {
            "step_id": self.step_id,
            "name": self.name,
            "description": self.description,
            "step_type": self.step_type.value,
            "department_id": self.department_id,
            "preferred_agent_id": (
                self.preferred_agent_id
            ),
            "required_capabilities": list(
                self.required_capabilities
            ),
            "required_tools": list(
                self.required_tools
            ),
            "required_permissions": list(
                self.required_permissions
            ),
            "depends_on": list(self.depends_on),
            "continue_on_error": (
                self.continue_on_error
            ),
            "optional": self.optional,
            "enabled": self.enabled,
            "priority": self.priority,
            "input_template": self.input_template,
            "metadata": dict(self.metadata),
            "status": self.status.value,
            "is_terminal": self.is_terminal,
            "is_successful": self.is_successful,
        }

    @staticmethod
    def _normalize_string_list(
        values: Optional[List[str]],
    ) -> List[str]:
        """
        Normaliza listas de identificadores.
        """

        normalized: List[str] = []

        for value in values or []:
            item = str(value).strip()

            if item and item not in normalized:
                normalized.append(item)

        return normalized

    def __repr__(self) -> str:
        return (
            "WorkflowStep("
            f"step_id='{self.step_id}', "
            f"type='{self.step_type.value}', "
            f"status='{self.status.value}', "
            f"dependencies={len(self.depends_on)}"
            ")"
        )