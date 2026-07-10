import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ExecutionMemory:
    """
    Memoria persistente de ejecuciones de Atlas AI Platform.

    Guarda cada tarea y su resultado en formato JSONL.
    Cada línea del archivo representa una ejecución independiente.
    """

    def __init__(self, memory_dir: Path) -> None:
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.history_file = (
            self.memory_dir / "execution_history.jsonl"
        )

    def save(
        self,
        task: str,
        result: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Guarda una ejecución en la memoria persistente.
        """
        normalized_task = task.strip()

        if not normalized_task:
            raise ValueError(
                "La tarea no puede estar vacía."
            )

        record = {
            "execution_id": str(uuid4()),
            "created_at": datetime.now().isoformat(),
            "task": normalized_task,
            "result": result,
            "metadata": metadata or {},
        }

        with self.history_file.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    default=str,
                )
                + "\n"
            )

        return record

    def get_history(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Devuelve el historial de ejecuciones.

        Si se indica un límite, devuelve las últimas ejecuciones.
        """
        if not self.history_file.exists():
            return []

        records: List[Dict[str, Any]] = []

        with self.history_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            for line in file:
                normalized_line = line.strip()

                if not normalized_line:
                    continue

                records.append(
                    json.loads(normalized_line)
                )

        if limit is not None:
            if limit < 1:
                raise ValueError(
                    "El límite debe ser mayor que cero."
                )

            return records[-limit:]

        return records

    def get_last(
        self,
    ) -> Optional[Dict[str, Any]]:
        """
        Devuelve la última ejecución guardada.
        """
        history = self.get_history(limit=1)

        if not history:
            return None

        return history[0]

    def count(self) -> int:
        """
        Devuelve la cantidad total de ejecuciones guardadas.
        """
        return len(self.get_history())

    def clear(self) -> None:
        """
        Elimina todo el historial de ejecuciones.
        """
        if self.history_file.exists():
            self.history_file.unlink()