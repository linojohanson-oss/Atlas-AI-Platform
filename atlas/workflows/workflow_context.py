"""
Atlas AI Platform - Workflow Context

Contexto compartido durante la ejecución de un workflow.

Este objeto conserva:

- La solicitud original.
- Variables compartidas.
- Resultados producidos por cada paso.
- Historial de ejecución.
- Errores y metadatos.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class WorkflowContext:
    """
    Estado compartido durante la ejecución de un workflow.
    """

    request: str
    workflow_id: str

    execution_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    variables: Dict[str, Any] = field(
        default_factory=dict
    )

    step_results: Dict[str, Dict[str, Any]] = field(
        default_factory=dict
    )

    history: List[Dict[str, Any]] = field(
        default_factory=list
    )

    errors: List[Dict[str, Any]] = field(
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
        Valida y normaliza los valores iniciales.
        """

        self.request = str(
            self.request
        ).strip()

        self.workflow_id = str(
            self.workflow_id
        ).strip()

        self.execution_id = str(
            self.execution_id
        ).strip()

        if not self.request:
            raise ValueError(
                "WorkflowContext requiere una solicitud."
            )

        if not self.workflow_id:
            raise ValueError(
                "WorkflowContext requiere un workflow_id."
            )

        if not self.execution_id:
            raise ValueError(
                "WorkflowContext requiere un execution_id."
            )

        self.variables = deepcopy(
            dict(self.variables or {})
        )

        self.step_results = deepcopy(
            dict(self.step_results or {})
        )

        self.history = deepcopy(
            list(self.history or [])
        )

        self.errors = deepcopy(
            list(self.errors or [])
        )

        self.metadata = deepcopy(
            dict(self.metadata or {})
        )

    # ============================================================
    # Variables compartidas
    # ============================================================

    def set_variable(
        self,
        key: str,
        value: Any,
    ) -> None:
        """
        Guarda una variable compartida.
        """

        normalized_key = str(
            key
        ).strip()

        if not normalized_key:
            raise ValueError(
                "La clave de la variable "
                "no puede estar vacía."
            )

        self.variables[
            normalized_key
        ] = deepcopy(value)

        self._touch()

    def get_variable(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Recupera una variable compartida.
        """

        normalized_key = str(
            key
        ).strip()

        if not normalized_key:
            return deepcopy(default)

        return deepcopy(
            self.variables.get(
                normalized_key,
                default,
            )
        )

    def has_variable(
        self,
        key: str,
    ) -> bool:
        """
        Indica si existe una variable.
        """

        normalized_key = str(
            key
        ).strip()

        return bool(
            normalized_key
            and normalized_key
            in self.variables
        )

    def remove_variable(
        self,
        key: str,
    ) -> Any:
        """
        Elimina una variable compartida.
        """

        normalized_key = str(
            key
        ).strip()

        if not normalized_key:
            return None

        value = self.variables.pop(
            normalized_key,
            None,
        )

        self._touch()

        return deepcopy(value)

    # ============================================================
    # Resultados de pasos
    # ============================================================

    def record_step_result(
        self,
        step_id: str,
        result: Dict[str, Any],
    ) -> None:
        """
        Registra el resultado completo de un paso.
        """

        normalized_step_id = self._normalize_step_id(
            step_id
        )

        if not normalized_step_id:
            raise ValueError(
                "step_id no puede estar vacío."
            )

        normalized_result = deepcopy(
            dict(result or {})
        )

        self.step_results[
            normalized_step_id
        ] = normalized_result

        self.add_history_event(
            event_type="step-result",
            step_id=normalized_step_id,
            details={
                "status": normalized_result.get(
                    "status",
                    "unknown",
                ),
            },
        )

        self._touch()

    def get_step_result(
        self,
        step_id: str,
        default: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Recupera el resultado de un paso.
        """

        normalized_step_id = self._normalize_step_id(
            step_id
        )

        if not normalized_step_id:
            return deepcopy(default)

        result = self.step_results.get(
            normalized_step_id
        )

        if result is None:
            return deepcopy(default)

        return deepcopy(result)

    def get_compact_step_result(
        self,
        step_id: str,
        default: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Recupera una versión compacta del resultado.

        Esta versión está pensada para transmitir contexto
        entre pasos sin arrastrar información operativa,
        métricas, permisos y objetos completos de agentes.
        """

        result = self.get_step_result(
            step_id=step_id,
        )

        if result is None:
            return deepcopy(default)

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

        compact_result = {
            "status": result.get(
                "status",
                execution.get(
                    "status",
                    "unknown",
                ),
            ),
            "output": execution.get(
                "output"
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
            key: deepcopy(value)
            for key, value
            in compact_result.items()
            if value is not None
        }

    def has_step_result(
        self,
        step_id: str,
    ) -> bool:
        """
        Indica si ya existe resultado para un paso.
        """

        normalized_step_id = self._normalize_step_id(
            step_id
        )

        return bool(
            normalized_step_id
            and normalized_step_id
            in self.step_results
        )

    # ============================================================
    # Historial
    # ============================================================

    def add_history_event(
        self,
        event_type: str,
        step_id: Optional[Any] = None,
        details: Optional[
            Dict[str, Any]
        ] = None,
        data: Optional[
            Dict[str, Any]
        ] = None,
    ) -> None:
        """
        Agrega un evento al historial del workflow.

        Admite las dos formas:

        add_history_event(
            event_type,
            details_dict,
        )

        y:

        add_history_event(
            event_type=...,
            step_id=...,
            details=...,
        )
        """

        normalized_event_type = str(
            event_type
        ).strip()

        if not normalized_event_type:
            raise ValueError(
                "event_type no puede estar vacío."
            )

        # Compatibilidad con:
        # add_history_event(event_type, data)
        if (
            isinstance(step_id, dict)
            and details is None
            and data is None
        ):
            details = step_id
            step_id = details.get(
                "step_id"
            )

        event_details = {}

        if data:
            event_details.update(
                deepcopy(dict(data))
            )

        if details:
            event_details.update(
                deepcopy(dict(details))
            )

        normalized_step_id = (
            self._normalize_step_id(step_id)
            if step_id is not None
            else None
        )

        # Evitamos duplicar step_id dentro de details.
        if "step_id" in event_details:
            if normalized_step_id is None:
                normalized_step_id = (
                    self._normalize_step_id(
                        event_details.get(
                            "step_id"
                        )
                    )
                )

            event_details.pop(
                "step_id",
                None,
            )

        event = {
            "event_type": (
                normalized_event_type
            ),
            "step_id": (
                normalized_step_id
            ),
            "details": deepcopy(
                event_details
            ),
            "created_at": (
                datetime.now().isoformat()
            ),
        }

        self.history.append(event)
        self._touch()

    # ============================================================
    # Errores
    # ============================================================

    def add_error(
        self,
        message: str,
        step_id: Optional[str] = None,
        error_type: Optional[str] = None,
        details: Optional[
            Dict[str, Any]
        ] = None,
    ) -> None:
        """
        Registra un error del workflow o de un paso.
        """

        normalized_message = str(
            message
        ).strip()

        if not normalized_message:
            raise ValueError(
                "El mensaje de error "
                "no puede estar vacío."
            )

        normalized_step_id = (
            self._normalize_step_id(step_id)
            if step_id is not None
            else None
        )

        normalized_error_type = (
            str(error_type).strip()
            if error_type is not None
            else None
        )

        error = {
            "message": normalized_message,
            "step_id": normalized_step_id,
            "error_type": normalized_error_type,
            "details": deepcopy(
                dict(details or {})
            ),
            "created_at": (
                datetime.now().isoformat()
            ),
        }

        self.errors.append(error)

        self.add_history_event(
            event_type="error",
            step_id=normalized_step_id,
            details={
                "message": normalized_message,
                "error_type": (
                    normalized_error_type
                ),
            },
        )

        self._touch()

    # ============================================================
    # Metadatos
    # ============================================================

    def merge_metadata(
        self,
        metadata: Dict[str, Any],
    ) -> None:
        """
        Incorpora metadatos adicionales.
        """

        if not metadata:
            return

        self.metadata.update(
            deepcopy(dict(metadata))
        )

        self._touch()

    # ============================================================
    # Construcción del contexto para pasos
    # ============================================================

    def build_step_input(
        self,
        step: Any = None,
        step_id: Optional[str] = None,
        input_template: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Construye el contexto que recibirá un paso.

        Acepta un objeto WorkflowStep o un identificador textual.
        Cuando recibe un WorkflowStep, incluye solamente los
        resultados de sus dependencias.
        """

        resolved_step = step

        if resolved_step is None:
            resolved_step = step_id

        normalized_step_id = (
            self._normalize_step_id(
                resolved_step
            )
        )

        dependencies: List[str] = []

        if hasattr(
            resolved_step,
            "depends_on",
        ):
            dependencies = [
                self._normalize_step_id(
                    dependency_id
                )
                for dependency_id
                in list(
                    getattr(
                        resolved_step,
                        "depends_on",
                        [],
                    )
                    or []
                )
            ]

        previous_results: Dict[
            str,
            Dict[str, Any],
        ] = {}

        if dependencies:
            for dependency_id in dependencies:
                compact_result = (
                    self.get_compact_step_result(
                        dependency_id
                    )
                )

                if compact_result is not None:
                    previous_results[
                        dependency_id
                    ] = compact_result

        prompt = None

        if input_template is not None:
            prompt = str(
                input_template
            ).strip() or None

        elif hasattr(
            resolved_step,
            "input_template",
        ):
            template_value = getattr(
                resolved_step,
                "input_template",
                None,
            )

            if template_value:
                prompt = str(
                    template_value
                ).strip() or None

        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "step_id": normalized_step_id,
            "request": self.request,
            "prompt": prompt,
            "variables": deepcopy(
                self.variables
            ),
            "previous_results": (
                previous_results
            ),
            "metadata": deepcopy(
                self.metadata
            ),
        }

    # ============================================================
    # Serialización
    # ============================================================

    def snapshot(self) -> Dict[str, Any]:
        """
        Devuelve una copia completa del contexto.
        """

        return self.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializa el contexto.
        """

        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "request": self.request,
            "variables": deepcopy(
                self.variables
            ),
            "step_results": deepcopy(
                self.step_results
            ),
            "history": deepcopy(
                self.history
            ),
            "errors": deepcopy(
                self.errors
            ),
            "metadata": deepcopy(
                self.metadata
            ),
            "created_at": (
                self.created_at.isoformat()
            ),
            "updated_at": (
                self.updated_at.isoformat()
            ),
        }

    # ============================================================
    # Utilidades internas
    # ============================================================

    @staticmethod
    def _normalize_step_id(
        step: Any,
    ) -> str:
        """
        Extrae y normaliza el identificador de un paso.

        Admite tanto un string como un objeto WorkflowStep.
        """

        if step is None:
            return ""

        if hasattr(
            step,
            "step_id",
        ):
            step = getattr(
                step,
                "step_id"
            )

        return str(
            step
        ).strip()

    def _touch(self) -> None:
        """
        Actualiza la fecha de modificación.
        """

        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        return (
            "WorkflowContext("
            f"workflow_id='{self.workflow_id}', "
            f"execution_id='{self.execution_id}', "
            f"steps={len(self.step_results)}, "
            f"errors={len(self.errors)}"
            ")"
        )