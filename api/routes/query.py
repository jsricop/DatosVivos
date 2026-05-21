"""POST /api/v1/query — orquesta el Analyzer y stream-ea eventos SSE.

Contrato de eventos (ADR-013):
    intent          {intent, confidence}
    dataset_hits    {datasets: [...]}
    soql            {soql}
    rows            {count, columns, preview}
    citations       {citations: [...]}
    narrative_chunk {text}
    error           {code, message}
    done            {elapsed_s}

Diseño:
- El Analyzer corre `analyze()` completo y luego emitimos los eventos en orden.
  No streameamos token a token todavía (Ollama lo permite, pero el
  validador anti-alucinación trabaja sobre la narrativa completa). Iteración
  futura: streaming verdadero cuando reescriba el validador.
- Si el Analyzer no se puede cargar (sin índice vectorial, sin red para el
  modelo de embeddings, etc.), emitimos `error` + `done` para que el cliente
  reciba retroalimentación clara y no se quede esperando.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import asdict
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from ai_engine.analyzer import AnalysisResult, Analyzer
from ai_engine.dashboard_spec_generator import DashboardSpecGenerator
from ai_engine.intent_classifier import IntentClassifier
from ai_engine.llm_backend import get_backend
from ai_engine.telemetry import log_query
from ai_engine.vector_index import VectorIndex
from api.models.schemas import QueryRequest

router = APIRouter()
log = logging.getLogger(__name__)


_analyzer: Analyzer | None = None
_analyzer_error: str | None = None
_analyzer_lock = asyncio.Lock()
_dashboard_generator: DashboardSpecGenerator | None = None


def _get_dashboard_generator() -> DashboardSpecGenerator:
    """Lazy-instancia el generador. Reutiliza el LLM backend del entorno."""
    global _dashboard_generator
    if _dashboard_generator is None:
        _dashboard_generator = DashboardSpecGenerator(llm=get_backend())
    return _dashboard_generator


async def _get_analyzer() -> tuple[Analyzer | None, str | None]:
    """Lazy-load del Analyzer. Si falla, retorna (None, mensaje)."""
    global _analyzer, _analyzer_error
    if _analyzer is not None:
        return _analyzer, None
    if _analyzer_error is not None:
        return None, _analyzer_error
    async with _analyzer_lock:
        if _analyzer is not None:
            return _analyzer, None
        if _analyzer_error is not None:
            return None, _analyzer_error
        try:
            analyzer = await asyncio.to_thread(_build_analyzer)
            _analyzer = analyzer
            return analyzer, None
        except Exception as exc:  # noqa: BLE001
            log.exception("No pude cargar Analyzer: %s", exc)
            _analyzer_error = (
                f"Motor IA no inicializado: {exc}. "
                "Verifica que el índice vectorial exista (scripts/build_index.py) "
                "y que el backend LLM esté disponible (LLM_BACKEND env)."
            )
            return None, _analyzer_error


def _build_analyzer() -> Analyzer:
    return Analyzer(
        vector_index=VectorIndex.load(),
        intent_classifier=IntentClassifier(),
        llm_backend=get_backend(),
    )


def _sse(event: str, data: dict | list | str) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=_json_default)
    return f"event: {event}\ndata: {payload}\n\n"


def _json_default(obj: object) -> object:
    """Pydantic / dataclass-safe JSON serializer fallback."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()  # type: ignore[attr-defined]
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


@router.post("/query")
async def query(body: dict) -> StreamingResponse:
    """SSE streaming sobre Analyzer.analyze()."""
    try:
        request = QueryRequest.model_validate(body)
    except ValidationError as exc:
        # Convertimos a stream para que el cliente reciba 'error' + 'done' incluso
        # ante request inválida, en lugar de un 422 que rompe la UX SSE.
        # Capturamos los errores en una variable local porque `exc` no sobrevive
        # al cierre de este `except` cuando el async generator se ejecuta después.
        errors_payload = exc.errors()

        async def err_stream() -> AsyncIterator[str]:
            yield _sse(
                "error",
                {
                    "code": "invalid_request",
                    "message": "Pregunta vacía o inválida",
                    "detail": errors_payload,
                },
            )
            yield _sse("done", {"elapsed_s": 0.0})

        return StreamingResponse(err_stream(), media_type="text/event-stream")

    return StreamingResponse(_event_stream(request), media_type="text/event-stream")


