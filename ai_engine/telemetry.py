"""Telemetría de consultas — dual-write CSV + PostgreSQL (ADR-014).

Diseño:
- **CSV append-only en `data/telemetry/queries.csv`**: fuente de verdad
  ligera, sin dependencias. Mantiene el flujo legacy de Beta-1.
- **PostgreSQL** (opcional, activado si `DATABASE_URL` está definido):
  inserta cada consulta en `queries` + `dataset_usage` para alimentar el
  dashboard PowerBI ejecutivo en `/tablero`.
- **Best-effort**: si Postgres no responde, el CSV sigue siendo la fuente.
  La telemetría nunca tumba el endpoint `/api/v1/query`.

Lazy import de `psycopg`: si el paquete no está instalado o `DATABASE_URL`
falta, la persistencia Postgres queda en NO-OP sin warnings ruidosos.
"""

from __future__ import annotations

import csv
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

log = logging.getLogger(__name__)

TELEMETRY_PATH = Path("data/telemetry/queries.csv")
_FIELDS = (
    "timestamp_iso",
    "question",
    "intent",
    "datasets_used",
    "soql_executed",
    "rows_count",
    "censored_count",
    "elapsed_s",
    "had_statistics",
)

# ----------------------------------------------------------------------
# Conexión Postgres lazy (singleton best-effort)
# ----------------------------------------------------------------------

_pool_lock = Lock()
_pool = None
_pool_disabled = False  # se enciende si la conexión falla irrecuperablemente


def _get_pool():
    """Devuelve un `psycopg_pool.ConnectionPool` o None si no aplica."""
    global _pool, _pool_disabled
    if _pool is not None or _pool_disabled:
        return _pool
    url = os.getenv("DATABASE_URL")
    if not url:
        return None
    with _pool_lock:
        if _pool is not None or _pool_disabled:
            return _pool
        try:
            # Import perezoso: si psycopg no está, la API queda funcional
            # sin telemetría Postgres.
            from psycopg_pool import ConnectionPool  # type: ignore

            _pool = ConnectionPool(
                conninfo=url,
                min_size=1,
                max_size=int(os.getenv("DATABASE_POOL_MAX", "4")),
                open=True,
                kwargs={"autocommit": True},
                name="datosvivos-telemetry",
            )
            log.info("telemetry: Postgres pool iniciado (max_size=%s)", os.getenv("DATABASE_POOL_MAX", "4"))
        except Exception as exc:  # noqa: BLE001
            _pool_disabled = True
            log.warning("telemetry: no pude iniciar pool Postgres (%s) — solo CSV", exc)
            return None
    return _pool


def log_query(
    *,
    question: str,
    intent: str,
    datasets_used: list[str],
    soql_executed: str | None,
    rows_count: int,
    censored_count: int,
    elapsed_s: float,
    had_statistics: bool,
) -> None:
    """Appendea un registro de consulta a CSV y (si está activo) Postgres.

    Best-effort en ambos canales — ni un fallo de IO ni de BD tumba el flujo.
    """
    ts_now = datetime.now(timezone.utc)
    timestamp_iso = ts_now.isoformat(timespec="seconds")
    question_clean = (question or "").replace("\n", " ").strip()
    datasets_clean = list(datasets_used or [])
    soql_clean = (soql_executed or "").replace("\n", " ") if soql_executed else None
    elapsed_round = round(float(elapsed_s), 2)
    rows_int = int(rows_count)
    censored_int = int(censored_count)
    had_stats = bool(had_statistics)

    # --- CSV (siempre intenta) ---
    try:
        TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        is_new = not TELEMETRY_PATH.exists()
        record: dict[str, Any] = {
            "timestamp_iso": timestamp_iso,
            "question": question_clean,
            "intent": intent,
            "datasets_used": "|".join(datasets_clean),
            "soql_executed": soql_clean or "",
            "rows_count": rows_int,
            "censored_count": censored_int,
            "elapsed_s": elapsed_round,
            "had_statistics": had_stats,
        }
        with TELEMETRY_PATH.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=_FIELDS)
            if is_new:
                writer.writeheader()
            writer.writerow(record)
    except Exception as exc:  # noqa: BLE001
        log.warning("telemetry CSV write falló (%s)", exc)

    # --- Postgres (best-effort) ---
    pool = _get_pool()
    if pool is None:
        return
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO queries (
                    timestamp_iso, question, intent, datasets_used,
                    soql_executed, rows_count, censored_count, elapsed_s, had_statistics
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (timestamp_iso, question) DO NOTHING
                RETURNING id
                """,
                (
                    ts_now,
                    question_clean,
                    intent,
                    datasets_clean,
                    soql_clean,
                    rows_int,
                    censored_int,
                    elapsed_round,
                    had_stats,
                ),
            )
            row = cur.fetchone()
            if row is None:
                return  # duplicado por constraint, no insertamos usage
            query_id = row[0]
            if datasets_clean:
                cur.executemany(
                    "INSERT INTO dataset_usage (dataset_id, query_id, created_at) VALUES (%s, %s, %s)",
                    [(d, query_id, ts_now) for d in datasets_clean],
                )
    except Exception as exc:  # noqa: BLE001
        log.warning("telemetry Postgres write falló (%s) — sigo con CSV", exc)
