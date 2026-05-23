#!/usr/bin/env python3
"""Auditoría de metadata de columnas Socrata (D.6.a).

Decide cuánto pueden las heurísticas + description de Socrata clasificar
columnas antes de invocar LLM. Genera reporte:

- % de datasets con al menos una columna con `description` poblada útil
- # promedio de columnas por dataset
- # promedio de columnas con description útil
- Distribución de `dataType` (Number, Text, Calendar date, Point, etc.)
- Sample de columnas tipo geo/fecha/metrica para verificar que la
  heurística por nombre + dataType funciona

Uso:
    DATABASE_URL=... python scripts/audit_columns_metadata.py [--limit N]

Por default toma los top-200 datasets no-admin por view_count.
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

from mcp_server.socrata.metadata_client import MetadataClient  # noqa: E402


def _useful_description(desc: str | None) -> bool:
    """Heurística: description es "útil" si tiene ≥10 caracteres y no es genérica."""
    if not desc:
        return False
    desc = desc.strip()
    if len(desc) < 10:
        return False
    GENERIC = {
        "variable",
        "campo",
        "column",
        "ver descripción del dataset",
        "n/a",
        "na",
        "-",
        "ver dataset",
    }
    if desc.lower() in GENERIC:
        return False
    return True


async def fetch_datasets_to_audit(conn, limit: int) -> list[dict]:
    """Top-N datasets no-admin por view_count."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT dataset_id, name, view_count
            FROM datasets
            WHERE quality_flag IS NULL OR quality_flag = 'ok'
            ORDER BY view_count DESC NULLS LAST
            LIMIT %s
            """,
            (limit,),
        )
        return cur.fetchall()


async def audit_one(client: MetadataClient, dataset_id: str) -> dict | None:
    """Devuelve estadísticas de un dataset o None si falla."""
    try:
        meta = await client.get(dataset_id)
    except Exception as exc:  # noqa: BLE001
        return {"dataset_id": dataset_id, "error": str(exc)[:80]}

    columns = meta.get("columns") or []
    n_cols = len(columns)
    n_with_desc = sum(1 for c in columns if _useful_description(c.get("description")))
    data_types = Counter(c.get("dataTypeName") or c.get("data_type") or "?" for c in columns)
    sample_cols = [
        {
            "name": c.get("fieldName") or c.get("field_name") or c.get("name"),
            "data_type": c.get("dataTypeName") or c.get("data_type"),
            "description": (c.get("description") or "")[:80],
        }
        for c in columns[:5]
    ]
    return {
        "dataset_id": dataset_id,
        "n_cols": n_cols,
        "n_with_desc": n_with_desc,
        "data_types": dict(data_types),
        "sample_cols": sample_cols,
    }


async def main_async(limit: int) -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL no definida", file=sys.stderr)
        return 2

    with psycopg.connect(url) as conn:
        datasets = await fetch_datasets_to_audit(conn, limit)
    print(f"Auditando {len(datasets)} datasets no-admin (top por view_count)...", file=sys.stderr)

    client = MetadataClient()
    sem = asyncio.Semaphore(5)  # paralelismo controlado

    async def _bounded(ds):
        async with sem:
            return await audit_one(client, ds["dataset_id"])

    results = await asyncio.gather(*[_bounded(d) for d in datasets])

    errored = [r for r in results if r and "error" in r]
    valid = [r for r in results if r and "error" not in r]

    print(f"\nDatasets auditados: {len(valid)} OK, {len(errored)} errored")
    if errored:
        print(f"Errors sample: {[r['error'] for r in errored[:3]]}")
    if not valid:
        return 1

    total_cols = sum(r["n_cols"] for r in valid)
    total_with_desc = sum(r["n_with_desc"] for r in valid)
    datasets_with_any_desc = sum(1 for r in valid if r["n_with_desc"] > 0)

    print(f"\nColumnas totales:           {total_cols:,}")
    print(f"Promedio cols/dataset:      {total_cols / len(valid):.1f}")
    print(f"Columnas con description útil: {total_with_desc:,} ({100*total_with_desc/total_cols:.1f}%)")
    print(f"Datasets con ≥1 col descrita:  {datasets_with_any_desc}/{len(valid)} ({100*datasets_with_any_desc/len(valid):.1f}%)")

    # Distribución data_types
    all_types: Counter = Counter()
    for r in valid:
        for dt, n in r["data_types"].items():
            all_types[dt] += n
    print(f"\nDistribución data_types (top 10):")
    for dt, n in all_types.most_common(10):
        print(f"  {dt:<20} {n:>6,} ({100*n/total_cols:.1f}%)")

    # Sample de columnas con/sin description
    print(f"\nSample de columnas con description útil:")
    shown = 0
    for r in valid:
        for c in r["sample_cols"]:
            if c["description"]:
                print(f"  [{r['dataset_id']}] {c['name']:<25} ({c['data_type']:<10}) — {c['description']}")
                shown += 1
                if shown >= 8:
                    break
        if shown >= 8:
            break

    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()
    return asyncio.run(main_async(args.limit))


if __name__ == "__main__":
    sys.exit(main())
