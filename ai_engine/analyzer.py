"""Orquestador end-to-end: pregunta NL → análisis estructurado.

Pipeline:
1. `IntentClassifier` categoriza la pregunta (search, descriptive, comparative, ...)
2. `VectorIndex` recupera datasets candidatos por matching semántico
3. Para intent ≠ search: `QueryGenerator` produce SoQL contra el dataset top
   y `SodaClient` lo ejecuta (integración pendiente para Sprint 3 FASE E)
4. `LLMBackend` genera narrativa en español sobre los resultados

Diseño:
- Inyección de dependencias en `__init__` — facilita testing con mocks
- Retorna `AnalysisResult` dataclass — interfaz estable para Streamlit (Sprint 4)
- Si vector_index está vacío, devuelve respuesta con `datasets_used=[]`
  y narrativa explicando la limitación

Sprint 3 FASE D (esta iteración): cubre intent=search end-to-end.
Sprint 3 FASE E: extiende a otros intents vía QueryGenerator + SodaClient.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ai_engine.intent_classifier import IntentClassifier
from ai_engine.llm_backend import LLMBackend
from ai_engine.vector_index import VectorIndex

log = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Resultado estructurado del análisis. Estable para Streamlit/Power BI."""

    question: str
    intent: str
    datasets_used: list[str] = field(default_factory=list)
    soql_executed: str | None = None
    rows: list[dict[str, Any]] = field(default_factory=list)
    narrative: str = ""

    def __getitem__(self, key: str):
        # Soporte dict-like para tests que usan result["intent"], etc.
        return getattr(self, key)

    def get(self, key: str, default=None):
        return getattr(self, key, default)


class Analyzer:
    """Orquesta el motor de IA: intent → recuperación → generación → narrativa."""

    def __init__(
        self,
        vector_index: VectorIndex,
        intent_classifier: IntentClassifier,
        llm_backend: LLMBackend,
        *,
        top_k_datasets: int = 5,
    ) -> None:
        self.vector_index = vector_index
        self.intent_classifier = intent_classifier
        self.llm = llm_backend
        self.top_k_datasets = top_k_datasets

    async def analyze(self, question: str) -> AnalysisResult:
        """Pipeline completo. Devuelve resultado estructurado."""
        question = (question or "").strip()
        if not question:
            return AnalysisResult(
                question="",
                intent="search",
                narrative="Pregunta vacía — provee una consulta en lenguaje natural.",
            )

        intent = self.intent_classifier.classify(question)
        log.info("Intent: %s | Pregunta: %s", intent, question[:80])

        # Recuperar datasets candidatos para CUALQUIER intent — son la base del contexto
        hits = self.vector_index.search(question, k=self.top_k_datasets)
        datasets_used = [h.id for h in hits]

        if not hits:
            narrative = await self._narrate_no_matches(question, intent)
            return AnalysisResult(
                question=question, intent=intent, datasets_used=[], narrative=narrative
            )

        if intent == "search":
            # Para SEARCH, el output ES la lista de datasets + narrativa resumen
            narrative = await self._narrate_search_results(question, hits)
            return AnalysisResult(
                question=question,
                intent=intent,
                datasets_used=datasets_used,
                narrative=narrative,
            )

        # Para intents distintos a search: por ahora narrativa basada en metadatos.
        # Sprint 3 FASE E completa este branch con QueryGenerator + SodaClient.
        narrative = await self._narrate_non_search_placeholder(question, intent, hits)
        return AnalysisResult(
            question=question,
            intent=intent,
            datasets_used=datasets_used,
            narrative=narrative,
        )

    async def _narrate_search_results(self, question: str, hits: list) -> str:
        """LLM resume los datasets recuperados como respuesta a la pregunta."""
        items = "\n".join(f"- {h.id}: {h.name} (entidad: {h.entity or 'N/D'})" for h in hits[:5])
        prompt = (
            f"Eres un asistente experto en datos abiertos de Colombia. "
            f"Un ciudadano preguntó: {question!r}\n"
            f"Estos son los datasets más relevantes encontrados en datos.gov.co:\n"
            f"{items}\n\n"
            f"Responde brevemente en español (3-5 frases) indicando qué datasets "
            f"pueden servir al ciudadano y por qué. No inventes información."
        )
        return await self.llm.generate(prompt, max_tokens=300)

    async def _narrate_no_matches(self, question: str, intent: str) -> str:
        prompt = (
            f"El ciudadano preguntó {question!r} (intent={intent}) pero no se "
            f"encontraron datasets relevantes en datos.gov.co. Responde "
            f"brevemente en español sugiriendo cómo reformular o qué keywords "
            f"intentar."
        )
        return await self.llm.generate(prompt, max_tokens=200)

    async def _narrate_non_search_placeholder(self, question: str, intent: str, hits: list) -> str:
        """Fallback temporal hasta Sprint 3 FASE E (QueryGenerator integrado)."""
        top = hits[0]
        prompt = (
            f"Pregunta: {question!r} (tipo: {intent}). El dataset más relevante "
            f"es {top.id} ({top.name}). Indica en una frase qué información "
            f"contiene este dataset y sugiere al ciudadano consultarlo "
            f"directamente. Español, máximo 3 frases."
        )
        return await self.llm.generate(prompt, max_tokens=200)
