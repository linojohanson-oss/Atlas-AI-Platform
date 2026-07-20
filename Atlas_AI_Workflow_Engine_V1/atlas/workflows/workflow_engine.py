from datetime import datetime
from time import perf_counter
from typing import Any, Dict

from atlas.utils.logger import logger
from atlas.workflows.workflow_models import (
    WorkflowExecution,
    WorkflowStatus,
    WorkflowStepResult,
    WorkflowStepStatus,
)


class WorkflowEngine:
    """Ejecuta workflows multiagente con trazabilidad completa."""

    def __init__(
        self,
        agent_manager: Any,
        event_bus: Any,
        workflow_registry: Any,
        workflow_trace: Any,
    ) -> None:
        self.agent_manager = agent_manager
        self.event_bus = event_bus
        self.workflow_registry = workflow_registry
        self.workflow_trace = workflow_trace

    def execute(
        self,
        workflow_name: str,
        prompt: str,
    ) -> Dict[str, Any]:
        normalized_prompt = prompt.strip()

        if not normalized_prompt:
            raise ValueError("El prompt del workflow no puede estar vacío.")

        definition = self.workflow_registry.get(workflow_name)
        execution = WorkflowExecution(
            workflow_name=definition.name,
            prompt=normalized_prompt,
        )

        started_clock = perf_counter()
        execution.status = WorkflowStatus.RUNNING
        execution.started_at = datetime.now().isoformat()

        self.event_bus.publish(
            "workflow.started",
            {
                "workflow_id": execution.workflow_id,
                "workflow_name": definition.name,
                "prompt": normalized_prompt,
            },
        )

        previous_output: Any = None

        try:
            for step_definition in definition.steps:
                step = WorkflowStepResult(
                    name=step_definition.name,
                    agent_name=step_definition.agent_name,
                )
                execution.steps.append(step)

                step.status = WorkflowStepStatus.RUNNING
                step.started_at = datetime.now().isoformat()
                step_clock = perf_counter()

                step_input = self._build_step_input(
                    original_prompt=normalized_prompt,
                    instruction=step_definition.instruction,
                    previous_output=previous_output,
                )
                step.input_text = step_input

                self.event_bus.publish(
                    "workflow.step.started",
                    {
                        "workflow_id": execution.workflow_id,
                        "step": step.name,
                        "agent": step.agent_name,
                    },
                )

                try:
                    result = self.agent_manager.execute(
                        agent_name=step.agent_name,
                        task=step_input,
                    )

                    step.output = result
                    step.status = WorkflowStepStatus.COMPLETED
                    previous_output = result

                except Exception as error:
                    step.status = WorkflowStepStatus.FAILED
                    step.error = str(error)
                    raise

                finally:
                    step.finished_at = datetime.now().isoformat()
                    step.duration_ms = round(
                        (perf_counter() - step_clock) * 1000,
                        2,
                    )

                self.event_bus.publish(
                    "workflow.step.completed",
                    {
                        "workflow_id": execution.workflow_id,
                        "step": step.name,
                        "agent": step.agent_name,
                        "duration_ms": step.duration_ms,
                    },
                )

            execution.final_result = previous_output
            execution.confidence = self._calculate_confidence(execution)
            execution.review_status = (
                "APPROVED"
                if execution.confidence >= 70.0
                else "REVIEW_RECOMMENDED"
            )
            execution.status = WorkflowStatus.COMPLETED

        except Exception as error:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(error)
            execution.review_status = "FAILED"
            logger.exception(
                "Workflow '%s' falló: %s",
                workflow_name,
                error,
            )

        finally:
            execution.finished_at = datetime.now().isoformat()
            execution.duration_ms = round(
                (perf_counter() - started_clock) * 1000,
                2,
            )

            result = execution.to_dict()
            self.workflow_trace.save(result)

            self.event_bus.publish(
                "workflow.finished",
                result,
            )

        return result

    @staticmethod
    def _build_step_input(
        original_prompt: str,
        instruction: str,
        previous_output: Any,
    ) -> str:
        context = (
            "No existe un resultado anterior."
            if previous_output is None
            else str(previous_output)
        )

        return (
            f"OBJETIVO ORIGINAL:\n{original_prompt}\n\n"
            f"INSTRUCCIÓN DE ESTA ETAPA:\n{instruction}\n\n"
            f"RESULTADO DE LA ETAPA ANTERIOR:\n{context}\n\n"
            "Entregá una respuesta clara, estructurada y accionable."
        )

    @staticmethod
    def _calculate_confidence(
        execution: WorkflowExecution,
    ) -> float:
        if not execution.steps:
            return 0.0

        completed = sum(
            step.status == WorkflowStepStatus.COMPLETED
            for step in execution.steps
        )
        completion_ratio = completed / len(execution.steps)

        output_ratio = sum(
            bool(step.output)
            for step in execution.steps
        ) / len(execution.steps)

        confidence = (
            completion_ratio * 80.0
            + output_ratio * 20.0
        )

        return round(min(confidence, 100.0), 2)
