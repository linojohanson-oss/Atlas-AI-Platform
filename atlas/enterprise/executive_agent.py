from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from atlas.enterprise.agent_selector import SelectionStrategy
from atlas.enterprise.department_runtime import DepartmentRuntime


class ExecutiveAgentStatus(str, Enum):
    """
    Estados posibles del Executive Agent.
    """

    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ExecutiveDecision:
    """
    Representa la decisión tomada por el Executive Agent.
    """

    request: str
    department_id: str
    confidence: float
    matched_keywords: List[str] = field(default_factory=list)
    reason: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request": self.request,
            "department_id": self.department_id,
            "confidence": self.confidence,
            "matched_keywords": list(self.matched_keywords),
            "reason": self.reason,
            "created_at": self.created_at,
        }


class ExecutiveAgent:
    """
    Agente ejecutivo de Atlas AI OS.

    Responsabilidades:

    - Recibir solicitudes generales del usuario.
    - Analizar la intención de la solicitud.
    - Determinar el departamento más apropiado.
    - Delegar la ejecución al DepartmentRuntime.
    - Registrar decisiones y resultados ejecutivos.
    """

    DEFAULT_DEPARTMENT = "planning"

    DEPARTMENT_KEYWORDS: Dict[str, List[str]] = {
        "executive": [
            "estrategia",
            "estrategico",
            "direccion",
            "gobierno",
            "politica",
            "decision ejecutiva",
            "organizacion",
            "prioridad",
            "objetivo general",
        ],
        "planning": [
            "plan",
            "planificar",
            "planificacion",
            "workflow",
            "flujo",
            "estrategia de ejecucion",
            "organizar",
            "descomponer",
            "pasos",
            "cronograma",
            "roadmap",
            "arquitectura de tareas",
        ],
        "research": [
            "investigar",
            "investigacion",
            "buscar informacion",
            "analizar fuentes",
            "fuentes",
            "documentacion",
            "comparar",
            "estudiar",
            "explorar",
            "descubrir",
            "sintetizar",
        ],
        "engineering": [
            "codigo",
            "programar",
            "programacion",
            "python",
            "javascript",
            "java",
            "api",
            "backend",
            "frontend",
            "base de datos",
            "software",
            "bug",
            "error",
            "depurar",
            "debug",
            "corregir codigo",
            "implementar",
            "desarrollar",
            "crear archivo",
            "refactorizar",
            "test",
            "prueba unitaria",
            "repositorio",
        ],
         "security": [
            "seguridad",
            "vulnerabilidad",
            "vulnerabilidades",
            "riesgo",
            "riesgos",
            "permiso",
            "permisos",
            "autenticacion",
            "autorizacion",
            "credencial",
            "credenciales",
            "token",
            "tokens",
            "cifrado",
            "ataque",
            "ataques",
            "amenaza",
            "amenazas",
            "auditoria de seguridad",
            "politica de acceso",
        ],
        "review": [
            "revisar",
            "revision",
            "validar",
            "validacion",
            "calidad",
            "aprobar",
            "verificar",
            "control",
            "compliance",
            "cumplimiento",
            "auditar",
            "evaluar resultado",
        ],
        "operations": [
            "operacion",
            "operaciones",
            "ejecutar servicio",
            "monitorear",
            "monitoreo",
            "produccion",
            "incidente",
            "continuidad",
            "despliegue",
            "deploy",
            "servidor",
            "estado del sistema",
            "mantenimiento",
        ],
        "knowledge": [
            "memoria",
            "conocimiento",
            "contexto",
            "recordar",
            "historial",
            "documentar",
            "base de conocimiento",
            "recuperar informacion",
            "guardar conocimiento",
            "activo de conocimiento",
        ],
    }

    DEPARTMENT_KEYWORD_WEIGHTS: Dict[str, Dict[str, float]] = {
        "executive": {
            "decision ejecutiva": 5.0,
            "gobierno": 4.0,
            "direccion": 3.0,
            "estrategia": 2.0,
        },
        "planning": {
            "planificar": 4.0,
            "planificacion": 4.0,
            "cronograma": 3.0,
            "roadmap": 3.0,
            "workflow": 2.0,
            "pasos": 1.5,
        },
        "research": {
            "investigar": 5.0,
            "investigacion": 5.0,
            "analizar fuentes": 5.0,
            "buscar informacion": 4.0,
            "comparar": 3.0,
            "fuentes": 2.0,
            "documentacion": 1.5,
        },
        "engineering": {
            "corregir codigo": 5.0,
            "crear archivo": 4.0,
            "refactorizar": 4.0,
            "implementar": 3.5,
            "desarrollar": 3.5,
            "programar": 3.5,
            "debug": 3.0,
            "depurar": 3.0,
            "bug": 3.0,
            "error": 2.0,
            "codigo": 2.0,
            "python": 1.0,
            "api": 1.0,
            "backend": 1.0,
            "frontend": 1.0,
        },
        "security": {
            "auditoria de seguridad": 6.0,
            "politica de acceso": 6.0,
            "vulnerabilidad": 5.0,
            "vulnerabilidades": 5.0,
            "seguridad": 5.0,
            "autenticacion": 4.0,
            "autorizacion": 4.0,
            "credencial": 4.0,
            "credenciales": 4.0,
            "cifrado": 4.0,
            "ataque": 4.0,
            "ataques": 4.0,
            "amenaza": 4.0,
            "amenazas": 4.0,
            "riesgo": 3.5,
            "riesgos": 3.5,
            "permiso": 2.5,
            "permisos": 2.5,
            "token": 2.5,
            "tokens": 2.5,
        },
        "review": {
            "evaluar resultado": 5.0,
            "cumplimiento": 4.0,
            "compliance": 4.0,
            "validar": 3.5,
            "verificar": 3.5,
            "auditar": 3.5,
            "calidad": 3.0,
            "revisar": 2.0,
        },
        "operations": {
            "estado del sistema": 5.0,
            "ejecutar servicio": 4.0,
            "incidente": 4.0,
            "produccion": 3.0,
            "despliegue": 3.0,
            "deploy": 3.0,
            "monitorear": 3.0,
            "mantenimiento": 2.5,
            "servidor": 2.0,
        },
        "knowledge": {
            "base de conocimiento": 5.0,
            "guardar conocimiento": 5.0,
            "recuperar informacion": 4.0,
            "memoria": 3.5,
            "recordar": 3.5,
            "contexto": 2.5,
            "historial": 2.5,
            "documentar": 2.0,
        },
    }

    DEPARTMENT_TIE_BREAK_PRIORITY: Dict[str, int] = {
        "security": 80,
        "review": 70,
        "engineering": 60,
        "research": 50,
        "operations": 40,
        "knowledge": 30,
        "planning": 20,
        "executive": 10,
    }

    DEPARTMENT_CAPABILITIES: Dict[str, List[str]] = {
        "executive": [
            "governance",
            "decision-making",
        ],
        "planning": [
            "task-planning",
            "general-reasoning",
        ],
        "research": [
            "research",
            "information-analysis",
        ],
        "engineering": [
            "coding",
            "debugging",
        ],
        "security": [
            "security-analysis",
        ],
        "review": [
            "review",
            "validation",
        ],
        "operations": [
            "operations",
            "monitoring",
        ],
        "knowledge": [
            "knowledge-management",
            "context-analysis",
        ],
    }

    def __init__(
        self,
        department_runtime: DepartmentRuntime,
    ) -> None:
        if department_runtime is None:
            raise ValueError(
                "department_runtime no puede ser None."
            )

        if not hasattr(department_runtime, "execute"):
            raise TypeError(
                "department_runtime no implementa el método "
                "requerido 'execute'."
            )

        self.department_runtime = department_runtime

        self._status = ExecutiveAgentStatus.CREATED
        self._decisions: List[ExecutiveDecision] = []
        self._execution_count = 0
        self._successful_executions = 0
        self._failed_executions = 0

        self._created_at = datetime.now().isoformat()
        self._started_at: Optional[str] = None
        self._stopped_at: Optional[str] = None
        self._last_error: Optional[str] = None

    # ============================================================
    # Propiedades
    # ============================================================

    @property
    def status(self) -> ExecutiveAgentStatus:
        return self._status

    @property
    def is_ready(self) -> bool:
        return self._status in {
            ExecutiveAgentStatus.READY,
            ExecutiveAgentStatus.RUNNING,
        }

    @property
    def execution_count(self) -> int:
        return self._execution_count

    @property
    def decision_count(self) -> int:
        return len(self._decisions)

    # ============================================================
    # Ciclo de vida
    # ============================================================

    def start(self) -> None:
        """
        Inicia el Executive Agent.
        """

        if self.is_ready:
            return

        if not self.department_runtime.is_ready:
            self.department_runtime.start()

        self._status = ExecutiveAgentStatus.READY
        self._started_at = datetime.now().isoformat()
        self._stopped_at = None
        self._last_error = None

    def stop(self) -> None:
        """
        Detiene el Executive Agent.
        """

        if self._status == ExecutiveAgentStatus.STOPPED:
            return

        self._status = ExecutiveAgentStatus.STOPPED
        self._stopped_at = datetime.now().isoformat()

    # ============================================================
    # Ejecución ejecutiva
    # ============================================================

    def execute(
        self,
        request: str,
        department_id: Optional[str] = None,
        required_capabilities: Optional[List[str]] = None,
        required_tools: Optional[List[str]] = None,
        required_permissions: Optional[List[str]] = None,
        preferred_agent_ids: Optional[List[str]] = None,
        excluded_agent_ids: Optional[List[str]] = None,
        strategy: SelectionStrategy = SelectionStrategy.BALANCED,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analiza una solicitud y la delega al departamento apropiado.

        Si department_id es proporcionado, se utiliza directamente.
        De lo contrario, el Executive Agent resuelve automáticamente
        el departamento según la intención de la solicitud.
        """

        self._ensure_ready()

        normalized_request = str(request).strip()

        if not normalized_request:
            raise ValueError(
                "La solicitud ejecutiva no puede estar vacía."
            )

        self._status = ExecutiveAgentStatus.RUNNING
        self._execution_count += 1

        try:
            if department_id:
                decision = ExecutiveDecision(
                    request=normalized_request,
                    department_id=self._normalize_identifier(
                        department_id
                    ),
                    confidence=1.0,
                    matched_keywords=[],
                    reason=(
                        "Departamento indicado explícitamente "
                        "por el solicitante."
                    ),
                )
            else:
                decision = self.resolve_department(
                    normalized_request
                )

            self._decisions.append(decision)

            capabilities = (
                list(required_capabilities)
                if required_capabilities is not None
                else self._default_capabilities(
                    decision.department_id
                )
            )

            executive_metadata = dict(metadata or {})
            executive_metadata.update(
                {
                    "executive_agent": True,
                    "executive_decision": decision.to_dict(),
                }
            )

            runtime_result = self.department_runtime.execute(
                department_id=decision.department_id,
                task=normalized_request,
                required_capabilities=capabilities,
                required_tools=required_tools or [],
                required_permissions=required_permissions or [],
                preferred_agent_ids=preferred_agent_ids or [],
                excluded_agent_ids=excluded_agent_ids or [],
                strategy=strategy,
                metadata=executive_metadata,
            )

            self._successful_executions += 1
            self._status = ExecutiveAgentStatus.READY
            self._last_error = None

            return {
                "agent": "executive-agent",
                "status": "completed",
                "decision": decision.to_dict(),
                "execution": runtime_result,
            }

        except Exception as error:
            self._failed_executions += 1
            self._last_error = str(error)
            self._status = ExecutiveAgentStatus.ERROR
            raise


    def execute_collaborative(
        self,
        request: str,
        max_departments: int = 3,
        min_score: float = 1.0,
        min_relative_score: float = 0.20,
        required_tools: Optional[List[str]] = None,
        required_permissions: Optional[List[str]] = None,
        strategy: SelectionStrategy = SelectionStrategy.BALANCED,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta una solicitud en varios departamentos relevantes.

        El Intent Router V2 genera un ranking y selecciona:

        - El departamento principal.
        - Departamentos alternativos con puntuación suficiente.
        - Hasta max_departments departamentos.

        Los departamentos sin agentes disponibles se registran como
        omitidos, sin interrumpir toda la ejecución colaborativa.
        """

        self._ensure_ready()

        normalized_request = str(request).strip()

        if not normalized_request:
            raise ValueError(
                "La solicitud colaborativa no puede estar vacía."
            )

        if max_departments < 1:
            raise ValueError(
                "max_departments debe ser mayor o igual a 1."
            )

        if min_score < 0:
            raise ValueError(
                "min_score no puede ser negativo."
            )

        if not 0 <= min_relative_score <= 1:
            raise ValueError(
                "min_relative_score debe estar entre 0 y 1."
            )

        self._status = ExecutiveAgentStatus.RUNNING
        self._execution_count += 1

        try:
            ranking = self.rank_departments(
                normalized_request
            )

            scored_candidates = [
                candidate
                for candidate in ranking
                if candidate["score"] > 0
            ]

            if not scored_candidates:
                scored_candidates = [
                    {
                        "department_id": self.DEFAULT_DEPARTMENT,
                        "score": 0.0,
                        "matched_keywords": [],
                        "match_count": 0,
                        "tie_break_priority": (
                            self.DEPARTMENT_TIE_BREAK_PRIORITY.get(
                                self.DEFAULT_DEPARTMENT,
                                0,
                            )
                        ),
                    }
                ]

            primary_candidate = scored_candidates[0]
            primary_score = primary_candidate["score"]

            selected_candidates: List[Dict[str, Any]] = []

            for candidate in scored_candidates:
                candidate_score = candidate["score"]

                if candidate is primary_candidate:
                    selected_candidates.append(candidate)
                    continue

                relative_score = (
                    candidate_score / primary_score
                    if primary_score > 0
                    else 0.0
                )

                if candidate_score < min_score:
                    continue

                if relative_score < min_relative_score:
                    continue

                selected_candidates.append(candidate)

                if len(selected_candidates) >= max_departments:
                    break

            selected_candidates = selected_candidates[
                :max_departments
            ]

            primary_decision = ExecutiveDecision(
                request=normalized_request,
                department_id=primary_candidate[
                    "department_id"
                ],
                confidence=self._calculate_ranking_confidence(
                    primary_candidate=primary_candidate,
                    candidates=scored_candidates,
                ),
                matched_keywords=list(
                    primary_candidate["matched_keywords"]
                ),
                reason=(
                    "Ejecución colaborativa iniciada mediante "
                    "Intent Router V2. Departamento principal: "
                    f"{primary_candidate['department_id']}."
                ),
            )

            self._decisions.append(primary_decision)

            base_metadata = dict(metadata or {})
            base_metadata.update(
                {
                    "executive_agent": True,
                    "collaborative_execution": True,
                    "primary_decision": (
                        primary_decision.to_dict()
                    ),
                    "department_ranking": ranking,
                }
            )

            executions: List[Dict[str, Any]] = []
            skipped_departments: List[Dict[str, Any]] = []

            for order, candidate in enumerate(
                selected_candidates,
                start=1,
            ):
                department_id = candidate["department_id"]

                department_metadata = dict(base_metadata)
                department_metadata.update(
                    {
                        "collaboration_order": order,
                        "collaboration_department": (
                            department_id
                        ),
                        "collaboration_score": (
                            candidate["score"]
                        ),
                        "collaboration_matches": list(
                            candidate["matched_keywords"]
                        ),
                    }
                )

                try:
                    runtime_result = (
                        self.department_runtime.execute(
                            department_id=department_id,
                            task=normalized_request,
                            required_capabilities=(
                                self._default_capabilities(
                                    department_id
                                )
                            ),
                            required_tools=required_tools or [],
                            required_permissions=(
                                required_permissions or []
                            ),
                            preferred_agent_ids=[],
                            excluded_agent_ids=[],
                            strategy=strategy,
                            metadata=department_metadata,
                        )
                    )

                    executions.append(
                        {
                            "order": order,
                            "department_id": department_id,
                            "score": candidate["score"],
                            "matched_keywords": list(
                                candidate[
                                    "matched_keywords"
                                ]
                            ),
                            "status": "completed",
                            "result": runtime_result,
                        }
                    )

                except RuntimeError as error:
                    skipped_departments.append(
                        {
                            "order": order,
                            "department_id": department_id,
                            "score": candidate["score"],
                            "matched_keywords": list(
                                candidate[
                                    "matched_keywords"
                                ]
                            ),
                            "status": "skipped",
                            "reason": str(error),
                        }
                    )

            if not executions:
                raise RuntimeError(
                    "Ningún departamento pudo ejecutar la "
                    "solicitud colaborativa."
                )

            self._successful_executions += 1
            self._status = ExecutiveAgentStatus.READY
            self._last_error = None

            return {
                "agent": "executive-agent",
                "mode": "collaborative",
                "status": "completed",
                "request": normalized_request,
                "primary_decision": (
                    primary_decision.to_dict()
                ),
                "selected_departments": [
                    {
                        "department_id": candidate[
                            "department_id"
                        ],
                        "score": candidate["score"],
                        "matched_keywords": list(
                            candidate["matched_keywords"]
                        ),
                    }
                    for candidate in selected_candidates
                ],
                "executions": executions,
                "skipped_departments": skipped_departments,
                "execution_count": len(executions),
                "skipped_count": len(
                    skipped_departments
                ),
            }

        except Exception as error:
            self._failed_executions += 1
            self._last_error = str(error)
            self._status = ExecutiveAgentStatus.ERROR
            raise

    # ============================================================
    # Resolución de intención
    # ============================================================

    def rank_departments(
            self,
            request: str,
    ) -> List[Dict[str, Any]]:
        """
        Puntúa y ordena los departamentos según la intención
        detectada en la solicitud.
        """

        normalized_request = self._normalize_text(request)
        ranking: List[Dict[str, Any]] = []

        for department_id, keywords in (
                self.DEPARTMENT_KEYWORDS.items()
        ):
            department_matches: List[str] = []
            department_score = 0.0

            department_weights = (
                self.DEPARTMENT_KEYWORD_WEIGHTS.get(
                    department_id,
                    {},
                )
            )

            for keyword in keywords:
                normalized_keyword = self._normalize_text(
                    keyword
                )

                keyword_pattern = (
                    r"(?<!\w)"
                    + re.escape(normalized_keyword)
                    + r"(?!\w)"
                )

                if not re.search(
                    keyword_pattern,
                    normalized_request,
                ):
                    continue

                department_matches.append(keyword)

                default_weight = (
                    2.0
                    if len(normalized_keyword.split()) > 1
                    else 1.0
                )

                keyword_weight = department_weights.get(
                    keyword,
                    default_weight,
                )

                department_score += keyword_weight

            ranking.append(
                {
                    "department_id": department_id,
                    "score": round(department_score, 4),
                    "matched_keywords": department_matches,
                    "match_count": len(department_matches),
                    "tie_break_priority": (
                        self.DEPARTMENT_TIE_BREAK_PRIORITY.get(
                            department_id,
                            0,
                        )
                    ),
                }
            )

        ranking.sort(
            key=lambda candidate: (
                candidate["score"],
                candidate["match_count"],
                candidate["tie_break_priority"],
            ),
            reverse=True,
        )

        return ranking

    def resolve_department(
            self,
            request: str,
    ) -> ExecutiveDecision:
        """
        Determina el departamento principal utilizando
        puntuación ponderada y ranking de intención.
        """

        normalized_request = str(request).strip()

        ranking = self.rank_departments(
            normalized_request
        )

        candidates_with_score = [
            candidate
            for candidate in ranking
            if candidate["score"] > 0
        ]

        if not candidates_with_score:
            return ExecutiveDecision(
                request=normalized_request,
                department_id=self.DEFAULT_DEPARTMENT,
                confidence=0.40,
                matched_keywords=[],
                reason=(
                    "No se detectaron palabras clave suficientes. "
                    "La solicitud fue enviada al departamento de "
                    "planificación para su análisis."
                ),
            )

        selected_candidate = candidates_with_score[0]
        selected_score = selected_candidate["score"]

        total_score = sum(
            candidate["score"]
            for candidate in candidates_with_score
        )

        confidence = (
            selected_score / total_score
            if total_score > 0
            else 0.40
        )

        confidence = max(
            0.50,
            min(0.99, confidence),
        )

        selected_matches = selected_candidate[
            "matched_keywords"
        ]

        alternative_candidates = [
            (
                candidate["department_id"],
                candidate["score"],
            )
            for candidate in candidates_with_score[1:4]
        ]

        reason = (
                "Departamento seleccionado mediante Intent Router V2. "
                "Coincidencias: "
                + ", ".join(selected_matches)
        )

        if alternative_candidates:
            alternatives_text = ", ".join(
                f"{department}={score}"
                for department, score
                in alternative_candidates
            )

            reason += (
                    ". Alternativas puntuadas: "
                    + alternatives_text
            )

        return ExecutiveDecision(
            request=normalized_request,
            department_id=selected_candidate[
                "department_id"
            ],
            confidence=round(confidence, 4),
            matched_keywords=selected_matches,
            reason=reason,
        )
    # ============================================================
    # Consultas
    # ============================================================

    def get_last_decision(
        self,
    ) -> Optional[Dict[str, Any]]:
        if not self._decisions:
            return None

        return self._decisions[-1].to_dict()

    def list_decisions(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        decisions = list(
            reversed(self._decisions)
        )

        if limit is not None:
            if limit < 1:
                return []

            decisions = decisions[:limit]

        return [
            decision.to_dict()
            for decision in decisions
        ]

    def summary(self) -> Dict[str, Any]:
        return {
            "status": self._status.value,
            "is_ready": self.is_ready,
            "created_at": self._created_at,
            "started_at": self._started_at,
            "stopped_at": self._stopped_at,
            "last_error": self._last_error,
            "execution_count": self._execution_count,
            "successful_executions": (
                self._successful_executions
            ),
            "failed_executions": (
                self._failed_executions
            ),
            "decision_count": self.decision_count,
            "default_department": self.DEFAULT_DEPARTMENT,
            "available_departments": sorted(
                self.DEPARTMENT_KEYWORDS.keys()
            ),
            "last_decision": self.get_last_decision(),
        }

    # ============================================================
    # Utilidades internas
    # ============================================================

    def _ensure_ready(self) -> None:
        if not self.is_ready:
            raise RuntimeError(
                "ExecutiveAgent no está iniciado. "
                "Ejecute start() antes de utilizarlo."
            )

        if not self.department_runtime.is_ready:
            raise RuntimeError(
                "DepartmentRuntime no está listo."
            )

    @staticmethod
    def _calculate_ranking_confidence(
        primary_candidate: Dict[str, Any],
        candidates: List[Dict[str, Any]],
    ) -> float:
        """
        Calcula la confianza del departamento principal
        respecto del total de puntuaciones positivas.
        """

        primary_score = float(
            primary_candidate.get("score", 0.0)
        )

        total_score = sum(
            float(candidate.get("score", 0.0))
            for candidate in candidates
            if float(candidate.get("score", 0.0)) > 0
        )

        if total_score <= 0:
            return 0.40

        confidence = primary_score / total_score

        confidence = max(
            0.50,
            min(0.99, confidence),
        )

        return round(confidence, 4)

    def _default_capabilities(
        self,
        department_id: str,
    ) -> List[str]:
        normalized_id = self._normalize_identifier(
            department_id
        )

        return list(
            self.DEPARTMENT_CAPABILITIES.get(
                normalized_id,
                [],
            )
        )

    @staticmethod
    def _normalize_identifier(
        value: str,
    ) -> str:
        normalized = str(value).strip().lower()
        normalized = normalized.replace(" ", "-")
        normalized = normalized.replace("_", "-")

        if not normalized:
            raise ValueError(
                "El identificador no puede estar vacío."
            )

        return normalized

    @staticmethod
    def _normalize_text(
        value: str,
    ) -> str:
        text = str(value).strip().lower()

        text = unicodedata.normalize(
            "NFD",
            text,
        )

        text = "".join(
            character
            for character in text
            if unicodedata.category(character) != "Mn"
        )

        return " ".join(
            text.split()
        )