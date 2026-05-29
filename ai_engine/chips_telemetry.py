"""Telemetría liviana para los endpoints de Hito 1 (chips).

Diseño: best-effort. Si la inserción falla, NO debe afectar la respuesta
al usuario — registramos un log.warning y seguimos. La idea es observar,
no bloquear.

Uso (desde los handlers):

    from ai_engine.chips_telemetry import emit_event

    t0 = time.time()
    ... ejecutar ...
    emit_event(
        endpoint="execute", dataset_id=req.dataset_id, tipo=req.tipo,
        elapsed_ms=int((time.time()-t0)*1000), row_count=...,
        soql_chars=len(soql), error=None,
    )

Privacidad: el query NL no se almacena literal — solo su sha1 (40 chars).
Suficiente para deduplicar y para detectar queries recurrentes que
fallan, sin revelar el texto del ciudadano en logs.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

import psycopg

log = logging.getLogger(__name__)


def _hash_query(text: str) -> str | None:
    if not text:
        return None
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def emit_event(
    *,
    endpoint: str,
    dataset_id: str | None = None,
    tipo: str | None = None,
    source_type: str | None = None,
    source_portal: str | None = None,
    elapsed_ms: int | None = None,
    row_count: int | None = None,
    soql_chars: int | None = None,
    error: str | None = None,
    hallucinated: int | None = None,
    nl_query: str | None = None,
    chips_picked: int | None = None,
) -> None:
    """Inserta una fila en `chips_telemetry`. Best-effort.

    Cualquier excepción se loggea como warning y se descarta — la
    telemetría NUNCA debe romper el flujo del usuario.
    """
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return
    try:
        with psycopg.connect(dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chips_telemetry (
                        endpoint, dataset_id, tipo, source_type, source_portal,
                        elapsed_ms, row_count, soql_chars, error, hallucinated,
                        nl_query_hash, chips_picked
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        endpoint, dataset_id, tipo, source_type, source_portal,
                        elapsed_ms, row_count, soql_chars,
                        error[:500] if error else None,
                        hallucinated, _hash_query(nl_query) if nl_query else None,
                        chips_picked,
                    ),
                )
    except Exception as exc:  # noqa: BLE001
        log.warning("chips_telemetry insert falló: %s", exc)
