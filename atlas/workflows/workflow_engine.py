"""
Atlas AI Platform - Workflow Engine

Motor central para ejecutar workflows departamentales.

Responsabilidades:

- Recuperar workflows desde WorkflowRegistry.
- Crear y administrar WorkflowContext.
- Resolver dependencias entre pasos.
- Ejecutar departamentos mediante DepartmentRuntime.
- Registrar pasos completados, fallidos, omitidos y bloqueados.
- Consolidar WorkflowResult.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from time import perf_counter
from typing import Any, Dict, List, Optional
from uuid import uuid4

from atlas.enterprise.agent_selector import (
    SelectionStrategy,
)
from atlas.enterprise.department_runtime import (
    DepartmentRuntime,
)
from atlas.workflows.workflow_context import (
    WorkflowContext,
)
from atlas.workflows.workflow_definition import (
    WorkflowDefinition,
)
from atlas.workflows.workflow_registry import (
    WorkflowRegistry,
)
from atlas.workflows.workflow_result import (
    WorkflowResult,
)
from atlas.workflows.workflow_step import (
    WorkflowStep,
    WorkflowStepStatus,
    WorkflowStepType,
)
from atlas.workflows.workflow_event_bus import (
    WorkflowEventBus,
    WorkflowEventType,
)

class WorkflowEngineStatus(str, Enum):
    """
    Estados posibles del motor.
    """

    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class WorkflowEngine:
    """
    Motor de ejecución de workflows de Atlas AI.
    """

    def __init__(
            self,
            department_runtime: DepartmentRuntime,
            workflow_registry: WorkflowRegistry,
            event_bus: Optional[
                WorkflowEventBus
            ] = None,
    ) -> None:
        if department_runtime is None:
            raise ValueError(
                "department_runtime no puede ser None."
            )

        if workflow_registry is None:
            raise ValueError(
                "workflow_registry no puede ser None."
            )

        if not hasattr(
            department_runtime,
            "execute",
        ):
            raise TypeError(
                "department_runtime no implementa "
                "el método execute()."
            )

        if not isinstance(
            workflow_registry,
            WorkflowRegistry,
        ):
            raise TypeError(
                "workflow_registry debe ser una "
                "instancia de WorkflowRegistry."
            )

        self.department_runtime = (
            department_runtime
        )

        self.workflow_registry = (
            workflow_registry
        )
        if (
                event_bus is not None
                and not isinstance(
            event_bus,
            WorkflowEventBus,
        )
        ):
            raise TypeError(
                "event_bus debe ser una instancia "
                "de WorkflowEventBus o None."
            )

        self.event_bus = (
                event_bus
                or WorkflowEventBus()
        )
        self._status = (
            WorkflowEngineStatus.CREATED
        )

        self._executions: Dict[
            str,
            WorkflowResult,
        ] = {}

        self._created_at = (
            datetime.now().isoformat()
        )

        self._started_at: Optional[str] = None
        self._stopped_at: Optional[str] = None
        self._last_error: Optional[str] = None

        self._execution_count = 0
        self._successful_executions = 0
        self._partial_executions = 0
        self._failed_executions = 0

    # ============================================================
    # Propiedades
    # ============================================================

    @property
    def status(self) -> WorkflowEngineStatus:
        return self._status

    @property
    def is_ready(self) -> bool:
        return self._status in {
            WorkflowEngineStatus.READY,
            WorkflowEngineStatus.RUNNING,
        }

    @property
    def execution_count(self) -> int:
        return self._execution_count

    @property
    def active_execution_count(self) -> int:
        return sum(
            1
            for result in self._executions.values()
            if result.status.value == "running"
        )

    # ============================================================
    # Ciclo de vida
    # ============================================================

    def start(self) -> None:
        """
        Inicia el motor.
        """

        if self.is_ready:
            return

        if not self.department_runtime.is_ready:
            self.department_runtime.start()

        self._status = (
            WorkflowEngineStatus.READY
        )

        self._started_at = (
            datetime.now().isoformat()
        )

        self._stopped_at = None
        self._last_error = None

    def stop(self) -> None:
        """
        Detiene el motor.
        """

        if (
            self._status
            == WorkflowEngineStatus.STOPPED
        ):
            return

        self._status = (
            WorkflowEngineStatus.STOPPING
        )

        self._status = (
            WorkflowEngineStatus.STOPPED
        )

        self._stopped_at = (
            datetime.now().isoformat()
        )

    # ============================================================
    # Ejecución pública
    # ============================================================

    def execute(
        self,
        workflow_id: str,
        request: str,
        variables: Optional[
            Dict[str, Any]
        ] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> WorkflowResult:
        """
        Ejecuta un workflow registrado.
        """

        self._ensure_ready()

        normalized_request = str(
            request
        ).strip()

        if not normalized_request:
            raise ValueError(
                "La solicitud del workflow "
                "no puede estar vacía."
            )

        workflow = self.workflow_registry.require(
            workflow_id=workflow_id,
            enabled_only=True,
            clone=True,
        )

        return self.execute_definition(
            workflow=workflow,
            request=normalized_request,
            variables=variables,
            metadata=metadata,
        )

    def execute_definition(
        self,
        workflow: WorkflowDefinition,
        request: str,
        variables: Optional[
            Dict[str, Any]
        ] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> WorkflowResult:
        """
        Ejecuta directamente una definición.
        """

        self._ensure_ready()

        if not isinstance(
            workflow,
            WorkflowDefinition,
        ):
            raise TypeError(
                "workflow debe ser una instancia "
                "de WorkflowDefinition."
            )

        workflow.validate()

        if not workflow.enabled:
            raise RuntimeError(
                f"El workflow "
                f"'{workflow.workflow_id}' "
                "está deshabilitado."
            )

        normalized_request = str(
            request
        ).strip()

        if not normalized_request:
            raise ValueError(
                "La solicitud del workflow "
                "no puede estar vacía."
            )

        execution_id = str(uuid4())

        context = WorkflowContext(
            workflow_id=workflow.workflow_id,
            execution_id=execution_id,
            request=normalized_request,
            variables=dict(variables or {}),
            metadata=dict(metadata or {}),
        )

        result = WorkflowResult(
            workflow_id=workflow.workflow_id,
            execution_id=execution_id,
            request=normalized_request,
            metadata={
                "workflow_name": workflow.name,
                "workflow_version": workflow.version,
                "strategy": workflow.strategy.value,
                **dict(metadata or {}),
            },
        )

        self._executions[
            execution_id
        ] = result

        self._execution_count += 1
        self._status = (
            WorkflowEngineStatus.RUNNING
        )

        result.start()
        expected_steps = [
            {
                "step_id": step.step_id,
                "step_name": step.name,
                "department_id": (
                    step.department_id
                ),
                "agent_id": (
                    step.preferred_agent_id
                ),
                "step_type": (
                    step.step_type.value
                ),
            }
            for step in workflow.steps
        ]
        self._publish_event(
            event_type=(
                WorkflowEventType
                .WORKFLOW_STARTED
                .value
            ),
            context=context,
            data={
                "workflow_name": (
                    workflow.name
                ),
                "workflow_version": (
                    workflow.version
                ),
                "step_count": (
                    workflow.step_count
                ),
                "expected_steps": (
                    expected_steps
                ),
                "request": (
                    normalized_request
                ),
                "status": "running",
            },
        )
        try:
            workflow.reset_steps()

            execution_order = (
                workflow.execution_order()
            )

            stop_execution = False

            for step in execution_order:
                if stop_execution:
                    self._block_step(
                        step=step,
                        context=context,
                        result=result,
                        reason=(
                            "La ejecución fue detenida "
                            "por un error anterior."
                        ),
                    )
                    continue

                if not step.enabled:
                    self._skip_step(
                        step=step,
                        context=context,
                        result=result,
                        reason=(
                            "El paso está deshabilitado."
                        ),
                    )
                    continue

                dependency_problem = (
                    self._dependency_problem(
                        step=step,
                        workflow=workflow,
                    )
                )

                if dependency_problem:
                    self._block_step(
                        step=step,
                        context=context,
                        result=result,
                        reason=dependency_problem,
                    )
                    continue

                try:
                    self._execute_step(
                        workflow=workflow,
                        step=step,
                        context=context,
                        result=result,
                    )

                except Exception as error:
                    should_continue = (
                        step.optional
                        or step.continue_on_error
                        or workflow.continue_on_error
                    )

                    if not should_continue:
                        stop_execution = True

            self._finalize_result(
                workflow=workflow,
                context=context,
                result=result,
            )

            self._status = (
                WorkflowEngineStatus.READY
            )

            self._last_error = None

            return result

        except Exception as error:
            self._last_error = str(error)

            self._status = (
                WorkflowEngineStatus.ERROR
            )

            self._add_context_error(
                context=context,
                message=str(error),
                step_id=None,
            )
            self._publish_event(
                event_type=(
                    WorkflowEventType
                    .WORKFLOW_FAILED
                    .value
                ),
                context=context,
                data={
                    "status": "failed",
                    "error": str(error),
                },
            )
            result.fail(
                error=str(error),
                context=self._context_snapshot(
                    context
                ),
            )

            self._failed_executions += 1

            raise

    # ============================================================
    # Ejecución de pasos
    # ============================================================

    def _execute_step(
        self,
        workflow: WorkflowDefinition,
        step: WorkflowStep,
        context: WorkflowContext,
        result: WorkflowResult,
    ) -> None:
        """
        Ejecuta un paso individual.
        """

        step_started = perf_counter()

        self._mark_step_ready(step)
        self._mark_step_running(step)
        self._publish_event(
            event_type=(
                WorkflowEventType
                .STEP_STARTED
                .value
            ),
            context=context,
            step_id=step.step_id,
            data={
                "step_name": step.name,
                "department_id": (
                    step.department_id
                ),
                "step_type": (
                    step.step_type.value
                ),
                "status": "running",
            },
        )
        self._add_history(
            context,
            event_type="step-started",
            data={
                "step_id": step.step_id,
                "department_id": (
                    step.department_id
                ),
                "step_type": (
                    step.step_type.value
                ),
            },
        )

        try:
            if (
                step.step_type
                != WorkflowStepType.DEPARTMENT
            ):
                raise NotImplementedError(
                    "WorkflowEngine actualmente "
                    "soporta pasos de tipo "
                    "'department'."
                )

            if not step.department_id:
                raise ValueError(
                    f"El paso '{step.step_id}' "
                    "no tiene department_id."
                )

            step_input = (
                self._build_step_input(
                    step=step,
                    context=context,
                )
            )

            preferred_agent_ids: List[str] = []

            if step.preferred_agent_id:
                preferred_agent_ids.append(
                    step.preferred_agent_id
                )

            execution_metadata = {
                "workflow_execution": True,
                "workflow_id": (
                    workflow.workflow_id
                ),
                "execution_id": (
                    context.execution_id
                ),
                "workflow_step_id": (
                    step.step_id
                ),
                "workflow_step_name": (
                    step.name
                ),
                **dict(step.metadata or {}),
            }

            runtime_result = (
                self.department_runtime.execute(
                    department_id=(
                        step.department_id
                    ),
                    task=step_input,
                    required_capabilities=list(
                        step.required_capabilities
                    ),
                    required_tools=list(
                        step.required_tools
                    ),
                    required_permissions=list(
                        step.required_permissions
                    ),
                    preferred_agent_ids=(
                        preferred_agent_ids
                    ),
                    excluded_agent_ids=[],
                    strategy=(
                        SelectionStrategy.BALANCED
                    ),
                    metadata=execution_metadata,
                )
            )

            duration_seconds = round(
                perf_counter() - step_started,
                6,
            )

            runtime_status = str(
                runtime_result.get(
                    "status",
                    "completed",
                )
            ).strip().lower()

            if runtime_status in {
                "failed",
                "error",
                "cancelled",
                "canceled",
            }:
                raise RuntimeError(
                    "DepartmentRuntime devolvió "
                    f"estado '{runtime_status}'."
                )
            agent_id = (
                runtime_result.get("agent_id")
                or runtime_result.get(
                    "selected_agent_id"
                )
                or runtime_result.get(
                    "assigned_agent_id"
                )
            )

            if not agent_id:
                agent_data = runtime_result.get(
                    "agent",
                    {},
                )

                if isinstance(agent_data, dict):
                    agent_id = (
                        agent_data.get("agent_id")
                        or agent_data.get("id")
                        or agent_data.get("name")
                    )
            self._mark_step_completed(
                step=step,
                execution_result=runtime_result,
                duration_seconds=duration_seconds,
            )

            self._record_step_result(
                context=context,
                step_id=step.step_id,
                step_result=runtime_result,
            )

            result.add_completed_step(
                step_id=step.step_id,
                result=runtime_result,
                duration_seconds=(
                    duration_seconds
                ),
            )
            self._publish_event(
                event_type=(
                    WorkflowEventType
                    .STEP_COMPLETED
                    .value
                ),
                context=context,
                step_id=step.step_id,
                data={
                    "step_name": step.name,

                    "department_id": (
                        step.department_id
                    ),
                    "agent_id": agent_id,

                    "status": "completed",

                    "duration_seconds": (
                        duration_seconds
                    ),

                    "result": (
                        self._compact_step_result(
                            runtime_result
                        )
                    ),
                },
            )
            self._add_history(
                context,
                event_type="step-completed",
                data={
                    "step_id": step.step_id,
                    "department_id": (
                        step.department_id
                    ),
                    "duration_seconds": (
                        duration_seconds
                    ),
                    "status": runtime_status,
                },
            )

        except Exception as error:
            duration_seconds = round(
                perf_counter() - step_started,
                6,
            )

            self._mark_step_failed(
                step=step,
                error=str(error),
                duration_seconds=duration_seconds,
            )

            self._add_context_error(
                context=context,
                message=str(error),
                step_id=step.step_id,
            )

            result.add_failed_step(
                step_id=step.step_id,
                error=str(error),
                duration_seconds=(
                    duration_seconds
                ),
            )
            self._publish_event(
                event_type=(
                    WorkflowEventType
                    .STEP_FAILED
                    .value
                ),
                context=context,
                step_id=step.step_id,
                data={
                    "step_name": step.name,
                    "department_id": (
                        step.department_id
                    ),
                    "status": "failed",
                    "error": str(error),
                    "duration_seconds": (
                        duration_seconds
                    ),
                },
            )
            self._add_history(
                context,
                event_type="step-failed",
                data={
                    "step_id": step.step_id,
                    "department_id": (
                        step.department_id
                    ),
                    "error": str(error),
                    "duration_seconds": (
                        duration_seconds
                    ),
                },
            )

            raise

    # ============================================================
    # Dependencias
    # ============================================================

    def _dependency_problem(
        self,
        step: WorkflowStep,
        workflow: WorkflowDefinition,
    ) -> Optional[str]:
        """
        Devuelve el motivo del bloqueo o None.
        """

        if not step.depends_on:
            return None

        for dependency_id in step.depends_on:
            dependency = workflow.require_step(
                dependency_id
            )

            if (
                dependency.status
                == WorkflowStepStatus.COMPLETED
            ):
                continue

            if (
                dependency.status
                == WorkflowStepStatus.SKIPPED
                and dependency.optional
            ):
                continue

            return (
                f"La dependencia "
                f"'{dependency_id}' terminó con "
                f"estado "
                f"'{dependency.status.value}'."
            )

        return None

    def _skip_step(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
        result: WorkflowResult,
        reason: str,
    ) -> None:
        """
        Marca un paso como omitido.
        """

        self._mark_step_skipped(
            step=step,
            reason=reason,
        )

        result.add_skipped_step(
            step_id=step.step_id,
            reason=reason,
        )

    def _block_step(
            self,
            step: WorkflowStep,
            context: WorkflowContext,
            result: WorkflowResult,
            reason: str,
    ) -> None:
        """
        Marca un paso como bloqueado.
        """

        self._mark_step_blocked(
            step=step,
            reason=reason,
        )

        result.add_blocked_step(
            step_id=step.step_id,
            reason=reason,
        )

        self._publish_event(
            event_type=(
                WorkflowEventType.STEP_BLOCKED.value
            ),
            context=context,
            step_id=step.step_id,
            data={
                "step_name": step.name,
                "department_id": step.department_id,
                "status": "blocked",
                "reason": reason,
            },
        )

        self._add_history(
            context,
            event_type="step-blocked",
            data={
                "step_id": step.step_id,
                "department_id": step.department_id,
                "reason": reason,
            },
        )
    # ============================================================
    # Finalización
    # ============================================================

    def _finalize_result(
        self,
        workflow: WorkflowDefinition,
        context: WorkflowContext,
        result: WorkflowResult,
    ) -> None:
        """
        Determina el estado final.
        """

        final_output = self._build_final_output(
            workflow=workflow,
            context=context,
            result=result,
        )

        context_snapshot = (
            self._context_snapshot(context)
        )

        required_failed = [
            step
            for step in workflow.steps
            if (
                not step.optional
                and step.status
                == WorkflowStepStatus.FAILED
            )
        ]

        required_blocked = [
            step
            for step in workflow.steps
            if (
                not step.optional
                and step.status
                == WorkflowStepStatus.BLOCKED
            )
        ]

        if required_failed:
            result.fail(
                error=(
                    "El workflow contiene pasos "
                    "obligatorios fallidos: "
                    + ", ".join(
                        step.step_id
                        for step
                        in required_failed
                    )
                ),
                final_output=final_output,
                context=context_snapshot,
            )

            self._failed_executions += 1

        elif required_blocked:
            result.complete_partial(
                final_output=final_output,
                context=context_snapshot,
            )

            self._partial_executions += 1

        elif (
            result.failed_count > 0
            or result.blocked_count > 0
            or result.skipped_count > 0
        ):
            result.complete_partial(
                final_output=final_output,
                context=context_snapshot,
            )

            self._partial_executions += 1

        else:
            result.complete(
                final_output=final_output,
                context=context_snapshot,
            )

            self._successful_executions += 1

        self._add_history(
            context,
            event_type="workflow-finished",
            data={
                "workflow_id": (
                    workflow.workflow_id
                ),
                "execution_id": (
                    result.execution_id
                ),
                "status": (
                    result.status.value
                ),
                "completed_count": (
                    result.completed_count
                ),
                "failed_count": (
                    result.failed_count
                ),
                "skipped_count": (
                    result.skipped_count
                ),
                "blocked_count": (
                    result.blocked_count
                ),
            },
        )
        self._publish_event(
            event_type=(
                WorkflowEventType
                .WORKFLOW_FINISHED
                .value
            ),
            context=context,
            data={
                "status": (
                    result.status.value
                ),
                "completed_count": (
                    result.completed_count
                ),
                "failed_count": (
                    result.failed_count
                ),
                "skipped_count": (
                    result.skipped_count
                ),
                "blocked_count": (
                    result.blocked_count
                ),
                "final_output": (
                    result.final_output
                ),
            },
        )

    def _build_final_output(
            self,
            workflow: WorkflowDefinition,
            context: WorkflowContext,
            result: WorkflowResult,
    ) -> Dict[str, Any]:
        """
        Consolida una salida final compacta.

        Los resultados completos continúan disponibles en el
        snapshot del contexto, pero no se duplican dentro de
        final_output.
        """

        terminal_outputs: Dict[
            str,
            Dict[str, Any],
        ] = {}

        for step in workflow.terminal_steps:
            step_result = self._get_step_result(
                context=context,
                step_id=step.step_id,
            )

            if step_result is None:
                continue

            terminal_outputs[
                step.step_id
            ] = self._compact_step_result(
                step_result
            )

        completed_steps: Dict[
            str,
            Dict[str, Any],
        ] = {}

        for step_id, step_result in (
                getattr(
                    context,
                    "step_results",
                    {},
                ).items()
        ):
            completed_steps[
                step_id
            ] = self._compact_step_result(
                step_result
            )

        primary_output = None

        if terminal_outputs:
            last_terminal_id = next(
                reversed(
                    terminal_outputs
                )
            )

            primary_output = (
                terminal_outputs[
                    last_terminal_id
                ].get("output")
            )

        return {
            "workflow_id": (
                workflow.workflow_id
            ),
            "workflow_name": workflow.name,
            "execution_id": (
                result.execution_id
            ),
            "request": result.request,
            "status": self._calculate_final_status(
                workflow=workflow,
                result=result,
            ),
            "output": primary_output,
            "terminal_outputs": (
                terminal_outputs
            ),
            "completed_steps": (
                completed_steps
            ),
        }

    @staticmethod
    def _calculate_final_status(
        workflow: WorkflowDefinition,
        result: WorkflowResult,
    ) -> str:
        """
        Calcula anticipadamente el estado final del workflow.
        """

        required_failed = any(
            not step.optional
            and step.status
            == WorkflowStepStatus.FAILED
            for step in workflow.steps
        )

        if required_failed:
            return "failed"

        required_blocked = any(
            not step.optional
            and step.status
            == WorkflowStepStatus.BLOCKED
            for step in workflow.steps
        )

        if required_blocked:
            return "partial"

        if (
            result.failed_count > 0
            or result.blocked_count > 0
            or result.skipped_count > 0
        ):
            return "partial"

        return "completed"
    # ============================================================
    # Consultas
    # ============================================================

    def get_execution(
        self,
        execution_id: str,
    ) -> WorkflowResult:
        """
        Obtiene una ejecución.
        """

        normalized_execution_id = str(
            execution_id
        ).strip()

        if (
            normalized_execution_id
            not in self._executions
        ):
            raise KeyError(
                f"La ejecución "
                f"'{normalized_execution_id}' "
                "no está registrada."
            )

        return self._executions[
            normalized_execution_id
        ]

    def get_execution_data(
        self,
        execution_id: str,
    ) -> Dict[str, Any]:
        """
        Obtiene una ejecución serializada.
        """

        return self.get_execution(
            execution_id
        ).to_dict()

    def list_executions(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Lista ejecuciones recientes.
        """

        executions = sorted(
            self._executions.values(),
            key=lambda item: (
                item.started_at
            ),
            reverse=True,
        )

        if limit is not None:
            if limit < 1:
                return []

            executions = executions[:limit]

        return [
            execution.to_dict()
            for execution in executions
        ]

    def summary(self) -> Dict[str, Any]:
        """
        Resumen operativo del motor.
        """

        return {
            "status": self._status.value,
            "is_ready": self.is_ready,
            "created_at": self._created_at,
            "started_at": self._started_at,
            "stopped_at": self._stopped_at,
            "last_error": self._last_error,
            "execution_count": (
                self._execution_count
            ),
            "active_executions": (
                self.active_execution_count
            ),
            "successful_executions": (
                self._successful_executions
            ),
            "partial_executions": (
                self._partial_executions
            ),
            "failed_executions": (
                self._failed_executions
            ),
            "registered_workflows": (
                self.workflow_registry.count
            ),
            "event_bus": (
                self.event_bus.summary()
            ),
        }

    # ============================================================
    # Compatibilidad con WorkflowContext
    # ============================================================

    @staticmethod
    def _build_step_input(
        step: WorkflowStep,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """
        Construye la entrada estructurada que recibirá el paso.

        Mantiene el contexto como diccionario y evita convertirlo
        en una cadena de texto extensa.
        """

        if hasattr(
            context,
            "build_step_input",
        ):
            try:
                value = context.build_step_input(
                    step=step,
                )

                if isinstance(value, dict):
                    return value

            except TypeError:
                try:
                    value = context.build_step_input(
                        step_id=step.step_id,
                        input_template=(
                            step.input_template
                        ),
                    )

                    if isinstance(value, dict):
                        return value

                except TypeError:
                    pass

        previous_results: Dict[
            str,
            Dict[str, Any],
        ] = {}

        for dependency_id in (
            step.depends_on or []
        ):
            dependency_result = (
                WorkflowEngine
                ._get_step_result(
                    context=context,
                    step_id=dependency_id,
                )
            )

            if dependency_result is None:
                continue

            previous_results[
                dependency_id
            ] = (
                WorkflowEngine
                ._compact_step_result(
                    dependency_result
                )
            )

        return {
            "execution_id": (
                context.execution_id
            ),
            "workflow_id": (
                context.workflow_id
            ),
            "step_id": step.step_id,
            "request": context.request,
            "prompt": (
                str(step.input_template).strip()
                if step.input_template
                else None
            ),
            "variables": dict(
                getattr(
                    context,
                    "variables",
                    {},
                )
            ),
            "previous_results": (
                previous_results
            ),
            "metadata": dict(
                getattr(
                    context,
                    "metadata",
                    {},
                )
            ),
        }

    @staticmethod
    def _compact_step_result(
        result: Any,
    ) -> Dict[str, Any]:
        """
        Devuelve solamente la información útil de un paso.

        Evita transmitir departamentos, métricas, permisos,
        perfiles completos de agentes y otros datos internos.
        """

        if not isinstance(
            result,
            dict,
        ):
            return {
                "status": "unknown",
                "output": result,
            }

        execution = result.get(
            "execution",
            {},
        )

        if not isinstance(
            execution,
            dict,
        ):
            execution = {}

        selected_agent = result.get(
            "selected_agent",
            {},
        )

        if not isinstance(
            selected_agent,
            dict,
        ):
            selected_agent = {}

        compact = {
            "status": result.get(
                "status",
                execution.get(
                    "status",
                    "unknown",
                ),
            ),
            "output": execution.get(
                "output",
                result.get("output"),
            ),
            "agent_id": (
                selected_agent.get(
                    "agent_id"
                )
                or execution.get(
                    "agent"
                )
            ),
            "duration_seconds": (
                execution.get(
                    "duration_seconds"
                )
                or result.get(
                    "duration_seconds"
                )
            ),
        }

        return {
            key: value
            for key, value
            in compact.items()
            if value is not None
        }


    @staticmethod
    def _record_step_result(
        context: WorkflowContext,
        step_id: str,
        step_result: Dict[str, Any],
    ) -> None:
        if hasattr(
            context,
            "record_step_result",
        ):
            try:
                context.record_step_result(
                    step_id,
                    step_result,
                )
                return
            except TypeError:
                context.record_step_result(
                    step_id=step_id,
                    result=step_result,
                )
                return

        context.step_results[
            step_id
        ] = step_result

    @staticmethod
    def _get_step_result(
        context: WorkflowContext,
        step_id: str,
    ) -> Any:
        if hasattr(
            context,
            "get_step_result",
        ):
            return context.get_step_result(
                step_id
            )

        return getattr(
            context,
            "step_results",
            {},
        ).get(step_id)

    @staticmethod
    def _context_snapshot(
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        if hasattr(context, "snapshot"):
            return context.snapshot()

        if hasattr(context, "to_dict"):
            return context.to_dict()

        return {
            "workflow_id": context.workflow_id,
            "execution_id": (
                context.execution_id
            ),
            "request": context.request,
            "variables": dict(
                getattr(
                    context,
                    "variables",
                    {},
                )
            ),
            "step_results": dict(
                getattr(
                    context,
                    "step_results",
                    {},
                )
            ),
        }

    @staticmethod
    def _add_history(
        context: WorkflowContext,
        event_type: str,
        data: Dict[str, Any],
    ) -> None:
        if hasattr(
            context,
            "add_history_event",
        ):
            try:
                context.add_history_event(
                    event_type,
                    data,
                )
                return
            except TypeError:
                context.add_history_event(
                    event_type=event_type,
                    data=data,
                )
                return

        if hasattr(context, "history"):
            context.history.append(
                {
                    "event_type": event_type,
                    "data": dict(data),
                    "created_at": (
                        datetime.now()
                        .isoformat()
                    ),
                }
            )

    @staticmethod
    def _add_context_error(
        context: WorkflowContext,
        message: str,
        step_id: Optional[str],
    ) -> None:
        if hasattr(context, "add_error"):
            try:
                context.add_error(
                    message=message,
                    step_id=step_id,
                )
                return
            except TypeError:
                try:
                    context.add_error(
                        message,
                        step_id,
                    )
                    return
                except TypeError:
                    context.add_error(message)
                    return

    # ============================================================
    # Compatibilidad con WorkflowStep
    # ============================================================

    @staticmethod
    def _mark_step_ready(
        step: WorkflowStep,
    ) -> None:
        if hasattr(step, "mark_ready"):
            step.mark_ready()
        else:
            step.status = (
                WorkflowStepStatus.READY
            )

    @staticmethod
    def _mark_step_running(
        step: WorkflowStep,
    ) -> None:
        if hasattr(step, "mark_running"):
            step.mark_running()
        else:
            step.status = (
                WorkflowStepStatus.RUNNING
            )

    @staticmethod
    def _mark_step_completed(
        step: WorkflowStep,
        execution_result: Dict[str, Any],
        duration_seconds: float,
    ) -> None:
        if hasattr(step, "mark_completed"):
            try:
                step.mark_completed(
                    result=execution_result,
                    duration_seconds=(
                        duration_seconds
                    ),
                )
                return
            except TypeError:
                try:
                    step.mark_completed(
                        execution_result
                    )
                    return
                except TypeError:
                    step.mark_completed()
                    return

        step.status = (
            WorkflowStepStatus.COMPLETED
        )

    @staticmethod
    def _mark_step_failed(
        step: WorkflowStep,
        error: str,
        duration_seconds: float,
    ) -> None:
        if hasattr(step, "mark_failed"):
            try:
                step.mark_failed(
                    error=error,
                    duration_seconds=(
                        duration_seconds
                    ),
                )
                return
            except TypeError:
                try:
                    step.mark_failed(error)
                    return
                except TypeError:
                    step.mark_failed()
                    return

        step.status = WorkflowStepStatus.FAILED

    @staticmethod
    def _mark_step_skipped(
        step: WorkflowStep,
        reason: str,
    ) -> None:
        if hasattr(step, "mark_skipped"):
            try:
                step.mark_skipped(reason=reason)
                return
            except TypeError:
                try:
                    step.mark_skipped(reason)
                    return
                except TypeError:
                    step.mark_skipped()
                    return

        step.status = (
            WorkflowStepStatus.SKIPPED
        )

    @staticmethod
    def _mark_step_blocked(
        step: WorkflowStep,
        reason: str,
    ) -> None:
        if hasattr(step, "mark_blocked"):
            try:
                step.mark_blocked(reason=reason)
                return
            except TypeError:
                try:
                    step.mark_blocked(reason)
                    return
                except TypeError:
                    step.mark_blocked()
                    return

        step.status = (
            WorkflowStepStatus.BLOCKED
        )

    # ============================================================
    # Eventos en tiempo real
    # ============================================================

    def _publish_event(
            self,
            event_type: str,
            context: WorkflowContext,
            step_id: Optional[str] = None,
            data: Optional[
                Dict[str, Any]
            ] = None,
    ) -> None:
        """
        Publica un evento de workflow sin afectar la ejecución.

        Cualquier error interno del EventBus queda aislado para que
        un visualizador o listener nunca interrumpa el workflow.
        """

        try:
            self.event_bus.publish(
                event_type=event_type,
                execution_id=(
                    context.execution_id
                ),
                workflow_id=(
                    context.workflow_id
                ),
                step_id=step_id,
                data=dict(data or {}),
            )

        except Exception as error:
            self._last_error = (
                "WorkflowEventBus: "
                f"{error}"
            )

    # ============================================================
    # Utilidades internas
    # ============================================================

    def _ensure_ready(self) -> None:
        if not self.is_ready:
            raise RuntimeError(
                "WorkflowEngine no está iniciado. "
                "Ejecute start() antes de utilizarlo."
            )

        if not self.department_runtime.is_ready:
            raise RuntimeError(
                "DepartmentRuntime no está listo."
            )

    def __repr__(self) -> str:
        return (
            "WorkflowEngine("
            f"status='{self._status.value}', "
            f"executions={self._execution_count}, "
            f"workflows="
            f"{self.workflow_registry.count}"
            ")"
        )