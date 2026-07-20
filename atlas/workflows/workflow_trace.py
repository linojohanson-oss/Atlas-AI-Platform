import json
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional


class WorkflowTrace:
    """Persistencia JSONL para auditoría de workflows."""

    def __init__(self, memory_dir: str) -> None:
        self.path = Path(memory_dir) / "workflow_history.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def save(self, execution: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            with self.path.open("a", encoding="utf-8") as file:
                file.write(
                    json.dumps(
                        execution,
                        ensure_ascii=False,
                        default=str,
                    )
                    + "\n"
                )

        return execution

    def get_history(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []

        records: List[Dict[str, Any]] = []

        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

        if limit is not None:
            return records[-limit:]

        return records

    def get_last(self) -> Optional[Dict[str, Any]]:
        history = self.get_history(limit=1)
        return history[0] if history else None

    def count(self) -> int:
        return len(self.get_history())
