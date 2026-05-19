"""Telemetría mínima para beta — append a CSV local.

Diseño:
- Sin DB ni dependencias extra (la fase 1 de beta no la requiere).
- Append-only CSV en `data/telemetry/queries.csv`.
- Schema fijo; si quieres agregar columnas, hazlo aquí y borra el archivo.
- Errores nunca tumban el flujo principal — la telemetría es best-effort.

Cuando lleguen suficientes datos, se migra a PostgreSQL (schema en `db/init.sql`).
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
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
    """Appendea un registro de consulta. Best-effort, no levanta excepciones."""
    try:
        TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        is_new = not TELEMETRY_PATH.exists()
        record: dict[str, Any] = {
            "timestamp_iso": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "question": question.replace("\n", " ").strip(),
            "intent": intent,
            "datasets_used": "|".join(datasets_used or []),
            "soql_executed": (soql_executed or "").replace("\n", " "),
            "rows_count": int(rows_count),
            "censored_count": int(censored_count),
            "elapsed_s": round(float(elapsed_s), 2),
            "had_statistics": bool(had_statistics),
        }
        with TELEMETRY_PATH.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=_FIELDS)
            if is_new:
                writer.writeheader()
            writer.writerow(record)
    except Exception as exc:  # noqa: BLE001 — telemetría no debe romper el flujo
        log.warning("telemetry.log_query falló (%s) — sigo sin loggear", exc)
