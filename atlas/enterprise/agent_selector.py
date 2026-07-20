from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from atlas.enterprise.agent_profile import (
    AgentLevel,
    AgentProfile,
    AuthorityLevel,
)
from atlas.enterprise.enterprise_agent_registry import (
    EnterpriseAgentRegistry,
)


class SelectionStrategy(str, Enum):
    """
    Estrategias disponibles para seleccionar agentes.
    """

    BALANCED = "balanced"
    PERFORMANCE = "performance"
    LOWEST_LOAD = "lowest-load"
    PRIORITY = "priority"
    HIERARCHY = "hierarchy"


@dataclass
class AgentSelectionCriteria:
    """
    Criterios usados para buscar y clasificar agentes.
    """

    required_capabilities: List[str] = field(
        default_factory=list
    )

    preferred_department: Optional[str] = None
    required_tools: List[str] = field(
        default_factory=list
    )

    required_permissions: List[str] = field(
        default_factory=list
    )

    minimum_level: Optional[AgentLevel] = None
    minimum_authority: Optional[AuthorityLevel] = None

    available_only: bool = True
    enabled_only: bool = True

    strategy: SelectionStrategy = SelectionStrategy.BALANCED

    preferred_agent_ids: List[str] = field(
        default_factory=list
    )

    excluded_agent_ids: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        self.required_capabilities = self._normalize_collection(
            self.required_capabilities
        )

        self.required_tools = self._normalize_collection(
            self.required_tools
        )

        self.required_permissions = self._normalize_collection(
            self.required_permissions
        )

        self.preferred_agent_ids = self._normalize_collection(
            self.preferred_agent_ids
        )

        self.excluded_agent_ids = self._normalize_collection(
            self.excluded_agent_ids
        )

        if self.preferred_department:
            self.preferred_department = str(
                self.preferred_department
            ).strip()

        if not isinstance(
            self.strategy,
            SelectionStrategy,
        ):
            self.strategy = SelectionStrategy(
                self.strategy
            )

        if (
            self.minimum_level is not None
            and not isinstance(
                self.minimum_level,
                AgentLevel,
            )
        ):
            self.minimum_level = AgentLevel(
                self.minimum_level
            )

        if (
            self.minimum_authority is not None
            and not isinstance(
                self.minimum_authority,
                AuthorityLevel,
            )
        ):
            self.minimum_authority = AuthorityLevel(
                self.minimum_authority
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

    @classmethod
    def _normalize_collection(
        cls,
        values: Sequence[str],
    ) -> List[str]:
        return sorted(
            {
                cls._normalize_identifier(value)
                for value in values
                if str(value).strip()
            }
        )


@dataclass
class AgentScoreBreakdown:
    """
    Desglose de puntuación de un agente candidato.
    """

    capability_score: float = 0.0
    tool_score: float = 0.0
    permission_score: float = 0.0
    department_score: float = 0.0
    availability_score: float = 0.0
    load_score: float = 0.0
    performance_score: float = 0.0
    confidence_score: float = 0.0
    quality_score: float = 0.0
    priority_score: float = 0.0
    hierarchy_score: float = 0.0
    preferred_agent_score: float = 0.0

    total_score: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "capability_score": round(
                self.capability_score,
                4,
            ),
            "tool_score": round(
                self.tool_score,
                4,
            ),
            "permission_score": round(
                self.permission_score,
                4,
            ),
            "department_score": round(
                self.department_score,
                4,
            ),
            "availability_score": round(
                self.availability_score,
                4,
            ),
            "load_score": round(
                self.load_score,
                4,
            ),
            "performance_score": round(
                self.performance_score,
                4,
            ),
            "confidence_score": round(
                self.confidence_score,
                4,
            ),
            "quality_score": round(
                self.quality_score,
                4,
            ),
            "priority_score": round(
                self.priority_score,
                4,
            ),
            "hierarchy_score": round(
                self.hierarchy_score,
                4,
            ),
            "preferred_agent_score": round(
                self.preferred_agent_score,
                4,
            ),
            "total_score": round(
                self.total_score,
                4,
            ),
        }


@dataclass
class AgentSelectionResult:
    """
    Resultado de selección o ranking de un agente.
    """

    agent: AgentProfile
    score: float
    breakdown: AgentScoreBreakdown
    reasons: List[str] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent.agent_id,
            "name": self.agent.name,
            "department": self.agent.department,
            "role": self.agent.role,
            "score": round(
                self.score,
                4,
            ),
            "reasons": list(
                self.reasons
            ),
            "breakdown": self.breakdown.to_dict(),
            "agent": self.agent.to_dict(),
        }


