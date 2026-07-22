"""
Atlas AI Platform - Workflow Test Utilities

Funciones reutilizables para construir workflows de prueba.
"""

from __future__ import annotations

from atlas.workflows.workflow_definition import (
    WorkflowDefinition,
    WorkflowExecutionStrategy,
)
from atlas.workflows.workflow_step import (
    WorkflowStep,
    WorkflowStepType,
)


def create_observability_workflow(
) -> WorkflowDefinition:
    """
    Crea un workflow secuencial de tres pasos para probar
    EventBus, Timeline, State y PerformanceProfiler.
    """

    steps = [
        WorkflowStep(
            step_id="security-analysis",
            name="Security Analysis",
            step_type=(
                WorkflowStepType.DEPARTMENT
            ),
            department_id="security",
            description=(
                "Analiza riesgos de seguridad."
            ),
        ),
        WorkflowStep(
            step_id="engineering-fix",
            name="Engineering Fix",
            step_type=(
                WorkflowStepType.DEPARTMENT
            ),
            department_id="engineering",
            description=(
                "Implementa las correcciones."
            ),
            depends_on=[
                "security-analysis",
            ],
        ),
        WorkflowStep(
            step_id="final-review",
            name="Final Review",
            step_type=(
                WorkflowStepType.DEPARTMENT
            ),
            department_id="operations",
            description=(
                "Realiza la revisión final."
            ),
            depends_on=[
                "engineering-fix",
            ],
        ),
    ]

    return WorkflowDefinition(
        workflow_id="security-api-review",
        name="Security API Review",
        description=(
            "Workflow de prueba para observabilidad."
        ),
        steps=steps,
        strategy=(
            WorkflowExecutionStrategy.DEPENDENCY
        ),
        continue_on_error=False,
        metadata={
            "environment": "test",
            "suite": "workflow-observability",
        },
    )