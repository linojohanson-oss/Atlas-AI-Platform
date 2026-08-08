from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from atlas.agents.base_agent import BaseAgent
from atlas.kernel.llm_manager import LLMManager
from atlas.kernel.tool_manager import ToolManager


class ResearchAgent(BaseAgent):
    """
    Atlas AI - Research Agent V2.1.

    Investiga usando WebResearchTool cuando ToolManager esta disponible,
    genera automaticamente varias consultas y luego sintetiza la evidencia
    mediante el LLM configurado en Atlas.
    """

    name = "research-agent"

    description = (
        "Agente especializado en investigacion estructurada, "
        "analisis de informacion, comparacion de evidencia "
        "y elaboracion de conclusiones."
    )

    capabilities = [
        "general_reasoning",
        "research",
        "information_analysis",
        "web_research",
    ]

    def __init__(
        self,
        llm_manager: LLMManager,
        tool_manager: Optional[ToolManager] = None,
    ) -> None:
        self.llm_manager = llm_manager
        self.tool_manager = tool_manager

    def execute(
        self,
        task: str,
    ) -> Dict[str, Any]:
        normalized_task = str(task).strip()

        if not normalized_task:
            raise ValueError(
                "La tarea no puede estar vacia."
            )

        research_topic = self._extract_research_topic(
            normalized_task
        )

        search_queries = self._generate_search_queries(
            research_topic
        )

        web_evidence = self._collect_web_evidence(
            research_topic=research_topic,
            search_queries=search_queries,
        )

        evidence_prompt = self._build_evidence_prompt(
            task=normalized_task,
            research_topic=research_topic,
            evidence=web_evidence,
        )

        llm_response = self.llm_manager.generate(
            system_prompt=(
                "Sos el Research Agent de Atlas AI. "
                "Tu responsabilidad es investigar problemas, "
                "analizar informacion, comparar evidencia, "
                "detectar contradicciones y producir conclusiones "
                "claras, fundamentadas y ordenadas. "
                "Usa primero la evidencia web provista cuando exista. "
                "No inventes datos, fechas, cifras ni fuentes. "
                "No atribuyas una cifra, proyeccion o afirmacion a una "
                "institucion salvo que esa institucion y ese dato aparezcan "
                "juntos en la misma fuente citada. "
                "Si dos fuentes discrepan, describi la discrepancia sin "
                "intentar reconciliarla mediante suposiciones. "
                "Diferencia hechos encontrados de inferencias propias. "
                "Cita las fuentes usando [1], [2], etc. cuando haya "
                "evidencia externa. "
                "Indica supuestos, limitaciones y nivel de certeza "
                "cuando corresponda."
            ),
            user_prompt=evidence_prompt,
        )

        return {
            "agent": self.name,
            "status": llm_response["status"],
            "task": normalized_task,
            "research_topic": research_topic,
            "search_queries": search_queries,
            "output": llm_response["content"],
            "provider": llm_response["provider"],
            "model": llm_response["model"],
            "web_research": web_evidence,
            "metadata": llm_response.get(
                "metadata",
                {},
            ),
        }

    def _collect_web_evidence(
        self,
        research_topic: str,
        search_queries: List[str],
    ) -> Dict[str, Any]:
        """
        Ejecuta WebResearchTool sin derribar el workflow
        si Internet, DDGS o ToolManager fallan.
        """

        if self.tool_manager is None:
            return {
                "tool": "web-research",
                "status": "unavailable",
                "query": research_topic,
                "query_count": 0,
                "source_count": 0,
                "sources": [],
                "errors": [
                    {
                        "error": (
                            "ResearchAgent no recibio ToolManager."
                        )
                    }
                ],
            }

        try:
            return self.tool_manager.execute(
                tool_name="web-research",
                query=search_queries[0],
                queries=search_queries[1:],
                max_results=5,
                max_sources=12,
            )
        except Exception as exc:
            return {
                "tool": "web-research",
                "status": "degraded",
                "query": research_topic,
                "query_count": len(search_queries),
                "source_count": 0,
                "sources": [],
                "errors": [
                    {
                        "error": str(exc),
                    }
                ],
            }

    @classmethod
    def _extract_research_topic(
        cls,
        task: str,
    ) -> str:
        """
        Intenta separar la solicitud original del contexto
        acumulado por el WorkflowEngine.
        """

        text = str(task).strip()

        marker_patterns = [
            r"SOLICITUD PRINCIPAL\s*:\s*(.+?)(?:\n\n|\Z)",
            r"REQUEST\s*:\s*(.+?)(?:\n\n|\Z)",
            r"TAREA PRINCIPAL\s*:\s*(.+?)(?:\n\n|\Z)",
            r"OBJETIVO\s*:\s*(.+?)(?:\n\n|\Z)",
        ]

        for pattern in marker_patterns:
            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )

            if match:
                candidate = cls._clean_topic(
                    match.group(1)
                )

                if candidate:
                    return candidate

        # Fallback: usa la primera porcion significativa.
        first_block = re.split(
            r"\n\s*\n",
            text,
            maxsplit=1,
        )[0]

        return cls._clean_topic(
            first_block[:700]
        )

    @staticmethod
    def _clean_topic(
        value: str,
    ) -> str:
        text = re.sub(
            r"\s+",
            " ",
            str(value),
        ).strip()

        return text[:500]

    @classmethod
    def _generate_search_queries(
        cls,
        topic: str,
    ) -> List[str]:
        """
        Genera hasta cuatro consultas automaticamente.

        Incluye especializacion economica cuando el objetivo
        contiene indicadores macroeconomicos; en otros casos
        utiliza consultas generales de investigacion.
        """

        normalized = topic.casefold()

        economic_keywords = (
            "economia",
            "economy",
            "inflacion",
            "inflation",
            "crecimiento",
            "growth",
            "reservas",
            "reserves",
            "deuda",
            "debt",
            "fiscal",
            "empleo",
            "employment",
            "tipo de cambio",
            "exchange rate",
        )

        if any(
            keyword in normalized
            for keyword in economic_keywords
        ):
            subject = cls._economic_subject(topic)

            candidates = [
                (
                    f"{subject} growth inflation economy "
                    "IMF forecast outlook"
                ),
                (
                    f"{subject} central bank reserves "
                    "exchange rate debt"
                ),
                (
                    f"{subject} employment investment "
                    "consumption outlook"
                ),
                (
                    f"{subject} fiscal balance external "
                    "sector exports"
                ),
            ]
        else:
            candidates = [
                f"{topic} latest official sources",
                f"{topic} current data evidence",
                f"{topic} risks outlook analysis",
                f"{topic} report statistics research",
            ]

        result: List[str] = []
        seen = set()

        for candidate in candidates:
            query = re.sub(
                r"\s+",
                " ",
                candidate,
            ).strip()

            key = query.casefold()

            if not query or key in seen:
                continue

            seen.add(key)
            result.append(query[:300])

        return result[:4]

    @staticmethod
    def _economic_subject(
        topic: str,
    ) -> str:
        """
        Extrae una cabecera corta para consultas economicas.
        Conserva especialmente pais/entidad y horizonte temporal.
        """

        words = re.findall(
            r"[A-Za-zÀ-ÿ0-9]+",
            topic,
        )

        if not words:
            return topic[:120]

        stop = {
            "analiza",
            "analizar",
            "explica",
            "evalua",
            "evaluar",
            "perspectivas",
            "expectativas",
            "economia",
            "economy",
            "para",
            "del",
            "de",
            "la",
            "el",
            "los",
            "las",
            "proximo",
            "proxima",
            "ano",
            "año",
            "incluyendo",
            "incluye",
            "considerando",
            "considera",
            "sobre",
            "perspectiva",
            "tambien",
            "también",
        }

        selected = []

        for word in words:
            if word.casefold() in stop:
                continue

            selected.append(word)

            if len(selected) >= 6:
                break

        return " ".join(selected) or topic[:120]

    @staticmethod
    def _build_evidence_prompt(
        task: str,
        research_topic: str,
        evidence: Dict[str, Any],
    ) -> str:
        sources = evidence.get(
            "sources",
            [],
        )

        lines = [
            "TAREA COMPLETA DEL WORKFLOW:",
            task,
            "",
            "TEMA CENTRAL DE INVESTIGACION:",
            research_topic,
            "",
            "EVIDENCIA WEB DISPONIBLE:",
        ]

        if not sources:
            lines.extend(
                [
                    (
                        "No se obtuvieron fuentes externas suficientes "
                        "en esta ejecucion."
                    ),
                    "",
                    (
                        "Continua con el contexto disponible, pero declara "
                        "explicitamente esta limitacion y evita presentar "
                        "datos actuales no verificados como hechos."
                    ),
                ]
            )

            return "\n".join(lines)

        for source in sources:
            rank = source.get("rank", "-")
            title = source.get("title", "")
            url = source.get("url", "")
            domain = source.get("domain", "")
            snippet = source.get("snippet", "")
            authority = source.get(
                "authority_score",
                "-",
            )
            relevance = source.get(
                "relevance_score",
                "-",
            )

            lines.extend(
                [
                    f"[{rank}] {title}",
                    f"Fuente: {domain}",
                    f"URL: {url}",
                    (
                        "Autoridad/Relevancia: "
                        f"{authority}/{relevance}"
                    ),
                    f"Extracto: {snippet}",
                    "",
                ]
            )

        lines.extend(
            [
                "INSTRUCCIONES DE ANALISIS:",
                (
                    "1. Responde la tarea usando prioritariamente "
                    "la evidencia encontrada."
                ),
                (
                    "2. Contrasta coincidencias y contradicciones "
                    "entre las fuentes."
                ),
                (
                    "3. Cita cada afirmacion factual relevante con "
                    "[1], [2], etc."
                ),
                (
                    "4. No inventes cifras ni atribuciones que no "
                    "aparezcan en la evidencia."
                ),
                (
                    "5. Separa claramente hechos, inferencias, "
                    "riesgos y limitaciones."
                ),
                (
                    "6. Nunca atribuyas una cifra o proyeccion a una "
                    "institucion si la misma fuente no contiene juntos "
                    "el nombre de la institucion y ese dato."
                ),
                (
                    "7. Si las fuentes ofrecen cifras distintas, informa "
                    "la discrepancia; no inventes una explicacion para "
                    "hacerlas coincidir."
                ),
            ]
        )

        return "\n".join(lines)
