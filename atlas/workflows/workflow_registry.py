"""
Atlas AI Platform - Workflow Registry

Registro central de definiciones de workflows.

Permite:

- Registrar workflows.
- Reemplazar definiciones existentes.
- Consultar workflows por identificador.
- Listar y filtrar workflows.
- Habilitar o deshabilitar workflows.
- Eliminar definiciones.
- Obtener estadísticas del registro.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from atlas.workflows.workflow_definition import (
    WorkflowDefinition,
)


class WorkflowRegistry:
    """
    Registro central de workflows de Atlas AI.
    """

    def __init__(self) -> None:
        self._workflows: Dict[
            str,
            WorkflowDefinition,
        ] = {}

        self._created_at = datetime.now()
        self._updated_at = datetime.now()

        self._registration_count = 0
        self._replacement_count = 0
        self._removal_count = 0

    @property
    def count(self) -> int:
        """
        Cantidad total de workflows registrados.
        """

        return len(self._workflows)

    @property
    def enabled_count(self) -> int:
        """
        Cantidad de workflows habilitados.
        """

        return sum(
            1
            for workflow in self._workflows.values()
            if workflow.enabled
        )

    @property
    def disabled_count(self) -> int:
        """
        Cantidad de workflows deshabilitados.
        """

        return self.count - self.enabled_count

    @property
    def workflow_ids(self) -> List[str]:
        """
        Identificadores registrados.
        """

        return sorted(self._workflows.keys())

    def register(
        self,
        workflow: WorkflowDefinition,
        replace: bool = False,
    ) -> WorkflowDefinition:
        """
        Registra una definición.

        Si ya existe y replace=False, lanza ValueError.
        """

        self._validate_workflow(workflow)

        workflow_id = workflow.workflow_id

        if (
            workflow_id in self._workflows
            and not replace
        ):
            raise ValueError(
                f"El workflow '{workflow_id}' "
                "ya está registrado."
            )

        stored_workflow = workflow.clone()

        if workflow_id in self._workflows:
            self._replacement_count += 1
        else:
            self._registration_count += 1

        self._workflows[workflow_id] = (
            stored_workflow
        )

        self._touch()

        return stored_workflow.clone()

    def register_many(
        self,
        workflows: Iterable[
            WorkflowDefinition
        ],
        replace: bool = False,
    ) -> List[WorkflowDefinition]:
        """
        Registra múltiples workflows de forma atómica.

        Si alguno falla, se restaura el estado anterior.
        """

        original_workflows = {
            workflow_id: workflow.clone()
            for workflow_id, workflow
            in self._workflows.items()
        }

        original_registration_count = (
            self._registration_count
        )
        original_replacement_count = (
            self._replacement_count
        )
        original_updated_at = self._updated_at

        registered: List[
            WorkflowDefinition
        ] = []

        try:
            for workflow in workflows:
                registered.append(
                    self.register(
                        workflow=workflow,
                        replace=replace,
                    )
                )

            return registered

        except Exception:
            self._workflows = original_workflows
            self._registration_count = (
                original_registration_count
            )
            self._replacement_count = (
                original_replacement_count
            )
            self._updated_at = original_updated_at
            raise

    def get(
        self,
        workflow_id: str,
        clone: bool = True,
    ) -> Optional[WorkflowDefinition]:
        """
        Recupera un workflow.

        Por defecto devuelve una copia independiente.
        """

        normalized_workflow_id = (
            self._normalize_workflow_id(
                workflow_id
            )
        )

        if not normalized_workflow_id:
            return None

        workflow = self._workflows.get(
            normalized_workflow_id
        )

        if workflow is None:
            return None

        if clone:
            return workflow.clone()

        return workflow

    def require(
        self,
        workflow_id: str,
        enabled_only: bool = False,
        clone: bool = True,
    ) -> WorkflowDefinition:
        """
        Recupera un workflow o lanza KeyError.

        enabled_only=True exige además que esté habilitado.
        """

        workflow = self.get(
            workflow_id=workflow_id,
            clone=clone,
        )

        if workflow is None:
            raise KeyError(
                f"No existe el workflow "
                f"'{workflow_id}'."
            )

        if enabled_only and not workflow.enabled:
            raise RuntimeError(
                f"El workflow '{workflow.workflow_id}' "
                "está deshabilitado."
            )

        return workflow

    def exists(
        self,
        workflow_id: str,
    ) -> bool:
        """
        Indica si un workflow está registrado.
        """

        normalized_workflow_id = (
            self._normalize_workflow_id(
                workflow_id
            )
        )

        return bool(
            normalized_workflow_id
            and normalized_workflow_id
            in self._workflows
        )

    def remove(
        self,
        workflow_id: str,
    ) -> WorkflowDefinition:
        """
        Elimina un workflow y devuelve una copia.
        """

        normalized_workflow_id = (
            self._normalize_workflow_id(
                workflow_id
            )
        )

        if (
            not normalized_workflow_id
            or normalized_workflow_id
            not in self._workflows
        ):
            raise KeyError(
                f"No existe el workflow "
                f"'{workflow_id}'."
            )

        removed = self._workflows.pop(
            normalized_workflow_id
        )

        self._removal_count += 1
        self._touch()

        return removed.clone()

    def clear(self) -> None:
        """
        Elimina todos los workflows.
        """

        removed_count = len(
            self._workflows
        )

        self._workflows.clear()
        self._removal_count += removed_count
        self._touch()

    def enable(
        self,
        workflow_id: str,
    ) -> WorkflowDefinition:
        """
        Habilita un workflow.
        """

        workflow = self.require(
            workflow_id=workflow_id,
            clone=False,
        )

        workflow.enabled = True
        workflow.updated_at = datetime.now()

        self._touch()

        return workflow.clone()

    def disable(
        self,
        workflow_id: str,
    ) -> WorkflowDefinition:
        """
        Deshabilita un workflow.
        """

        workflow = self.require(
            workflow_id=workflow_id,
            clone=False,
        )

        workflow.enabled = False
        workflow.updated_at = datetime.now()

        self._touch()

        return workflow.clone()

    def replace(
        self,
        workflow: WorkflowDefinition,
    ) -> WorkflowDefinition:
        """
        Reemplaza obligatoriamente una definición existente.
        """

        self._validate_workflow(workflow)

        if not self.exists(
            workflow.workflow_id
        ):
            raise KeyError(
                f"No existe el workflow "
                f"'{workflow.workflow_id}'."
            )

        return self.register(
            workflow=workflow,
            replace=True,
        )

    def list(
        self,
        enabled_only: bool = False,
        tag: Optional[str] = None,
        strategy: Optional[str] = None,
        clone: bool = True,
    ) -> List[WorkflowDefinition]:
        """
        Lista workflows con filtros opcionales.
        """

        normalized_tag = (
            str(tag).strip()
            if tag is not None
            else None
        )

        normalized_strategy = (
            str(strategy).strip().lower()
            if strategy is not None
            else None
        )

        workflows: List[
            WorkflowDefinition
        ] = []

        for workflow in self._workflows.values():
            if (
                enabled_only
                and not workflow.enabled
            ):
                continue

            if (
                normalized_tag
                and normalized_tag
                not in workflow.tags
            ):
                continue

            if (
                normalized_strategy
                and workflow.strategy.value
                != normalized_strategy
            ):
                continue

            workflows.append(
                workflow.clone()
                if clone
                else workflow
            )

        workflows.sort(
            key=lambda item: (
                item.name.lower(),
                item.workflow_id,
            )
        )

        return workflows

    def search(
        self,
        query: str,
        enabled_only: bool = False,
    ) -> List[WorkflowDefinition]:
        """
        Busca por ID, nombre, descripción o etiquetas.
        """

        normalized_query = str(
            query
        ).strip().lower()

        if not normalized_query:
            return self.list(
                enabled_only=enabled_only
            )

        matches: List[
            WorkflowDefinition
        ] = []

        for workflow in self.list(
            enabled_only=enabled_only,
            clone=False,
        ):
            searchable_text = " ".join(
                [
                    workflow.workflow_id,
                    workflow.name,
                    workflow.description,
                    " ".join(workflow.tags),
                ]
            ).lower()

            if normalized_query in searchable_text:
                matches.append(
                    workflow.clone()
                )

        return matches

    def reset_all_steps(self) -> None:
        """
        Reinicia el estado de los pasos de todos
        los workflows registrados.
        """

        for workflow in self._workflows.values():
            workflow.reset_steps()

        self._touch()

    def validate_all(self) -> Dict[str, Any]:
        """
        Valida todas las definiciones registradas.
        """

        valid: List[str] = []
        invalid: List[Dict[str, str]] = []

        for workflow_id, workflow in (
            self._workflows.items()
        ):
            try:
                workflow.validate()
                valid.append(workflow_id)

            except Exception as error:
                invalid.append(
                    {
                        "workflow_id": workflow_id,
                        "error": str(error),
                    }
                )

        return {
            "valid": sorted(valid),
            "invalid": invalid,
            "valid_count": len(valid),
            "invalid_count": len(invalid),
            "is_valid": not invalid,
        }

    def stats(self) -> Dict[str, Any]:
        """
        Devuelve estadísticas generales.
        """

        total_steps = sum(
            workflow.step_count
            for workflow
            in self._workflows.values()
        )

        strategy_counts: Dict[str, int] = {}

        for workflow in self._workflows.values():
            strategy = workflow.strategy.value

            strategy_counts[strategy] = (
                strategy_counts.get(
                    strategy,
                    0,
                )
                + 1
            )

        return {
            "workflow_count": self.count,
            "enabled_count": self.enabled_count,
            "disabled_count": self.disabled_count,
            "total_steps": total_steps,
            "strategy_counts": strategy_counts,
            "registration_count": (
                self._registration_count
            ),
            "replacement_count": (
                self._replacement_count
            ),
            "removal_count": (
                self._removal_count
            ),
            "created_at": (
                self._created_at.isoformat()
            ),
            "updated_at": (
                self._updated_at.isoformat()
            ),
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializa el registro completo.
        """

        return {
            "stats": self.stats(),
            "workflows": [
                workflow.to_dict()
                for workflow
                in self.list()
            ],
        }

    @staticmethod
    def _validate_workflow(
        workflow: WorkflowDefinition,
    ) -> None:
        """
        Valida el tipo y contenido del workflow.
        """

        if not isinstance(
            workflow,
            WorkflowDefinition,
        ):
            raise TypeError(
                "workflow debe ser una instancia "
                "de WorkflowDefinition."
            )

        workflow.validate()

    @staticmethod
    def _normalize_workflow_id(
        workflow_id: str,
    ) -> str:
        """
        Normaliza un identificador.
        """

        return str(
            workflow_id or ""
        ).strip()

    def _touch(self) -> None:
        """
        Actualiza la fecha del registro.
        """

        self._updated_at = datetime.now()

    def __contains__(
        self,
        workflow_id: object,
    ) -> bool:
        return self.exists(
            str(workflow_id)
        )

    def __len__(self) -> int:
        return self.count

    def __iter__(self):
        """
        Itera sobre copias de workflows ordenados.
        """

        return iter(self.list())

    def __repr__(self) -> str:
        return (
            "WorkflowRegistry("
            f"workflows={self.count}, "
            f"enabled={self.enabled_count}, "
            f"disabled={self.disabled_count}"
            ")"
        )