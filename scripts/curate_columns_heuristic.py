#!/usr/bin/env python3
"""Curación heurística masiva de columnas Socrata (D.6.c).

Para todos los datasets no-admin del catálogo:
1. Llama Socrata Metadata API → obtiene lista de columnas con data_type
   y description.
2. Clasifica cada columna con `ai_engine.column_classifier.classify_column`.
3. UPSERT en `dataset_columns_curated`.

Diseño:
- Concurrencia controlada (sem=5) para no saturar Socrata.
- Batch INSERT cada N datasets para no abrir 100K transacciones.
- Idempotente: re-corrigible. UPSERT por (dataset_id, col_name).
- `--limit N` para correr sample antes de full run.
- `--only-missing` para procesar solo datasets no curados todavía.

Uso:
    docker compose exec -T api python scripts/curate_columns_heuristic.py
    docker compose exec -T api python scripts/curate_columns_heuristic.py --limit 100
    docker compose exec -T api python scripts/curate_columns_heuristic.py --only-missing
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections import Counter
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_engine.column_classifier import classify_column  # noqa: E402
from mcp_server.socrata.metadata_client import MetadataClient  # noqa: E402


CONCURRENCY = 5
BATCH_SIZE = 50  # commit cada N datasets


def fetch_datasets(conn, only_missing: bool, limit: int | None) -> list[dict]:
    where_extra = ""
    if only_missing:
        where_extra = (
            " AND NOT EXISTS ("
            "  SELECT 1 FROM dataset_columns_curated dcc "
            "  WHERE dcc.dataset_id = d.dataset_id"
            ")"
        )
    sql = f"""
        SELECT d.dataset_id, d.view_count
        FROM datasets d
        WHERE (d.quality_flag IS NULL OR d.quality_flag = 'ok')
          {where_extra}
        ORDER BY d.view_count DESC NULLS LAST
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql)
        return cur.fetchall()


async def fetch_columns(client: MetadataClient, dataset_id: str) -> list[dict] | None:
    try:
        meta = await client.get(dataset_id)
    except Exception:
        return None
    return meta.get("columns") or []


def classify_dataset_columns(dataset_id: str, columns: list[dict]) -> list[tuple]:
    """Devuelve filas listas para INSERT: (dataset_id, col_name, dtype, desc, type, subtype, conf, reason)."""
    rows: list[tuple] = []
    for c in columns:
        col_name = c.get("fieldName") or c.get("field_name") or c.get("name")
        if not col_name:
            continue
        dtype = c.get("dataTypeName") or c.get("data_type")
        desc = (c.get("description") or "").strip() or None
        result = classify_column(col_name, dtype, desc)
        rows.append((
            dataset_id,
            col_name,
            dtype,
            desc,
            result.semantic_type,
            result.semantic_subtype,
            result.confidence,
            result.reason,
        ))
    return rows


def upsert_batch(conn, rows: list[tuple]) -> int:
    if not rows:
        return 0
    sql = """
        INSERT INTO dataset_columns_curated
          (dataset_id, col_name, socrata_data_type, socrata_description,
           semantic_type, semantic_subtype, confidence, reason, curated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (dataset_id, col_name) DO UPDATE
        SET socrata_data_type = EXCLUDED.socrata_data_type,
            socrata_description = EXCLUDED.socrata_description,
            semantic_type = EXCLUDED.semantic_type,
            semantic_subtype = EXCLUDED.semantic_subtype,
            confidence = EXCLUDED.confidence,
            reason = EXCLUDED.reason,
            curated_at = NOW()
    """
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
        return cur.rowcount


async def main_async(args) -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL no definida", file=sys.stderr)
        return 2

    with psycopg.connect(url) as conn:
        datasets = fetch_datasets(conn, args.only_missing, args.limit)
    if not datasets:
        print("No hay datasets para procesar.")
        return 0

    print(f"Procesando {len(datasets):,} datasets (concurrency={CONCURRENCY})…", file=sys.stderr)

    client = MetadataClient()
    sem = asyncio.Semaphore(CONCURRENCY)

    # Counters globales
    by_type: Counter = Counter()
    by_conf: Counter = Counter()
    n_failed = 0
    n_processed = 0
    n_cols_total = 0
    batch_rows: list[tuple] = []

    async def _bounded(ds):
        async with sem:
            cols = await fetch_columns(client, ds["dataset_id"])
            return ds["dataset_id"], cols

    with psycopg.connect(url) as conn_write:
        for chunk_start in range(0, len(datasets), BATCH_SIZE):
            chunk = datasets[chunk_start : chunk_start + BATCH_SIZE]
            results = await asyncio.gather(*[_bounded(d) for d in chunk])
            for dsid, cols in results:
                if cols is None:
                    n_failed += 1
                    continue
                rows = classify_dataset_columns(dsid, cols)
                for r in rows:
                    by_type[r[4]] += 1
                    by_conf[r[6]] += 1
                n_cols_total += len(rows)
                batch_rows.extend(rows)
            n_processed += len(chunk)
            if batch_rows:
                upsert_batch(conn_write, batch_rows)
                conn_write.commit()
                batch_rows.clear()
            if n_processed % (BATCH_SIZE * 4) == 0:
                print(f"  procesados {n_processed:,}/{len(datasets):,}", file=sys.stderr)

    print(f"\n=== Resumen ===")
    print(f"Datasets procesados:   {n_processed:,}")
    print(f"Datasets con error:    {n_failed}")
    print(f"Columnas clasificadas: {n_cols_total:,}")
    print(f"\nPor tipo semántico:")
    for t, n in by_type.most_common():
        pct = 100 * n / n_cols_total if n_cols_total else 0
        print(f"  {t:<12} {n:>7,}  ({pct:.1f}%)")
    print(f"\nPor confidence:")
    for c, n in by_conf.most_common():
        pct = 100 * n / n_cols_total if n_cols_total else 0
        print(f"  {c:<10} {n:>7,}  ({pct:.1f}%)")

    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only-missing", action="store_true",
                        help="Skip datasets que ya están en dataset_columns_curated")
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
