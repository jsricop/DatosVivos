"""Audit `dataset_columns_curated` contra Discovery `resource.columns_*`.

Para cada dataset: compara el conjunto local de (col_name, datatype) contra
el conjunto que viene en el payload Discovery. Reporta:
- datasets con count distinto.
- datasets con nombres distintos (set diff).
- datasets con datatypes mal asignados.

No modifica nada.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

import psycopg

from mcp_server.socrata.discovery_client import DiscoveryClient


async def main(out_path: str, dsn: str) -> None:
    # 1. local: {dataset_id: [(col_name, datatype), ...]}
    local: dict[str, list[tuple[str, str | None]]] = defaultdict(list)
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT dataset_id, col_name, socrata_data_type "
                "FROM dataset_columns_curated"
            )
            for ds_id, name, dt in cur.fetchall():
                local[ds_id].append((name, dt))
    print(f"Local: {len(local)} datasets con columnas curadas; "
          f"{sum(len(v) for v in local.values())} filas total", file=sys.stderr)

    # 2. iterar Discovery, comparar
    client = DiscoveryClient()
    offset = 0
    PAGE = 1000
    same_count = 0
    same_names = 0
    same_datatypes = 0
    only_socrata = 0
    only_local = 0
    total_native = 0
    federated_skipped = 0
    missing_in_local = 0
    examples_count_diff = []
    examples_name_diff = []
    examples_datatype_diff = []

    while True:
        results = await client.search(query=None, limit=PAGE, offset=offset)
        if not results:
            break
        for r in results:
            res = r.get("resource") or {}
            ds_id = res.get("id")
            if not ds_id:
                continue
            if res.get("type") == "federated_href":
                federated_skipped += 1
                continue
            total_native += 1
            # Discovery expone dos paralelos:
            #   columns_name       → display name humano ("Código DIVIPOLA")
            #   columns_field_name → ident técnico snake_case ("codigo_divipola")
            # Local guarda field_name, así que comparamos contra ese.
            soc_names = [n for n in (res.get("columns_field_name") or []) if n]
            soc_datatypes = res.get("columns_datatype") or []
            soc_pairs = list(zip(soc_names, soc_datatypes + [None] * len(soc_names)))
            loc_pairs = local.get(ds_id, [])
            if not loc_pairs:
                missing_in_local += 1
                continue
            loc_names = {n for n, _ in loc_pairs}
            socn = set(soc_names)
            loc_dt = {n: dt for n, dt in loc_pairs}
            soc_dt = {n: dt for n, dt in soc_pairs}
            # 1) cuenta de columnas
            if len(loc_pairs) == len(soc_pairs):
                same_count += 1
            elif len(examples_count_diff) < 10:
                examples_count_diff.append(
                    {"ds": ds_id, "local": len(loc_pairs), "socrata": len(soc_pairs)}
                )
            # 2) names
            if loc_names == socn:
                same_names += 1
            else:
                only_socrata += len(socn - loc_names)
                only_local += len(loc_names - socn)
                if len(examples_name_diff) < 10:
                    examples_name_diff.append({
                        "ds": ds_id,
                        "only_socrata": sorted(socn - loc_names)[:5],
                        "only_local": sorted(loc_names - socn)[:5],
                    })
            # 3) datatypes (solo donde el name coincide en ambos)
            shared = loc_names & socn
            mismatches = [
                (n, loc_dt.get(n), soc_dt.get(n))
                for n in shared
                if (loc_dt.get(n) or "").lower() != (soc_dt.get(n) or "").lower()
            ]
            if not mismatches:
                same_datatypes += 1
            elif len(examples_datatype_diff) < 10:
                examples_datatype_diff.append(
                    {"ds": ds_id, "diffs": mismatches[:5]}
                )
        offset += len(results)
        print(f"  procesados {offset}", file=sys.stderr)
        await asyncio.sleep(0.1)

    # 3. reporte
    lines = []
    lines.append(f"# Auditoría columns_curated vs Socrata Discovery")
    lines.append(f"\nGenerado: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Datasets nativos en Discovery: {total_native}")
    lines.append(f"- Federados saltados: {federated_skipped}")
    lines.append(f"- Datasets nativos sin filas en local: {missing_in_local}")
    if total_native:
        pct_c = same_count / total_native * 100
        pct_n = same_names / total_native * 100
        pct_d = same_datatypes / total_native * 100
        lines.append(f"\n| métrica | n | % |\n|---|---:|---:|")
        lines.append(f"| nativos con mismo COUNT de columnas | {same_count} | {pct_c:.1f}% |")
        lines.append(f"| nativos con mismo SET de nombres | {same_names} | {pct_n:.1f}% |")
        lines.append(f"| nativos con DATATYPES coincidentes | {same_datatypes} | {pct_d:.1f}% |")
    lines.append(f"\n- Columnas solo en Socrata (no en local): {only_socrata}")
    lines.append(f"- Columnas solo en local (no en Socrata): {only_local}")

    if examples_count_diff:
        lines.append("\n## Ejemplos: diff en COUNT de columnas")
        for e in examples_count_diff:
            lines.append(f"- `{e['ds']}` · local={e['local']} · socrata={e['socrata']}")
    if examples_name_diff:
        lines.append("\n## Ejemplos: diff en NOMBRES de columnas")
        for e in examples_name_diff:
            lines.append(f"- `{e['ds']}` · only_socrata={e['only_socrata']} · only_local={e['only_local']}")
    if examples_datatype_diff:
        lines.append("\n## Ejemplos: diff en DATATYPES")
        for e in examples_datatype_diff:
            diffs = "; ".join(f"`{n}`: local=`{l}` socrata=`{s}`" for n, l, s in e["diffs"])
            lines.append(f"- `{e['ds']}` · {diffs}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Reporte escrito en {out_path}", file=sys.stderr)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--dsn", default=None)
    args = p.parse_args()
    dsn = args.dsn or os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR: DATABASE_URL requerido", file=sys.stderr)
        sys.exit(1)
    asyncio.run(main(args.output, dsn))
