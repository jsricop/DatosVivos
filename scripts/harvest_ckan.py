"""Reto F.5 — Harvester CKAN genérico (Bogotá / Cali / Valle / otros).

Recorre el endpoint `/api/3/action/package_search` del portal indicado,
extrae recursos con `format='CSV'` y los inserta en `datasets` como
`source_type='federated'`, consultables directamente vía DuckDB (F.4
los enruta solo; URLs no-directas las resuelve F.4.2 al query-time).

Portales soportados:
    bogota → datosabiertos.bogota.gov.co        (id prefix: bog-)
    cali   → datos.cali.gov.co                  (id prefix: cal-)
    valle  → datosabiertos.valledelcauca.gov.co (id prefix: val-)

Uso (dentro del contenedor api):
    DATABASE_URL=... python -m scripts.harvest_ckan --portal bogota
    DATABASE_URL=... python -m scripts.harvest_ckan --portal cali --limit 50
    DATABASE_URL=... python -m scripts.harvest_ckan --portal valle --dry-run

Idempotente: UPSERT por dataset_id. Re-correr actualiza metadata.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import urllib.parse
import urllib.request
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

PAGE_SIZE = 100
USER_AGENT = "DatosVivos/F.5-harvester (+https://github.com/jsricop/DatosVivos)"

PORTALS: dict[str, dict[str, str]] = {
    "bogota": {"host": "datosabiertos.bogota.gov.co",        "prefix": "bog-"},
    "cali":   {"host": "datos.cali.gov.co",                  "prefix": "cal-"},
    "valle":  {"host": "datosabiertos.valledelcauca.gov.co", "prefix": "val-"},
}

log = logging.getLogger("harvest_ckan")
DATABASE_URL = os.environ.get("DATABASE_URL")


def _build_dataset_id(resource_id: str, prefix: str) -> str:
    """`<prefix><16hex>` = 20 chars (cabe en VARCHAR(20))."""
    clean = (resource_id or "").replace("-", "")
    return f"{prefix}{clean[:16]}"


def _http_get(url: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _iter_packages(host: str, limit: int | None) -> Iterator[dict[str, Any]]:
    """Genera packages CKAN paginando 100 a la vez."""
    base = f"https://{host}"
    start = 0
    yielded = 0
    while True:
        params = urllib.parse.urlencode({"rows": PAGE_SIZE, "start": start})
        url = f"{base}/api/3/action/package_search?{params}"
        log.info("GET %s", url)
        data = _http_get(url)
        results = (data.get("result") or {}).get("results") or []
        if not results:
            return
        for pkg in results:
            yield pkg
            yielded += 1
            if limit and yielded >= limit:
                return
        start += len(results)
        time.sleep(0.1)


def _pick_csv_resources(pkg: dict[str, Any]) -> list[dict[str, Any]]:
    """Devuelve resources con `format='CSV'` y URL utilizable.

    Para URLs page-style (`/resource/<uuid>` sin `/download/`), las
    aceptamos: el executor F.4.2 las resolverá al query-time vía CKAN
    `resource_show`. Sólo rechazamos URLs vacías.
    """
    out = []
    for r in pkg.get("resources") or []:
        fmt = (r.get("format") or "").upper().strip()
        url = (r.get("url") or "").strip()
        if fmt != "CSV":
            continue
        if not url:
            continue
        out.append(r)
    return out


def _parse_iso(s: str | None):
    if not s:
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _build_row(
    pkg: dict[str, Any], res: dict[str, Any], host: str, prefix: str
) -> dict[str, Any]:
    """Mapea (package, resource) a una fila de `datasets`."""
    res_id = res.get("id") or ""
    dataset_id = _build_dataset_id(res_id, prefix)

    pkg_title = pkg.get("title") or pkg.get("name") or ""
    res_name = (res.get("name") or "").strip()
    # Si el resource tiene nombre distinto al paquete, anexar.
    if res_name and res_name.lower() not in pkg_title.lower():
        name = f"{pkg_title} — {res_name}"
    else:
        name = pkg_title

    org = pkg.get("organization") or {}
    entity_raw = (org.get("title") or "").strip() or None
    groups = pkg.get("groups") or []
    category = (groups[0].get("title") if groups else None) or None

    last_mod = _parse_iso(res.get("last_modified") or pkg.get("metadata_modified"))
    created = _parse_iso(res.get("created") or pkg.get("metadata_created"))

    return {
        "dataset_id": dataset_id,
        "name": name,
        "entity_raw": entity_raw,
        "category": category,
        "description": ((pkg.get("notes") or "")[:2000]) or None,
        "rows_updated_at": last_mod,
        "data_updated_at": last_mod,
        "metadata_updated_at": last_mod,
        "publication_date": created,
        "created_at_socrata": created,
        "provenance": "official",
        "license": pkg.get("license_title") or None,
        "source_type": "federated",
        "source_portal": host,
        "data_url": res.get("url"),
        "data_format": "csv",
        "federated_status": "ok",
        "socrata_url": f"https://{host}/dataset/{pkg.get('name')}",
        "api_url": None,
    }


def _resolve_entity_id(cur: psycopg.Cursor, entity_raw: str | None) -> int | None:
    if not entity_raw:
        return None
    cur.execute(
        """
        SELECT entity_id FROM entities
        WHERE lower(trim(name)) = lower(trim(%s))
        ORDER BY length(name) DESC LIMIT 1
        """,
        (entity_raw,),
    )
    row = cur.fetchone()
    return row["entity_id"] if row else None


_UPSERT_SQL = """
INSERT INTO datasets (
    dataset_id, name, entity_id, entity_raw, category, description,
    rows_updated_at, data_updated_at, metadata_updated_at, publication_date,
    created_at_socrata, provenance, license, source_type, source_portal,
    data_url, data_format, federated_status, socrata_url, api_url,
    last_refreshed_at
) VALUES (
    %(dataset_id)s, %(name)s, %(entity_id)s, %(entity_raw)s, %(category)s,
    %(description)s, %(rows_updated_at)s, %(data_updated_at)s,
    %(metadata_updated_at)s, %(publication_date)s, %(created_at_socrata)s,
    %(provenance)s, %(license)s, %(source_type)s, %(source_portal)s,
    %(data_url)s, %(data_format)s, %(federated_status)s, %(socrata_url)s,
    %(api_url)s, NOW()
)
ON CONFLICT (dataset_id) DO UPDATE SET
    name = EXCLUDED.name,
    entity_id = EXCLUDED.entity_id,
    entity_raw = EXCLUDED.entity_raw,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    rows_updated_at = EXCLUDED.rows_updated_at,
    data_updated_at = EXCLUDED.data_updated_at,
    metadata_updated_at = EXCLUDED.metadata_updated_at,
    license = EXCLUDED.license,
    data_url = EXCLUDED.data_url,
    last_refreshed_at = NOW()