class AgentSelector:
    """
    Motor de selección de agentes de Atlas AI OS.

    Evalúa perfiles empresariales según capacidades,
    herramientas, permisos, disponibilidad, carga,
    prioridad, jerarquía y métricas operativas.
    """

    _LEVEL_RANK = {
        AgentLevel.JUNIOR: 1,
        AgentLevel.MID: 2,
        AgentLevel.SENIOR: 3,
        AgentLevel.LEAD: 4,
        AgentLevel.DIRECTOR: 5,
        AgentLevel.EXECUTIVE: 6,
    }

    _AUTHORITY_RANK = {
        AuthorityLevel.LOW: 1,
        AuthorityLevel.MEDIUM: 2,
        AuthorityLevel.HIGH: 3,
        AuthorityLevel.CRITICAL: 4,
    }

    def __init__(
        self,
        registry: EnterpriseAgentRegistry,
    ) -> None:
        if not isinstance(
            registry,
            EnterpriseAgentRegistry,
        ):
            raise TypeError(
                "registry debe ser una instancia "
                "de EnterpriseAgentRegistry."
            )

        self.registry = registry

    def select(
        self,
        criteria: AgentSelectionCriteria,
    ) -> Optional[AgentSelectionResult]:
        """
        Selecciona el mejor agente según los criterios.
        """
        ranked = self.rank(
            criteria=criteria,
            limit=1,
        )

        if not ranked:
            return None

        return ranked[0]

    def rank(
        self,
        criteria: AgentSelectionCriteria,
        limit: Optional[int] = None,
    ) -> List[AgentSelectionResult]:
        """
        Clasifica agentes candidatos de mayor a menor puntuación.
        """
        if not isinstance(
            criteria,
            AgentSelectionCriteria,
        ):
            raise TypeError(
                "criteria debe ser una instancia "
                "de AgentSelectionCriteria."
            )

        candidates = self._filter_candidates(
            criteria
        )

        results = [
            self._evaluate_agent(
                agent=agent,
                criteria=criteria,
            )
            for agent in candidates
        ]

        results.sort(
            key=lambda item: (
                -item.score,
                item.agent.priority,
                item.agent.load_percentage,
                item.agent.agent_id,
            )
        )

        if limit is not None:
            if limit < 1:
                return []

            return results[:limit]

        return results

    def select_by_capability(
        self,
        capability: str,
        department: Optional[str] = None,
        strategy: SelectionStrategy = SelectionStrategy.BALANCED,
        available_only: bool = True,
    ) -> Optional[AgentSelectionResult]:
        """
        Atajo para seleccionar por una única capacidad.
        """
        criteria = AgentSelectionCriteria(
            required_capabilities=[
                capability
            ],
            preferred_department=department,
            strategy=strategy,
            available_only=available_only,
        )

        return self.select(
            criteria
        )

    def explain_selection(
        self,
        criteria: AgentSelectionCriteria,
    ) -> Dict[str, Any]:
        """
        Devuelve una explicación completa de la selección.
        """
        ranking = self.rank(
            criteria
        )

        selected = (
            ranking[0].to_dict()
            if ranking
            else None
        )

        return {
            "selected": selected,
            "candidate_count": len(
                ranking
            ),
            "ranking": [
                result.to_dict()
                for result in ranking
            ],
            "criteria": {
                "required_capabilities": list(
                    criteria.required_capabilities
                ),
                "preferred_department": (
                    criteria.preferred_department
                ),
                "required_tools": list(
                    criteria.required_tools
                ),
                "required_permissions": list(
                    criteria.required_permissions
                ),
                "minimum_level": (
                    criteria.minimum_level.value
                    if criteria.minimum_level
                    else None
                ),
                "minimum_authority": (
                    criteria.minimum_authority.value
                    if criteria.minimum_authority
                    else None
                ),
                "available_only": (
                    criteria.available_only
                ),
                "enabled_only": (
                    criteria.enabled_only
                ),
                "strategy": (
                    criteria.strategy.value
                ),
                "preferred_agent_ids": list(
                    criteria.preferred_agent_ids
                ),
                "excluded_agent_ids": list(
                    criteria.excluded_agent_ids
                ),
            },
        }

    def _filter_candidates(
        self,
        criteria: AgentSelectionCriteria,
    ) -> List[AgentProfile]:
        candidates: List[AgentProfile] = []

        for agent in self.registry.list_profiles():
            if (
                agent.agent_id
                in criteria.excluded_agent_ids
            ):
                continue

            if criteria.enabled_only and not agent.enabled:
                continue

            if criteria.available_only and not agent.is_available:
                continue

            if not self._meets_level_requirement(
                agent,
                criteria.minimum_level,
            ):
                continue

            if not self._meets_authority_requirement(
                agent,
                criteria.minimum_authority,
            ):
                continue

            if not self._has_all_capabilities(
                agent,
                criteria.required_capabilities,
            ):
                continue

            if not self._has_all_tools(
                agent,
                criteria.required_tools,
            ):
                continue

            if not self._has_all_permissions(
                agent,
                criteria.required_permissions,
            ):
                continue

            candidates.append(
                agent
            )

        return candidates

    def _evaluate_agent(
        self,
        agent: AgentProfile,
        criteria: AgentSelectionCriteria,
    ) -> AgentSelectionResult:
        breakdown = AgentScoreBreakdown()
        reasons: List[str] = []

        breakdown.capability_score = (
            self._capability_score(
                agent,
                criteria.required_capabilities,
            )
        )

        breakdown.tool_score = (
            self._tool_score(
                agent,
                criteria.required_tools,
            )
        )

        breakdown.permission_score = (
            self._permission_score(
                agent,
                criteria.required_permissions,
            )
        )

        breakdown.department_score = (
            self._department_score(
                agent,
                criteria.preferred_department,
            )
        )

        breakdown.availability_score = (
            100.0
            if agent.is_available
            else 0.0
        )

        breakdown.load_score = max(
            0.0,
            100.0 - agent.load_percentage,
        )

        breakdown.performance_score = (
            agent.metrics.success_rate
        )

        breakdown.confidence_score = (
            agent.metrics.confidence_score
        )

        breakdown.quality_score = (
            agent.metrics.quality_score
        )

        breakdown.priority_score = (
            self._priority_score(
                agent.priority
            )
        )

        breakdown.hierarchy_score = (
            self._hierarchy_score(
                agent
            )
        )

        breakdown.preferred_agent_score = (
            100.0
            if agent.agent_id
            in criteria.preferred_agent_ids
            else 0.0
        )

        weights = self._strategy_weights(
            criteria.strategy
        )

        breakdown.total_score = sum(
            getattr(
                breakdown,
                field_name,
            ) * weight
            for field_name, weight in weights.items()
        )

        self._build_reasons(
            agent=agent,
            criteria=criteria,
            breakdown=breakdown,
            reasons=reasons,
        )

        return AgentSelectionResult(
            agent=agent,
            score=breakdown.total_score,
            breakdown=breakdown,
            reasons=reasons,
        )

    def _build_reasons(
        self,
        agent: AgentProfile,
        criteria: AgentSelectionCriteria,
        breakdown: AgentScoreBreakdown,
        reasons: List[str],
    ) -> None:
        if criteria.required_capabilities:
            reasons.append(
                "Cumple todas las capacidades requeridas."
            )

        if criteria.required_tools:
            reasons.append(
                "Dispone de todas las herramientas requeridas."
            )

        if criteria.required_permissions:
            reasons.append(
                "Posee todos los permisos requeridos."
            )

        if (
            criteria.preferred_department
            and agent.department.lower()
            == criteria.preferred_department.lower()
        ):
            reasons.append(
                "Pertenece al departamento preferido."
            )

        if agent.is_available:
            reasons.append(
                "Está disponible para nuevas tareas."
            )

        if breakdown.load_score >= 80.0:
            reasons.append(
                "Tiene baja carga operativa."
            )

        if agent.metrics.success_rate >= 80.0:
            reasons.append(
                "Presenta una tasa de éxito alta."
            )

        if agent.metrics.quality_score >= 80.0:
            reasons.append(
                "Presenta una calidad histórica alta."
            )

        if agent.metrics.confidence_score >= 80.0:
            reasons.append(
                "Presenta una confianza histórica alta."
            )

        if agent.agent_id in criteria.preferred_agent_ids:
            reasons.append(
                "Fue marcado como agente preferido."
            )

        if not reasons:
            reasons.append(
                "Cumple los criterios mínimos de selección."
            )

    def _capability_score(
        self,
        agent: AgentProfile,
        required: Sequence[str],
    ) -> float:
        if not required:
            return 100.0

        matched = sum(
            1
            for capability in required
            if agent.has_capability(
                capability
            )
        )

        return (
            matched
            / len(required)
        ) * 100.0

    def _tool_score(
        self,
        agent: AgentProfile,
        required: Sequence[str],
    ) -> float:
        if not required:
            return 100.0

        matched = sum(
            1
            for tool_name in required
            if agent.has_tool(
                tool_name
            )
        )

        return (
            matched
            / len(required)
        ) * 100.0

    def _permission_score(
        self,
        agent: AgentProfile,
        required: Sequence[str],
    ) -> float:
        if not required:
            return 100.0

        matched = sum(
            1
            for permission in required
            if agent.has_permission(
                permission
            )
        )

        return (
            matched
            / len(required)
        ) * 100.0

    @staticmethod
    def _department_score(
        agent: AgentProfile,
        preferred_department: Optional[str],
    ) -> float:
        if not preferred_department:
            return 100.0

        if (
            agent.department.lower()
            == preferred_department.lower()
        ):
            return 100.0

        return 0.0

    @staticmethod
    def _priority_score(
        priority: int,
    ) -> float:
        normalized_priority = max(
            0,
            int(priority),
        )

        return max(
            0.0,
            100.0 - float(
                normalized_priority
            ),
        )

    def _hierarchy_score(
        self,
        agent: AgentProfile,
    ) -> float:
        level_rank = self._LEVEL_RANK[
            agent.level
        ]

        authority_rank = self._AUTHORITY_RANK[
            agent.authority
        ]

        max_level = max(
            self._LEVEL_RANK.values()
        )

        max_authority = max(
            self._AUTHORITY_RANK.values()
        )

        level_score = (
            level_rank
            / max_level
        ) * 100.0

        authority_score = (
            authority_rank
            / max_authority
        ) * 100.0

        return (
            level_score * 0.6
            + authority_score * 0.4
        )

    def _strategy_weights(
        self,
        strategy: SelectionStrategy,
    ) -> Dict[str, float]:
        weights: Dict[
            SelectionStrategy,
            Dict[str, float],
        ] = {
            SelectionStrategy.BALANCED: {
                "capability_score": 0.24,
                "tool_score": 0.08,
                "permission_score": 0.08,
                "department_score": 0.08,
                "availability_score": 0.10,
                "load_score": 0.10,
                "performance_score": 0.10,
                "confidence_score": 0.05,
                "quality_score": 0.05,
                "priority_score": 0.05,
                "hierarchy_score": 0.05,
                "preferred_agent_score": 0.02,
            },
            SelectionStrategy.PERFORMANCE: {
                "capability_score": 0.20,
                "tool_score": 0.05,
                "permission_score": 0.05,
                "department_score": 0.05,
                "availability_score": 0.05,
                "load_score": 0.05,
                "performance_score": 0.25,
                "confidence_score": 0.10,
                "quality_score": 0.12,
                "priority_score": 0.03,
                "hierarchy_score": 0.03,
                "preferred_agent_score": 0.02,
            },
            SelectionStrategy.LOWEST_LOAD: {
                "capability_score": 0.20,
                "tool_score": 0.05,
                "permission_score": 0.05,
                "department_score": 0.05,
                "availability_score": 0.15,
                "load_score": 0.30,
                "performance_score": 0.05,
                "confidence_score": 0.03,
                "quality_score": 0.03,
                "priority_score": 0.04,
                "hierarchy_score": 0.03,
                "preferred_agent_score": 0.02,
            },
            SelectionStrategy.PRIORITY: {
                "capability_score": 0.20,
                "tool_score": 0.05,
                "permission_score": 0.05,
                "department_score": 0.05,
                "availability_score": 0.10,
                "load_score": 0.08,
                "performance_score": 0.07,
                "confidence_score": 0.04,
                "quality_score": 0.04,
                "priority_score": 0.25,
                "hierarchy_score": 0.05,
                "preferred_agent_score": 0.02,
            },
            SelectionStrategy.HIERARCHY: {
                "capability_score": 0.20,
                "tool_score": 0.05,
                "permission_score": 0.05,
                "department_score": 0.05,
                "availability_score": 0.08,
                "load_score": 0.07,
                "performance_score": 0.07,
                "confidence_score": 0.05,
                "quality_score": 0.05,
                "priority_score": 0.05,
                "hierarchy_score": 0.26,
                "preferred_agent_score": 0.02,
            },
        }

        return weights[
            strategy
        ]

    def _has_all_capabilities(
        self,
        agent: AgentProfile,
        capabilities: Sequence[str],
    ) -> bool:
        return all(
            agent.has_capability(
                capability
            )
            for capability in capabilities
        )

    def _has_all_tools(
        self,
        agent: AgentProfile,
        tools: Sequence[str],
    ) -> bool:
        return all(
            agent.has_tool(
                tool_name
            )
            for tool_name in tools
        )

    def _has_all_permissions(
        self,
        agent: AgentProfile,
        permissions: Sequence[str],
    ) -> bool:
        return all(
            agent.has_permission(
                permission
            )
            for permission in permissions
        )

    def _meets_level_requirement(
        self,
        agent: AgentProfile,
        minimum_level: Optional[AgentLevel],
    ) -> bool:
        if minimum_level is None:
            return True

        return (
            self._LEVEL_RANK[
                agent.level
            ]
            >= self._LEVEL_RANK[
                minimum_level
            ]
        )

    def _meets_authority_requirement(
        self,
        agent: AgentProfile,
        minimum_authority: Optional[
            AuthorityLevel
        ],
    ) -> bool:
        if minimum_authority is None:
            return True

        return (
            self._AUTHORITY_RANK[
                agent.authority
            ]
            >= self._AUTHORITY_RANK[
                minimum_authority
            ]
        )
