"""
Atlas AI Platform - Workflow Definition

Define la estructura completa de un workflow:

- Identidad y descripción.
- Pasos ejecutables.
- Dependencias.
- Estrategia general.
- Validación del grafo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Set

from atlas.workflows.workflow_step import (
    WorkflowStep,
)


class WorkflowExecutionStrategy(str, Enum):
    """
    Estrategias generales de ejecución.
    """

    SEQUENTIAL = "sequential"
    DEPENDENCY = "dependency"
    PARALLEL = "parallel"


@dataclass
class WorkflowDefinition:
    """
    Representa la definición completa de un workflow.
    """

    workflow_id: str
    name: str

    description: str = ""

    steps: List[WorkflowStep] = field(
        default_factory=list
    )

    strategy: WorkflowExecutionStrategy = (
        WorkflowExecutionStrategy.DEPENDENCY
    )

    version: str = "1.0.0"

    enabled: bool = True
    continue_on_error: bool = False

    tags: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    created_at: datetime = field(
        default_factory=datetime.now
    )

    updated_at: datetime = field(
        default_factory=datetime.now
    )

    def __post_init__(self) -> None:
        """
        Valida y normaliza la definición.
        """

        self.workflow_id = str(
            self.workflow_id
        ).strip()

        self.name = str(self.name).strip()

        self.description = str(
            self.description or ""
        ).strip()

        self.version = str(
            self.version or "1.0.0"
        ).strip()

        if not self.workflow_id:
            raise ValueError(
                "WorkflowDefinition requiere workflow_id."
            )

        if not self.name:
            raise ValueError(
                "WorkflowDefinition requiere name."
            )

        if isinstance(self.strategy, str):
            self.strategy = WorkflowExecutionStrategy(
                self.strategy
            )

        self.steps = list(self.steps or [])

        self.tags = self._normalize_string_list(
            self.tags
        )

        self.metadata = dict(
            self.metadata or {}
        )

        self._validate_steps()

    @property
    def step_count(self) -> int:
        """
        Cantidad total de pasos.
        """

        return len(self.steps)

    @property
    def enabled_steps(self) -> List[WorkflowStep]:
        """
        Devuelve los pasos habilitados.
        """

        return [
            step
            for step in self.steps
            if step.enabled
        ]

    @property
    def disabled_steps(self) -> List[WorkflowStep]:
        """
        Devuelve los pasos deshabilitados.
        """

        return [
            step
            for step in self.steps
            if not step.enabled
        ]

    @property
    def initial_steps(self) -> List[WorkflowStep]:
        """
        Devuelve los pasos sin dependencias.
        """

        return [
            step
            for step in self.enabled_steps
            if not step.depends_on
        ]

    @property
    def terminal_steps(self) -> List[WorkflowStep]:
        """
        Devuelve los pasos de los que ningún otro paso depende.
        """

        dependency_ids: Set[str] = set()

        for step in self.enabled_steps:
            dependency_ids.update(
                step.depends_on
            )

        return [
            step
            for step in self.enabled_steps
            if step.step_id not in dependency_ids
        ]

    def add_step(
        self,
        step: WorkflowStep,
    ) -> None:
        """
        Agrega un nuevo paso al workflow.
        """

        if not isinstance(step, WorkflowStep):
            raise TypeError(
                "step debe ser una instancia de WorkflowStep."
            )

        if self.has_step(step.step_id):
            raise ValueError(
                f"Ya existe el paso '{step.step_id}'."
            )

        self.steps.append(step)

        try:
            self._validate_steps()
        except Exception:
            self.steps.pop()
            raise

        self._touch()

    def add_steps(
        self,
        steps: Iterable[WorkflowStep],
    ) -> None:
        """
        Agrega varios pasos de forma segura.
        """

        original_steps = list(self.steps)

        try:
            for step in steps:
                if not isinstance(
                    step,
                    WorkflowStep,
                ):
                    raise TypeError(
                        "Todos los elementos deben ser "
                        "WorkflowStep."
                    )

                if self.has_step(step.step_id):
                    raise ValueError(
                        f"Ya existe el paso "
                        f"'{step.step_id}'."
                    )

                self.steps.append(step)

            self._validate_steps()
            self._touch()

        except Exception:
            self.steps = original_steps
            raise

    def remove_step(
        self,
        step_id: str,
        force: bool = False,
    ) -> WorkflowStep:
        """
        Elimina un paso.

        Si otros pasos dependen de él, requiere force=True.
        """

        normalized_step_id = str(
            step_id
        ).strip()

        step = self.get_step(
            normalized_step_id
        )

        if step is None:
            raise KeyError(
                f"No existe el paso "
                f"'{normalized_step_id}'."
            )

        dependents = self.get_dependents(
            normalized_step_id
        )

        if dependents and not force:
            dependent_ids = [
                dependent.step_id
                for dependent in dependents
            ]

            raise ValueError(
                f"No se puede eliminar "
                f"'{normalized_step_id}'. "
                f"Dependientes: {dependent_ids}"
            )

        self.steps = [
            current_step
            for current_step in self.steps
            if current_step.step_id
            != normalized_step_id
        ]

        if force:
            for current_step in self.steps:
                current_step.depends_on = [
                    dependency
                    for dependency
                    in current_step.depends_on
                    if dependency
                    != normalized_step_id
                ]

        self._validate_steps()
        self._touch()

        return step

    def get_step(
        self,
        step_id: str,
    ) -> Optional[WorkflowStep]:
        """
        Recupera un paso por identificador.
        """

        normalized_step_id = str(
            step_id
        ).strip()

        if not normalized_step_id:
            return None

        for step in self.steps:
            if step.step_id == normalized_step_id:
                return step

        return None

    def require_step(
        self,
        step_id: str,
    ) -> WorkflowStep:
        """
        Recupera un paso o lanza una excepción.
        """

        step = self.get_step(step_id)

        if step is None:
            raise KeyError(
                f"No existe el paso '{step_id}'."
            )

        return step

    def has_step(
        self,
        step_id: str,
    ) -> bool:
        """
        Indica si existe un paso.
        """

        return self.get_step(step_id) is not None

    def get_dependencies(
        self,
        step_id: str,
    ) -> List[WorkflowStep]:
        """
        Devuelve las dependencias directas de un paso.
        """

        step = self.require_step(step_id)

        return [
            self.require_step(dependency_id)
            for dependency_id
            in step.depends_on
        ]

    def get_dependents(
        self,
        step_id: str,
    ) -> List[WorkflowStep]:
        """
        Devuelve los pasos que dependen directamente
        del paso indicado.
        """

        normalized_step_id = str(
            step_id
        ).strip()

        return [
            step
            for step in self.steps
            if normalized_step_id
            in step.depends_on
        ]

    def execution_order(self) -> List[WorkflowStep]:
        """
        Devuelve un orden topológico válido.

        Lanza ValueError si existe una dependencia circular.
        """

        enabled_steps = self.enabled_steps

        step_map = {
            step.step_id: step
            for step in enabled_steps
        }

        in_degree: Dict[str, int] = {
            step.step_id: 0
            for step in enabled_steps
        }

        dependents_map: Dict[str, List[str]] = {
            step.step_id: []
            for step in enabled_steps
        }

        for step in enabled_steps:
            for dependency_id in step.depends_on:
                if dependency_id not in step_map:
                    continue

                in_degree[step.step_id] += 1

                dependents_map[
                    dependency_id
                ].append(step.step_id)

        available = [
            step
            for step in enabled_steps
            if in_degree[step.step_id] == 0
        ]

        available.sort(
            key=lambda item: (
                -item.priority,
                item.step_id,
            )
        )

        ordered: List[WorkflowStep] = []

        while available:
            current = available.pop(0)
            ordered.append(current)

            for dependent_id in dependents_map[
                current.step_id
            ]:
                in_degree[dependent_id] -= 1

                if in_degree[dependent_id] == 0:
                    available.append(
                        step_map[dependent_id]
                    )

                    available.sort(
                        key=lambda item: (
                            -item.priority,
                            item.step_id,
                        )
                    )

        if len(ordered) != len(enabled_steps):
            raise ValueError(
                "El workflow contiene una dependencia "
                "circular."
            )

        return ordered

    def reset_steps(self) -> None:
        """
        Restablece todos los pasos a pending.
        """

        for step in self.steps:
            step.reset()

        self._touch()

    def validate(self) -> None:
        """
        Ejecuta nuevamente todas las validaciones.
        """

        self._validate_steps()

    def clone(
        self,
        workflow_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> "WorkflowDefinition":
        """
        Crea una copia independiente del workflow.
        """

        cloned_steps = [
            WorkflowStep(
                step_id=step.step_id,
                name=step.name,
                step_type=step.step_type,
                description=step.description,
                department_id=step.department_id,
                preferred_agent_id=(
                    step.preferred_agent_id
                ),
                required_capabilities=list(
                    step.required_capabilities
                ),
                required_tools=list(
                    step.required_tools
                ),
                required_permissions=list(
                    step.required_permissions
                ),
                depends_on=list(
                    step.depends_on
                ),
                continue_on_error=(
                    step.continue_on_error
                ),
                optional=step.optional,
                enabled=step.enabled,
                priority=step.priority,
                input_template=(
                    step.input_template
                ),
                metadata=dict(step.metadata),
                status=step.status,
            )
            for step in self.steps
        ]

        return WorkflowDefinition(
            workflow_id=(
                str(workflow_id).strip()
                if workflow_id is not None
                else self.workflow_id
            ),
            name=(
                str(name).strip()
                if name is not None
                else self.name
            ),
            description=self.description,
            steps=cloned_steps,
            strategy=self.strategy,
            version=self.version,
            enabled=self.enabled,
            continue_on_error=(
                self.continue_on_error
            ),
            tags=list(self.tags),
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializa la definición.
        """

        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "strategy": self.strategy.value,
            "version": self.version,
            "enabled": self.enabled,
            "continue_on_error": (
                self.continue_on_error
            ),
            "step_count": self.step_count,
            "steps": [
                step.to_dict()
                for step in self.steps
            ],
            "initial_step_ids": [
                step.step_id
                for step in self.initial_steps
            ],
            "terminal_step_ids": [
                step.step_id
                for step in self.terminal_steps
            ],
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
            "created_at": (
                self.created_at.isoformat()
            ),
            "updated_at": (
                self.updated_at.isoformat()
            ),
        }

    def _validate_steps(self) -> None:
        """
        Valida identificadores, dependencias y ciclos.
        """

        step_ids: List[str] = []

        for step in self.steps:
            if not isinstance(
                step,
                WorkflowStep,
            ):
                raise TypeError(
                    "Todos los pasos deben ser "
                    "instancias de WorkflowStep."
                )

            if step.step_id in step_ids:
                raise ValueError(
                    f"step_id duplicado: "
                    f"'{step.step_id}'."
                )

            step_ids.append(step.step_id)

        valid_step_ids = set(step_ids)

        for step in self.steps:
            missing_dependencies = [
                dependency_id
                for dependency_id
                in step.depends_on
                if dependency_id
                not in valid_step_ids
            ]

            if missing_dependencies:
                raise ValueError(
                    f"El paso '{step.step_id}' "
                    "tiene dependencias inexistentes: "
                    f"{missing_dependencies}"
                )

        self.execution_order()

    @staticmethod
    def _normalize_string_list(
        values: Optional[List[str]],
    ) -> List[str]:
        """
        Normaliza una lista de textos.
        """

        normalized: List[str] = []

        for value in values or []:
            item = str(value).strip()

            if item and item not in normalized:
                normalized.append(item)

        return normalized

    def _touch(self) -> None:
        """
        Actualiza la fecha de modificación.
        """

        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        return (
            "WorkflowDefinition("
            f"workflow_id='{self.workflow_id}', "
            f"name='{self.name}', "
            f"steps={self.step_count}, "
            f"strategy='{self.strategy.value}', "
            f"enabled={self.enabled}"
            ")"
        )