"""


def main(portal_key: str, limit: int | None, dry_run: bool) -> None:
    if not DATABASE_URL:
        log.error("DATABASE_URL no definida")
        sys.exit(1)
    cfg = PORTALS.get(portal_key)
    if not cfg:
        log.error("Portal desconocido %r. Opciones: %s", portal_key, list(PORTALS))
        sys.exit(2)
    host = cfg["host"]
    prefix = cfg["prefix"]

    n_pkg = n_csv = n_inserted = n_skipped = 0
    rows_to_insert: list[dict[str, Any]] = []

    for pkg in _iter_packages(host, limit):
        n_pkg += 1
        resources = _pick_csv_resources(pkg)
        if not resources:
            n_skipped += 1
            continue
        for res in resources:
            n_csv += 1
            row = _build_row(pkg, res, host, prefix)
            if not row["data_url"] or not row["dataset_id"].startswith(prefix):
                continue
            rows_to_insert.append(row)

    log.info(
        "Discovery [%s]: %d packages · %d CSV resources · %d sin CSV",
        portal_key, n_pkg, n_csv, n_skipped,
    )

    if dry_run:
        log.info("DRY-RUN: no inserto. Ejemplo:")
        if rows_to_insert:
            sample = rows_to_insert[0]
            log.info("  %s | %s | %s", sample["dataset_id"], sample["name"][:60], sample["data_url"][:60])
        return

    with psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=False) as conn:
        with conn.cursor() as cur:
            for row in rows_to_insert:
                row["entity_id"] = _resolve_entity_id(cur, row["entity_raw"])
                try:
                    cur.execute(_UPSERT_SQL, row)
                    n_inserted += 1
                except Exception as exc:  # noqa: BLE001
                    log.warning("UPSERT falló para %s: %s", row["dataset_id"], exc)
            conn.commit()

    log.info("Insertados/actualizados: %d datasets (de %d CSV candidatos)", n_inserted, n_csv)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--portal", default="bogota", choices=list(PORTALS),
                   help="Portal CKAN a cosechar")
    p.add_argument("--limit", type=int, default=None, help="Máx packages a procesar")
    p.add_argument("--dry-run", action="store_true", help="No inserta, solo cuenta")
    args = p.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    main(args.portal, args.limit, args.dry_run)
