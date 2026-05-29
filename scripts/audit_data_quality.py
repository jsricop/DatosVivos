"""audit_data_quality.py — Validación columna×columna del catálogo contra Socrata.

Recorre el catálogo Discovery del dominio (paginado), compara cada columna del
snapshot local (`_audit_snapshot`) contra el campo equivalente del payload, y
emite un reporte markdown con counts agregados + ejemplos de mismatches.

Modo de uso (dentro del contenedor api):
    python -m scripts.audit_data_quality --output /app/data/data_quality_<fecha>.md

No modifica `datasets`. Solo lee del snapshot y de Socrata.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import unicodedata
from datetime import datetime, timezone
from typing import Any, Callable

import psycopg

from mcp_server.socrata.discovery_client import DiscoveryClient


# ---------------------------------------------------------------------------
# Comparadores
# ---------------------------------------------------------------------------


def _nfc(s: Any) -> str | None:
    if s is None:
        return None
    return unicodedata.normalize("NFC", str(s).strip()) or None


def cmp_str(local: Any, source: Any) -> bool:
    a, b = _nfc(local), _nfc(source)
    return a == b


def cmp_str_truncated(local: Any, source: Any, n: int = 2000) -> bool:
    """description: el ETL trunca a 2000; comparar contra source[:n]."""
    a = _nfc(local)
    b = _nfc(source)
    if b is not None:
        b = b[:n]
    return a == b


def cmp_int_exact(local: Any, source: Any) -> bool:
    if local is None and source is None:
        return True
    if local is None or source is None:
        return False
    return int(local) == int(source)


def cmp_int_tol(local: Any, source: Any, tol_pct: float = 5.0) -> bool:
    """Engagement: tolera Δ% < tol_pct por lag de Discovery vs Views.

    Diferencias pequeñas son cache lag, no bug. Diferencias grandes indican
    extracción incorrecta.
    """
    if local is None and source is None:
        return True
    if local is None or source is None:
        return False
    a, b = int(local), int(source)
    if a == b:
        return True
    if max(a, b) == 0:
        return False
    return abs(a - b) / max(a, b) * 100 < tol_pct


def cmp_iso(local: Any, source: Any) -> bool:
    """TIMESTAMPTZ local vs ISO string Socrata — exact seconds."""
    if local is None and source is None:
        return True
    if local is None or source is None:
        return False
    if isinstance(local, str):
        ld = datetime.fromisoformat(local.replace("Z", "+00:00"))
    else:
        ld = local
    if isinstance(source, str):
        sd = datetime.fromisoformat(source.replace("Z", "+00:00"))
    else:
        sd = source
    if ld.tzinfo is None:
        ld = ld.replace(tzinfo=timezone.utc)
    if sd.tzinfo is None:
        sd = sd.replace(tzinfo=timezone.utc)
    return abs((ld - sd).total_seconds()) < 1


# ---------------------------------------------------------------------------
# Extracción del payload Discovery — replica el ETL Y la rama federada
# ---------------------------------------------------------------------------


def from_discovery(result: dict[str, Any]) -> dict[str, Any]:
    """Construye el dict ESPERADO desde el payload Discovery."""
    res = result.get("resource") or {}
    cls = result.get("classification") or {}
    mta = result.get("metadata") or {}
    pv = res.get("page_views") or {}
    is_federated = res.get("type") == "federated_href"
    dm = {}
    for item in cls.get("domain_metadata") or []:
        k = item.get("key")
        v = item.get("value")
        if k is not None:
            dm[k] = v

    nat_frec = dm.get("Información-de-Datos_Frecuencia-de-Actualización")
    nat_cob = dm.get("Información-de-Datos_Cobertura-Geográfica")
    nat_sec = dm.get("Información-de-la-Entidad_Sector")
    fed_frec = dm.get("Common-Core_Update-Frequency")
    fed_pub = dm.get("Common-Core_Publisher")
    fed_thm = dm.get("Common-Core_Theme")
    fed_lic = dm.get("Common-Core_License")
    fed_spat = dm.get("Common-Core_Spatial")

    return {
        "dataset_id": res.get("id"),
        "name": res.get("name"),
        "entity_raw": res.get("attribution") or (fed_pub if is_federated else None),
        "category": cls.get("domain_category") or (fed_thm if is_federated else None),
        "description": res.get("description") or "",
        "data_updated_at": res.get("data_updated_at"),
        "metadata_updated_at": res.get("metadata_updated_at"),
        "publication_date": res.get("publication_date"),
        "created_at_socrata": res.get("createdAt"),
        "update_frequency": nat_frec or (fed_frec if is_federated else None),
        "cobertura_geografica": nat_cob or (fed_spat if is_federated else None),
        "sector": nat_sec,  # federados DCAT no tienen sector
        "provenance": res.get("provenance"),
        "license": mta.get("license") or (fed_lic if is_federated else None),
        "download_count": res.get("download_count"),
        "page_views_total": pv.get("page_views_total"),
        "view_count": pv.get("page_views_total"),  # alias
        "page_views_last_week": pv.get("page_views_last_week"),
        "page_views_last_month": pv.get("page_views_last_month"),
        "is_federated": is_federated,
        "type_socrata": res.get("type"),
    }


# Columna local → comparador
CMP: dict[str, Callable[[Any, Any], bool]] = {
    "name": cmp_str,
    "entity_raw": cmp_str,
    "category": cmp_str,
    "description": cmp_str_truncated,
    "data_updated_at": cmp_iso,
    "metadata_updated_at": cmp_iso,
    "publication_date": cmp_iso,
    "created_at_socrata": cmp_iso,
    "update_frequency": cmp_str,
    "cobertura_geografica": cmp_str,
    "sector": cmp_str,
    "provenance": cmp_str,
    "license": cmp_str,
    "download_count": cmp_int_tol,
    "page_views_total": cmp_int_tol,
    "view_count": cmp_int_tol,
    "page_views_last_week": cmp_int_tol,
    "page_views_last_month": cmp_int_tol,
}

COLS = list(CMP.keys())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _new_bucket() -> dict[str, Any]:
    return {c: {"n": 0, "ok": 0, "mismatch": 0, "examples": []} for c in COLS}


def _record(bucket: dict, col: str, ok: bool, ds_id: str, loc: Any, src: Any) -> None:
    bucket[col]["n"] += 1
    if ok:
        bucket[col]["ok"] += 1
    else:
        bucket[col]["mismatch"] += 1
        if len(bucket[col]["examples"]) < 10:
            bucket[col]["examples"].append(
                {"ds": ds_id, "local": str(loc)[:120], "socrata": str(src)[:120]}
            )


async def main(out_path: str, dsn: str) -> None:
    # 1) Cargar snapshot local en memoria.
    snapshot: dict[str, dict[str, Any]] = {}
    cols_sql = ", ".join(COLS)
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT dataset_id, {cols_sql} FROM _audit_snapshot")
            colnames = [d.name for d in cur.description]
            for row in cur.fetchall():
                d = dict(zip(colnames, row))
                snapshot[d["dataset_id"]] = d
    print(f"Snapshot cargado: {len(snapshot)} datasets", file=sys.stderr)

    # 2) Iterar Discovery del dominio entero.
    natives = _new_bucket()
    federated = _new_bucket()
    not_in_snapshot = 0
    not_in_socrata = set(snapshot.keys())  # restamos a medida que vemos

    client = DiscoveryClient()
    offset = 0
    PAGE = 1000
    total_seen = 0
    while True:
        results = await client.search(query=None, limit=PAGE, offset=offset)
        if not results:
            break
        for r in results:
            exp = from_discovery(r)
            ds_id = exp["dataset_id"]
            if not ds_id:
                continue
            total_seen += 1
            loc = snapshot.get(ds_id)
            if not loc:
                not_in_snapshot += 1
                continue
            not_in_socrata.discard(ds_id)
            bucket = federated if exp["is_federated"] else natives
            for col, cmp in CMP.items():
                _record(bucket, col, cmp(loc.get(col), exp.get(col)), ds_id,
                        loc.get(col), exp.get(col))
        offset += len(results)
        print(f"  procesados {offset}", file=sys.stderr)
        await asyncio.sleep(0.1)
    print(f"Total Discovery: {total_seen}, fed-only-in-snapshot: {len(not_in_socrata)}, "
          f"in-socrata-not-in-snapshot: {not_in_snapshot}", file=sys.stderr)

    # 3) Reporte markdown.
    def _fmt_bucket(b: dict, title: str) -> str:
        lines = [f"### {title}\n"]
        lines.append("| columna | comparados | match | mismatch | %match |")
        lines.append("|---|---:|---:|---:|---:|")
        for col in COLS:
            row = b[col]
            n = row["n"]
            pct = (row["ok"] / n * 100) if n else 0.0
            lines.append(f"| {col} | {n} | {row['ok']} | {row['mismatch']} | {pct:.1f}% |")
        lines.append("")
        # ejemplos
        for col in COLS:
            ex = b[col]["examples"]
            if not ex:
                continue
            lines.append(f"#### {col} — ejemplos de mismatch (máx 10)")
            for e in ex:
                lines.append(f"- `{e['ds']}` · local=`{e['local']}` · socrata=`{e['socrata']}`")
            lines.append("")
        return "\n".join(lines)

    body = []
    body.append(f"# Auditoría de calidad — catálogo Socrata vs `_audit_snapshot`")
    body.append(f"\nGenerado: {datetime.now(timezone.utc).isoformat()}")
    body.append(f"\n- Snapshot local: {len(snapshot)} datasets")
    body.append(f"- Datasets en Discovery (dominio entero): {total_seen}")
    body.append(f"- En snapshot pero no en Discovery: {len(not_in_socrata)}")
    body.append(f"- En Discovery pero no en snapshot: {not_in_snapshot}")
    body.append(f"- Datasets nativos procesados: {natives['name']['n']}")
    body.append(f"- Datasets federated_href procesados: {federated['name']['n']}\n")
    body.append("## Nativos\n")
    body.append(_fmt_bucket(natives, "Match por columna — nativos"))
    body.append("## Federados (`federated_href`)\n")
    body.append(_fmt_bucket(federated, "Match por columna — federados"))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(body))
    print(f"Reporte escrito en {out_path}", file=sys.stderr)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, help="Ruta del .md de salida")
    p.add_argument("--dsn", default=None, help="DSN Postgres (default: env DATABASE_URL)")
    args = p.parse_args()
    dsn = args.dsn or os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR: DSN no provisto (use --dsn o env DATABASE_URL)", file=sys.stderr)
        sys.exit(1)
    asyncio.run(main(args.output, dsn))
