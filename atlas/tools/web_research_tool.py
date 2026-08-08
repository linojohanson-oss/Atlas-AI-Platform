from __future__ import annotations

from datetime import datetime
import re
import unicodedata
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

from ddgs import DDGS

from atlas.tools.base_tool import BaseTool


class WebResearchTool(BaseTool):
    """
    Atlas AI - Web Research Tool V2.2.

    Ejecuta multiples consultas, combina resultados, elimina duplicados,
    detecta el tema central de investigacion y prioriza fuentes relevantes
    y de mayor autoridad.
    """

    name = "web-research"
    description = (
        "Investiga informacion actual en la web mediante multiples consultas "
        "y devuelve evidencia estructurada, relevante y priorizada."
    )
    version = "2.2.0"

    AUTHORITY_DOMAINS = {
        "imf.org": 100,
        "worldbank.org": 98,
        "bcra.gob.ar": 98,
        "indec.gob.ar": 98,
        "argentina.gob.ar": 95,
        "oecd.org": 95,
        "iadb.org": 95,
        "cepal.org": 95,
        "un.org": 90,
        "reuters.com": 88,
        "apnews.com": 86,
        "bbc.com": 84,
        "piie.com": 84,
    }

    LOW_VALUE_DOMAINS = {
        "youtube.com",
        "youtu.be",
        "t.me",
        "telegram.me",
        "facebook.com",
        "instagram.com",
        "pinterest.com",
        "tiktok.com",
    }

    STOPWORDS = {
        "a", "al", "and", "are", "as", "at", "by", "de", "del", "el", "en",
        "for", "from", "in", "la", "las", "los", "of", "on", "or", "para",
        "por", "the", "to", "un", "una", "y",
    }

    GENERIC_TERMS = {
        "economy", "economic", "economia", "growth", "crecimiento",
        "inflation", "inflacion", "outlook", "perspectivas", "forecast",
        "projection", "projections", "investment", "inversion", "employment",
        "empleo", "consumption", "consumo", "fiscal", "balance", "external",
        "sector", "exports", "export", "reserves", "reservas", "debt", "deuda",
        "exchange", "rate", "central", "bank", "imf", "fmi",
    }

    def execute(
        self,
        query: str,
        max_results: int = 5,
        queries: Optional[List[str]] = None,
        max_sources: int = 12,
        min_relevance: int = 20,
        max_per_domain: int = 3,
    ) -> Dict[str, Any]:
        normalized_query = str(query).strip()

        if not normalized_query:
            raise ValueError("La consulta web no puede estar vacia.")

        try:
            per_query = max(1, min(int(max_results), 10))
        except (TypeError, ValueError):
            per_query = 5

        try:
            source_limit = max(1, min(int(max_sources), 30))
        except (TypeError, ValueError):
            source_limit = 12

        try:
            relevance_floor = max(0, min(int(min_relevance), 100))
        except (TypeError, ValueError):
            relevance_floor = 20

        try:
            domain_limit = max(1, min(int(max_per_domain), 10))
        except (TypeError, ValueError):
            domain_limit = 3

        search_queries = self._normalize_queries(
            normalized_query,
            queries,
        )

        anchors = self._detect_anchor_terms(search_queries)

        collected: List[Dict[str, Any]] = []
        errors: List[Dict[str, str]] = []

        for search_query in search_queries:
            query_terms = self._terms(search_query)

            try:
                raw_results = DDGS().text(
                    search_query,
                    max_results=per_query,
                )

                for item in raw_results or []:
                    if not isinstance(item, dict):
                        continue

                    title = str(item.get("title", "")).strip()
                    url = str(
                        item.get("href")
                        or item.get("url")
                        or ""
                    ).strip()
                    snippet = str(
                        item.get("body")
                        or item.get("snippet")
                        or ""
                    ).strip()

                    if not title and not url and not snippet:
                        continue

                    domain = self._domain(url)

                    if self._is_low_value_domain(domain):
                        continue

                    authority_score = self._authority_score(domain)
                    relevance_score = self._relevance_score(
                        query_terms=query_terms,
                        title=title,
                        snippet=snippet,
                        domain=domain,
                    )

                    anchor_score = self._anchor_score(
                        anchors=anchors,
                        title=title,
                        snippet=snippet,
                        url=url,
                    )

                    # Si detectamos un tema/entidad central, el resultado debe
                    # mencionarlo. Esto evita resultados sobre India, Europa,
                    # Canada, etc. en investigaciones sobre Argentina.
                    if anchors and anchor_score == 0:
                        continue

                    keep = (
                        authority_score >= 85
                        or relevance_score >= relevance_floor
                    )

                    if not keep:
                        continue

                    final_score = (
                        authority_score * 0.50
                        + relevance_score * 0.35
                        + anchor_score * 0.15
                    )

                    collected.append(
                        {
                            "title": title,
                            "url": url,
                            "domain": domain,
                            "snippet": snippet,
                            "search_query": search_query,
                            "authority_score": authority_score,
                            "relevance_score": relevance_score,
                            "anchor_score": anchor_score,
                            "final_score": round(final_score, 2),
                        }
                    )

            except Exception as exc:
                errors.append(
                    {
                        "query": search_query,
                        "error": str(exc),
                    }
                )

        deduplicated = self._deduplicate(collected)

        ranked = sorted(
            deduplicated,
            key=lambda item: (
                item.get("final_score", 0),
                item.get("authority_score", 0),
                item.get("relevance_score", 0),
            ),
            reverse=True,
        )

        diversified = self._limit_by_domain(
            ranked,
            max_per_domain=domain_limit,
            limit=source_limit,
        )

        for rank, item in enumerate(diversified, start=1):
            item["rank"] = rank

        if diversified:
            status = "completed"
        elif errors:
            status = "degraded"
        else:
            status = "no-results"

        return {
            "tool": self.name,
            "version": self.version,
            "status": status,
            "query": normalized_query,
            "queries": search_queries,
            "query_count": len(search_queries),
            "anchor_terms": sorted(anchors),
            "source_count": len(diversified),
            "sources": diversified,
            "errors": errors,
            "filters": {
                "min_relevance": relevance_floor,
                "max_per_domain": domain_limit,
            },
            "searched_at": datetime.now().isoformat(),
        }

    @staticmethod
    def _normalize_queries(
        query: str,
        queries: Optional[List[str]],
    ) -> List[str]:
        candidates = [query]

        if queries:
            candidates.extend(queries)

        normalized: List[str] = []
        seen = set()

        for candidate in candidates:
            value = str(candidate).strip()

            if not value:
                continue

            key = value.casefold()

            if key in seen:
                continue

            seen.add(key)
            normalized.append(value)

        return normalized[:6]

    @classmethod
    def _detect_anchor_terms(
        cls,
        queries: List[str],
    ) -> Set[str]:
        """
        Detecta terminos no genericos presentes en todas las consultas.
        En el ejemplo economico actual, detecta automaticamente 'argentina'.
        """

        if not queries:
            return set()

        term_sets = []

        for query in queries:
            terms = {
                term
                for term in cls._terms(query)
                if (
                    not term.isdigit()
                    and term not in cls.GENERIC_TERMS
                    and len(term) >= 4
                )
            }
            term_sets.append(terms)

        if not term_sets:
            return set()

        common = set.intersection(*term_sets)

        # Evita una exigencia excesiva si no existe un tema comun claro.
        return set(list(sorted(common))[:4])

    @staticmethod
    def _domain(url: str) -> str:
        if not url:
            return ""

        try:
            domain = urlparse(url).netloc.lower()
        except Exception:
            return ""

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    def _authority_score(self, domain: str) -> int:
        if not domain:
            return 0

        for trusted_domain, score in self.AUTHORITY_DOMAINS.items():
            if (
                domain == trusted_domain
                or domain.endswith("." + trusted_domain)
            ):
                return score

        if domain.endswith(".gov") or ".gov." in domain:
            return 92

        if domain.endswith(".edu") or ".edu." in domain:
            return 85

        return 50

    def _is_low_value_domain(self, domain: str) -> bool:
        for blocked in self.LOW_VALUE_DOMAINS:
            if domain == blocked or domain.endswith("." + blocked):
                return True
        return False

    @classmethod
    def _terms(cls, text: str) -> Set[str]:
        normalized = cls._normalize_text(text)

        return {
            token
            for token in re.findall(r"[a-z0-9]+", normalized)
            if len(token) >= 3 and token not in cls.STOPWORDS
        }

    @staticmethod
    def _normalize_text(value: str) -> str:
        text = unicodedata.normalize("NFKD", str(value).casefold())

        return "".join(
            char
            for char in text
            if not unicodedata.combining(char)
        )

    @classmethod
    def _relevance_score(
        cls,
        query_terms: Set[str],
        title: str,
        snippet: str,
        domain: str,
    ) -> int:
        if not query_terms:
            return 0

        title_terms = cls._terms(title)
        snippet_terms = cls._terms(snippet)
        domain_terms = cls._terms(domain.replace(".", " "))

        title_overlap = len(query_terms & title_terms)
        snippet_overlap = len(query_terms & snippet_terms)
        domain_overlap = len(query_terms & domain_terms)

        denominator = max(1, len(query_terms))

        weighted = (
            title_overlap * 3.0
            + snippet_overlap * 1.5
            + domain_overlap * 2.0
        )

        return int(
            min(
                100,
                round((weighted / denominator) * 25),
            )
        )

    @classmethod
    def _anchor_score(
        cls,
        anchors: Set[str],
        title: str,
        snippet: str,
        url: str,
    ) -> int:
        if not anchors:
            return 100

        haystack = cls._terms(
            f"{title} {snippet} {url}"
        )

        matched = len(anchors & haystack)

        return int(
            round(
                (matched / max(1, len(anchors))) * 100
            )
        )

    @staticmethod
    def _deduplicate(
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        unique: Dict[str, Dict[str, Any]] = {}

        for source in sources:
            url = str(source.get("url", "")).strip()
            title = str(source.get("title", "")).strip()

            key = url.casefold() if url else title.casefold()

            if not key:
                continue

            existing = unique.get(key)

            if existing is None:
                unique[key] = source
                continue

            if source.get("final_score", 0) > existing.get(
                "final_score",
                0,
            ):
                unique[key] = source

        return list(unique.values())

    @staticmethod
    def _limit_by_domain(
        sources: List[Dict[str, Any]],
        max_per_domain: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        selected: List[Dict[str, Any]] = []
        domain_counts: Dict[str, int] = {}

        for source in sources:
            domain = str(source.get("domain", "")).strip()
            count = domain_counts.get(domain, 0)

            if domain and count >= max_per_domain:
                continue

            selected.append(source)

            if domain:
                domain_counts[domain] = count + 1

            if len(selected) >= limit:
                break

        return selected
