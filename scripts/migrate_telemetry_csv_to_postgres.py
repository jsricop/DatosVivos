"""Migrate `data/telemetry/queries.csv` → Postgres `queries` + `dataset_usage`.

ADR-014: activamos Postgres como BD productiva. Este script es one-shot
(idempotente vía UNIQUE constraint en `timestamp_iso, question`).

Uso:
    DATABASE_URL=postgresql://dv:...@localhost:5432/datosvivos \\
        python -m scripts.migrate_telemetry_csv_to_postgres

Tras correrlo, `ai_engine/telemetry.py` queda en modo dual-write y los nuevos
registros llegan automáticamente a Postgres además del CSV.
"""

from __future__ import annotations

import csv
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import psycopg

log = logging.getLogger("migrate_telemetry")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CSV_PATH = Path(os.getenv("TELEMETRY_CSV_PATH", "data/telemetry/queries.csv"))
DATABASE_URL = os.getenv("DATABASE_URL")


def _parse_datasets(raw: str) -> list[str]:
    """`a|b|c` → `['a', 'b', 'c']`. Vacío si raw es None o ''."""
    if not raw:
        return []
    return [s for s in raw.split("|") if s]


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"true", "1", "yes"}


def _parse_int(raw: str) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _parse_float(raw: str) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _parse_ts(raw: str) -> datetime | None:
    if not raw:
        return None
    # Acepta tanto `2026-05-21T10:00:00+00:00` como `2026-05-21T10:00:00Z`.
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def main() -> int:
    if not DATABASE_URL:
        log.error("DATABASE_URL no definida. Aborto.")
        return 2

    if not CSV_PATH.exists():
        log.warning("No existe %s — nada que migrar.", CSV_PATH)
        return 0

    inserted = 0
    skipped = 0
    failed = 0

    with psycopg.connect(DATABASE_URL, autocommit=False) as conn, CSV_PATH.open(
        "r", encoding="utf-8"
    ) as fh:
        reader = csv.DictReader(fh)
        run_id = None
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO etl_runs (script_name, datasets_total)
                VALUES (%s, 0) RETURNING run_id
                """,
                ("migrate_telemetry_csv",),
            )
            row = cur.fetchone()
            assert row is not None
            run_id = row[0]

        for record in reader:
            try:
                ts = _parse_ts(record.get("timestamp_iso", ""))
                question = (record.get("question") or "").strip()
                if not ts or not question:
                    skipped += 1
                    continue
                datasets = _parse_datasets(record.get("datasets_used", ""))
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO queries (
                            timestamp_iso, question, intent, datasets_used,
                            soql_executed, rows_count, censored_count,
                            elapsed_s, had_statistics
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (timestamp_iso, question) DO NOTHING
                        RETURNING id
                        """,
                        (
                            ts,
                            question,
                            (record.get("intent") or "").strip() or None,
                            datasets,
                            (record.get("soql_executed") or "").strip() or None,
                            _parse_int(record.get("rows_count", "")),
                            _parse_int(record.get("censored_count", "")),
                            _parse_float(record.get("elapsed_s", "")),
                            _parse_bool(record.get("had_statistics", "")),
                        ),
                    )
                    new_row = cur.fetchone()
                    if new_row is None:
                        skipped += 1
                        continue
                    query_id = new_row[0]
                    if datasets:
                        cur.executemany(
                            "INSERT INTO dataset_usage (dataset_id, query_id, created_at) VALUES (%s, %s, %s)",
                            [(d, query_id, ts) for d in datasets],
                        )
                    inserted += 1
            except Exception as exc:  # noqa: BLE001
                log.exception("Fallo en fila %s: %s", record.get("timestamp_iso"), exc)
                failed += 1
                conn.rollback()
                continue

        # Cierre del run.
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE etl_runs SET
                    finished_at = NOW(),
                    datasets_total = %s,
                    datasets_succeeded = %s,
                    datasets_failed = %s
                WHERE run_id = %s
                """,
                (inserted + skipped + failed, inserted, failed, run_id),
            )
        conn.commit()

    log.info(
        "Migración terminada — insertadas=%d, skipped(dups o inválidas)=%d, failed=%d",
        inserted,
        skipped,
        failed,
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
