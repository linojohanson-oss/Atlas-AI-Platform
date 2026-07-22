"""
Atlas AI Platform - Workflow Observability Test

Prueba integral de:

- WorkflowEngine
- WorkflowEventBus
- WorkflowExecutionState
- ExecutionTimeline
- PerformanceProfiler
- propagación de agent_id
"""

from __future__ import annotations
from pathlib import Path
import sys

PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )
from atlas.workflows import (
    ExecutionTimeline,
    PerformanceProfiler,
    WorkflowEngine,
    WorkflowEventBus,
    WorkflowExecutionState,
    WorkflowRegistry,
)

from tests.fake_department_runtime import (
    FakeDepartmentRuntime,
)

from tests.workflow_test_utils import (
    create_observability_workflow,
)

def main() -> None:
    """
    Ejecuta la prueba integral de observabilidad.
    """

    runtime = FakeDepartmentRuntime(
        delay_seconds=0.002,
    )

    registry = WorkflowRegistry()

    event_bus = WorkflowEventBus()

    execution_state = WorkflowExecutionState()
    timeline = ExecutionTimeline()
    profiler = PerformanceProfiler(
        slow_step_threshold_seconds=0.001,
    )

    event_bus.subscribe(
        execution_state.on_event
    )
    event_bus.subscribe(
        timeline.on_event
    )
    event_bus.subscribe(
        profiler.on_event
    )

    engine = WorkflowEngine(
        department_runtime=runtime,
        workflow_registry=registry,
        event_bus=event_bus,
    )

    engine.start()

    workflow = create_observability_workflow()

    result = engine.execute_definition(
        workflow=workflow,
        request=(
            "Analizar, corregir y revisar "
            "la seguridad de una API."
        ),
        variables={
            "environment": "test",
        },
        metadata={
            "source": (
                "test_workflow_observability"
            ),
        },
    )

    state_data = execution_state.snapshot()
    timeline_data = timeline.to_dict()
    profiler_data = profiler.to_dict()

    print("=" * 72)
    print("ATLAS AI - WORKFLOW OBSERVABILITY TEST")
    print("=" * 72)

    print("\nRESULTADO")
    print("-" * 72)
    print("Workflow ID :", result.workflow_id)
    print("Estado      :", result.status.value)

    print("\nRUNTIME")
    print("-" * 72)
    print(runtime.summary())

    print("\nEXECUTION STATE")
    print("-" * 72)
    print(state_data)

    print("\nTIMELINE")
    print("-" * 72)

    for event in timeline_data:
        print(
            event.get("timestamp"),
            "-",
            event.get("message"),
        )

    print("\nPERFORMANCE")
    print("-" * 72)
    print(profiler_data)

    print("\nVALIDACIONES")
    print("-" * 72)

    assert result.status.value == "completed"

    assert runtime.execution_count == 3

    assert timeline.events_count() == 8

    assert profiler_data.get(
        "completed_steps"
    ) == 3

    assert profiler_data.get(
        "failed_steps"
    ) == 0

    step_metrics = profiler_data.get(
        "steps",
        [],
    )

    assert len(step_metrics) == 3

    agent_ids = {
        item.get("agent_id")
        for item in step_metrics
    }

    expected_agent_ids = {
        "security-agent",
        "engineering-agent",
        "operations-agent",
    }

    assert agent_ids == expected_agent_ids

    assert "unassigned" not in (
        profiler_data.get(
            "duration_by_agent_seconds",
            {}
        )
    )

    print("OK - workflow completado")
    print("OK - 3 pasos ejecutados")
    print("OK - 8 eventos registrados")
    print("OK - agent_id propagado")
    print("OK - profiler agrupado por agente")
    print("OK - observabilidad integral validada")

    engine.stop()

    print("\n" + "=" * 72)
    print("TEST COMPLETADO CORRECTAMENTE")
    print("=" * 72)


if __name__ == "__main__":
    main()