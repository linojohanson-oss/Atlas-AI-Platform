"""
Atlas AI Platform - Fake Department Runtime

Runtime controlado para pruebas del WorkflowEngine.

No utiliza agentes reales, proveedores LLM ni servicios externos.
Devuelve resultados deterministas para validar la infraestructura
de workflows y observabilidad.
"""

from __future__ import annotations

from time import perf_counter, sleep
from typing import Any, Dict, List, Optional


class FakeDepartmentRuntime:
    """
    Simula DepartmentRuntime durante las pruebas.

    Cada departamento recibe un agente predefinido:

    - security    -> security-agent
    - engineering -> engineering-agent
    - operations  -> operations-agent
    """

    AGENTS_BY_DEPARTMENT = {
        "security": "security-agent",
        "engineering": "engineering-agent",
        "operations": "operations-agent",
    }

    def __init__(
        self,
        delay_seconds: float = 0.001,
    ) -> None:
        self.delay_seconds = max(
            float(delay_seconds),
            0.0,
        )

        self._is_ready = False
        self.execution_count = 0
        self.executions: List[Dict[str, Any]] = []

    @property
    def is_ready(self) -> bool:
        """
        Indica si el runtime está preparado.
        """

        return self._is_ready

    def start(self) -> None:
        """
        Inicia el runtime simulado.
        """

        self._is_ready = True

    def stop(self) -> None:
        """
        Detiene el runtime simulado.
        """

        self._is_ready = False

    def execute(
        self,
        department_id: str,
        task: Any,
        required_capabilities: Optional[
            List[str]
        ] = None,
        required_tools: Optional[
            List[str]
        ] = None,
        required_permissions: Optional[
            List[str]
        ] = None,
        preferred_agent_ids: Optional[
            List[str]
        ] = None,
        excluded_agent_ids: Optional[
            List[str]
        ] = None,
        strategy: Any = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta una tarea simulada y devuelve un resultado compatible
        con DepartmentRuntime.
        """

        if not self._is_ready:
            raise RuntimeError(
                "FakeDepartmentRuntime no está iniciado."
            )

        normalized_department_id = str(
            department_id
        ).strip()

        if not normalized_department_id:
            raise ValueError(
                "department_id no puede estar vacío."
            )

        preferred_agents = list(
            preferred_agent_ids or []
        )

        if preferred_agents:
            agent_id = preferred_agents[0]
        else:
            agent_id = self.AGENTS_BY_DEPARTMENT.get(
                normalized_department_id,
                f"{normalized_department_id}-agent",
            )

        started_counter = perf_counter()

        if self.delay_seconds > 0:
            sleep(self.delay_seconds)

        duration_seconds = round(
            perf_counter() - started_counter,
            6,
        )

        self.execution_count += 1

        execution = {
            "message": (
                f"Tarea ejecutada por {agent_id}"
            ),
            "department_id": (
                normalized_department_id
            ),
            "agent_id": agent_id,
            "task": task,
            "success": True,
        }

        response = {
            "runtime": "fake-department-runtime",
            "task_id": (
                f"fake-task-{self.execution_count}"
            ),
            "status": "completed",
            "department": {
                "department_id": (
                    normalized_department_id
                ),
                "name": (
                    normalized_department_id.title()
                ),
            },
            "agent_id": agent_id,
            "selected_agent": {
                "agent_id": agent_id,
                "department_id": (
                    normalized_department_id
                ),
                "score": 1.0,
            },
            "execution": execution,
            "duration_seconds": duration_seconds,
            "metadata": dict(metadata or {}),
        }

        self.executions.append(response)

        return response

    def summary(self) -> Dict[str, Any]:
        """
        Devuelve un resumen del runtime simulado.
        """

        return {
            "is_ready": self.is_ready,
            "execution_count": (
                self.execution_count
            ),
            "agents": [
                item.get("agent_id")
                for item in self.executions
            ],
        }