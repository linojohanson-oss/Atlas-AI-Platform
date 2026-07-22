from __future__ import annotations

from typing import Any, Dict, List

from atlas.agents.base_agent import BaseAgent
from atlas.kernel.event_bus import EventBus


class AgentManager:
    """
    Administra los agentes disponibles en Atlas AI Platform.

    Permite registrar, consultar, eliminar y ejecutar agentes.
    Acepta tareas de texto y tareas estructuradas.
    """

    def __init__(
        self,
        event_bus: EventBus,
    ) -> None:
        if event_bus is None:
            raise ValueError(
                "event_bus no puede ser None."
            )

        self.event_bus = event_bus
        self._agents: Dict[
            str,
            BaseAgent,
        ] = {}

    # ============================================================
    # Registro y consulta
    # ============================================================

    def register(
        self,
        agent: BaseAgent,
    ) -> None:
        """
        Registra un agente.
        """

        if not isinstance(
            agent,
            BaseAgent,
        ):
            raise TypeError(
                "agent debe ser una instancia de BaseAgent."
            )

        agent_name = self._normalize_name(
            agent.name
        )

        if agent_name in self._agents:
            raise ValueError(
                f"El agente '{agent_name}' "
                "ya está registrado."
            )

        self._agents[
            agent_name
        ] = agent

        self.event_bus.publish(
            "agent.registered",
            {
                "agent": agent_name,
                "description": (
                    agent.description
                ),
                "capabilities": list(
                    agent.capabilities
                ),
            },
        )

    def get(
        self,
        agent_name: str,
    ) -> BaseAgent:
        """
        Obtiene un agente por nombre.
        """

        normalized_name = (
            self._normalize_name(
                agent_name
            )
        )

        if (
            normalized_name
            not in self._agents
        ):
            raise KeyError(
                f"El agente "
                f"'{normalized_name}' "
                "no está registrado."
            )

        return self._agents[
            normalized_name
        ]

    def remove(
        self,
        agent_name: str,
    ) -> None:
        """
        Elimina un agente.
        """

        normalized_name = (
            self._normalize_name(
                agent_name
            )
        )

        if (
            normalized_name
            not in self._agents
        ):
            raise KeyError(
                f"El agente "
                f"'{normalized_name}' "
                "no está registrado."
            )

        del self._agents[
            normalized_name
        ]

        self.event_bus.publish(
            "agent.removed",
            {
                "agent": normalized_name,
            },
        )

    # ============================================================
    # Ejecución
    # ============================================================

    def execute(
        self,
        agent_name: str,
        task: Any,
    ) -> Dict[str, Any]:
        """
        Ejecuta una tarea utilizando un agente registrado.

        La tarea puede ser texto plano o una estructura compleja,
        como un diccionario generado por WorkflowEngine.
        """

        agent = self.get(
            agent_name
        )

        task_summary = (
            self._task_summary(
                task
            )
        )

        self.event_bus.publish(
            "agent.started",
            {
                "agent": agent.name,
                "task": task_summary,
            },
        )

        try:
            result = agent.execute(
                task
            )

            if not isinstance(
                result,
                dict,
            ):
                result = {
                    "agent": agent.name,
                    "status": "completed",
                    "output": result,
                }

            self.event_bus.publish(
                "agent.completed",
                self._result_summary(
                    agent_name=agent.name,
                    result=result,
                ),
            )

            return result

        except Exception as exc:
            self.event_bus.publish(
                "agent.failed",
                {
                    "agent": agent.name,
                    "task": task_summary,
                    "error": str(exc),
                },
            )

            raise

    # ============================================================
    # Listados
    # ============================================================

    def list_agents(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Devuelve información de todos los agentes.
        """

        return [
            agent.information()
            for agent
            in self._agents.values()
        ]

    def list_names(
        self,
    ) -> List[str]:
        """
        Devuelve los nombres de los agentes registrados.
        """

        return sorted(
            self._agents.keys()
        )

    def count(
        self,
    ) -> int:
        """
        Devuelve la cantidad de agentes registrados.
        """

        return len(
            self._agents
        )

    # ============================================================
    # Utilidades
    # ============================================================

    @staticmethod
    def _task_summary(
        task: Any,
    ) -> Dict[str, Any]:
        """
        Genera una representación compacta de la tarea.

        Evita publicar en EventBus el contexto completo de un
        workflow y todos sus resultados anteriores.
        """

        if isinstance(
            task,
            dict,
        ):
            previous_results = task.get(
                "previous_results",
                {},
            )

            dependency_ids = (
                list(
                    previous_results.keys()
                )
                if isinstance(
                    previous_results,
                    dict,
                )
                else []
            )

            return {
                "type": "structured-task",
                "workflow_id": task.get(
                    "workflow_id"
                ),
                "execution_id": task.get(
                    "execution_id"
                ),
                "step_id": task.get(
                    "step_id"
                ),
                "request": str(
                    task.get(
                        "request",
                        "",
                    )
                )[:500],
                "dependency_ids": (
                    dependency_ids
                ),
            }

        return {
            "type": "text-task",
            "content": str(
                task
            )[:500],
        }

    @staticmethod
    def _result_summary(
        agent_name: str,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Genera un resumen compacto del resultado para EventBus.
        """

        output = result.get(
            "output"
        )

        if output is not None:
            output_preview = str(
                output
            )[:500]
        else:
            output_preview = None

        summary = {
            "agent": agent_name,
            "status": result.get(
                "status",
                "completed",
            ),
            "provider": result.get(
                "provider"
            ),
            "model": result.get(
                "model"
            ),
            "output_preview": (
                output_preview
            ),
        }

        return {
            key: value
            for key, value
            in summary.items()
            if value is not None
        }

    @staticmethod
    def _normalize_name(
        agent_name: str,
    ) -> str:
        normalized_name = str(
            agent_name
        ).strip().lower()

        if not normalized_name:
            raise ValueError(
                "El nombre del agente "
                "no puede estar vacío."
            )

        return normalized_name