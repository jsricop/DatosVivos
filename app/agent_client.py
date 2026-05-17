"""Cliente de la app Streamlit hacia el motor de IA.

Envuelve `ai_engine.Analyzer` para que las páginas Streamlit puedan invocarlo
sin lidiar con async ni con la composición de dependencias.

Diseño:
- `AgentClient()` se construye una vez por sesión Streamlit (usar `st.cache_resource`).
- `ask(question)` es sync wrapper sobre `Analyzer.analyze()` async — Streamlit
  no expone un event loop al script, así que envolvemos en `asyncio.run`
  (cada llamada arranca y cierra su propio loop).
- Selección de backend vía env (`LLM_BACKEND=ollama|mock|anthropic`) vía
  `ai_engine.llm_backend.get_backend()`.
"""

from __future__ import annotations

import asyncio
import logging

from ai_engine.analyzer import AnalysisResult, Analyzer
from ai_engine.intent_classifier import IntentClassifier
from ai_engine.llm_backend import get_backend
from ai_engine.vector_index import VectorIndex

log = logging.getLogger(__name__)


class AgentClient:
    """Wrapper sync sobre `ai_engine.Analyzer` para la UI Streamlit."""

    def __init__(
        self,
        analyzer: Analyzer | None = None,
        *,
        top_k_datasets: int = 5,
    ) -> None:
        if analyzer is None:
            analyzer = Analyzer(
                vector_index=VectorIndex.load(),
                intent_classifier=IntentClassifier(),
                llm_backend=get_backend(),
                top_k_datasets=top_k_datasets,
            )
        self.analyzer = analyzer

    def ask(self, question: str) -> AnalysisResult:
        """Sync wrapper: ejecuta `Analyzer.analyze()` en un asyncio loop nuevo.

        Streamlit corre el script en su propio thread sin event loop activo, así
        que `asyncio.run` es el patrón correcto aquí. No usar dentro de otro
        loop (no aplica en Streamlit, pero documentarlo evita confusión).
        """
        return asyncio.run(self.analyzer.analyze(question))