async def _event_stream(request: QueryRequest) -> AsyncIterator[str]:
    started = time.perf_counter()
    analyzer, err = await _get_analyzer()

    if analyzer is None:
        log.warning("Analyzer no disponible: %s", err)
        yield _sse(
            "error",
            {
                "code": "analyzer_unavailable",
                "message": err or "Motor IA no inicializado.",
            },
        )
        yield _sse("done", {"elapsed_s": round(time.perf_counter() - started, 2)})
        return

    try:
        result: AnalysisResult = await analyzer.analyze(request.q)
    except Exception as exc:  # noqa: BLE001
        log.exception("Analyzer.analyze falló: %s", exc)
        yield _sse(
            "error",
            {"code": "analyzer_error", "message": str(exc)},
        )
        yield _sse("done", {"elapsed_s": round(time.perf_counter() - started, 2)})
        return

    # 1) Intent
    yield _sse("intent", {"intent": result.intent, "confidence": 1.0})

    # 2) Dataset hits — usamos dataset_references como fuente de verdad para el frontend.
    yield _sse(
        "dataset_hits",
        {
            "datasets": [
                {
                    "id": ref.id,
                    "name": ref.name,
                    "entity": ref.entity,
                    "score": 1.0,
                }
                for ref in result.dataset_references
            ]
        },
    )

    # 3) SoQL (si hay)
    if result.soql_executed:
        yield _sse("soql", {"soql": result.soql_executed})

    # 4) Rows (preview limitado)
    if result.rows:
        columns = list(result.rows[0].keys()) if result.rows else []
        yield _sse(
            "rows",
            {
                "count": len(result.rows),
                "columns": columns,
                "preview": result.rows[:50],
            },
        )

    # 5) Dashboard spec — lo lanzamos en paralelo con los siguientes eventos.
    #    Si el LLM tarda, no bloqueamos la narrativa.
    dashboard_task: asyncio.Task[Any] | None = None
    if result.rows and result.dataset_references:
        try:
            generator = _get_dashboard_generator()
            top_name = (
                result.dataset_references[0].name if result.dataset_references else "Dataset"
            )
            dashboard_task = asyncio.create_task(
                generator.generate(
                    question=request.q,
                    intent=result.intent,
                    dataset_name=top_name,
                    columns=list(result.rows[0].keys()) if result.rows else [],
                    rows=result.rows,
                    stats=result.statistics,
                    geo_ctx=result.geo_context,
                )
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("No pude lanzar DashboardSpecGenerator: %s", exc)
            dashboard_task = None

    # 6) Citations
    if result.dataset_references:
        yield _sse(
            "citations",
            {
                "citations": [
                    {
                        "index": i + 1,
                        "id": ref.id,
                        "name": ref.name,
                        "entity": ref.entity,
                        "url": ref.url,
                        "api_url": ref.api_url,
                    }
                    for i, ref in enumerate(result.dataset_references)
                ]
            },
        )

    # 7) Narrative — en chunks para sensación de streaming.
    narrative = result.narrative or ""
    chunk_size = 240
    for i in range(0, len(narrative), chunk_size):
        chunk = narrative[i : i + chunk_size]
        yield _sse("narrative_chunk", {"text": chunk})
        # Pequeña pausa para evitar buffering agresivo y permitir cancelación.
        await asyncio.sleep(0)

    # 8) Esperar dashboard_spec si quedó pendiente (con timeout duro).
    # 90s para producción con LLM 14B compartido con la narrativa: ambos tasks
    # compiten por el mismo backend Ollama secuencialmente y el spec
    # generation puede arrancar realmente solo tras emitir narrative_chunks.
    if dashboard_task is not None:
        try:
            spec = await asyncio.wait_for(dashboard_task, timeout=90.0)
            if spec is not None:
                yield _sse("dashboard_spec", spec.model_dump(mode="json"))
            else:
                log.info("DashboardSpec generator devolvió None (válido para datasets escalares)")
        except asyncio.TimeoutError:
            log.warning("DashboardSpec timeout (>90s) — sigo sin dashboard")
        except Exception as exc:  # noqa: BLE001
            log.warning("DashboardSpec falló: %s", exc, exc_info=True)

    elapsed = round(time.perf_counter() - started, 2)

    # 7) Telemetría best-effort.
    try:
        await asyncio.to_thread(
            log_query,
            question=request.q,
            intent=result.intent,
            datasets_used=result.datasets_used or [],
            soql_executed=result.soql_executed,
            rows_count=len(result.rows),
            censored_count=0,
            elapsed_s=elapsed,
            had_statistics=result.statistics is not None,
        )
    except Exception:  # noqa: BLE001
        pass

    yield _sse("done", {"elapsed_s": elapsed})


# Necesario para que tests puedan importar sin ejecutar; el `asdict` import
# se queda como utility por si se requiere serializar dataclasses extra.
_ = asdict
_ = os.environ  # silenciar lint si os no se usa más
