from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class WorkflowStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WorkflowStepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class WorkflowStepDefinition:
    name: str
    agent_name: str
    instruction: str
    description: str = ""


@dataclass
class WorkflowDefinition:
    name: str
    description: str
    steps: List[WorkflowStepDefinition]
    version: str = "1.0"


@dataclass
class WorkflowStepResult:
    name: str
    agent_name: str
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_ms: Optional[float] = None
    input_text: Optional[str] = None
    output: Any = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass
class WorkflowExecution:
    workflow_name: str
    prompt: str
    workflow_id: str = field(
        default_factory=lambda: (
            f"WF-{datetime.now().strftime('%Y%m%d-%H%M%S')}-"
            f"{uuid4().hex[:6].upper()}"
        )
    )
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_ms: Optional[float] = None
    steps: List[WorkflowStepResult] = field(default_factory=list)
    final_result: Any = None
    confidence: float = 0.0
    review_status: str = "PENDING"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "prompt": self.prompt,
            "status": self.status.value,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "steps": [step.to_dict() for step in self.steps],
            "final_result": self.final_result,
            "confidence": self.confidence,
            "review_status": self.review_status,
            "error": self.error,
        }
