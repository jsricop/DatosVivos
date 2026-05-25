"""ETL — refresca el catálogo de datasets desde Socrata → Postgres.

Fuentes complementarias (cada una aporta lo que la otra no tiene):

1. **Discovery API (bulk, enumeración + casi todo)** — pagina TODO el dominio
   datos.gov.co. Aporta: name, attribution, category, tags, descripción,
   engagement (download_count, page_views semana/mes/total), fechas
   (data/metadata/publicación/creación), provenance, license y la metadata
   estructurada colombiana (`domain_metadata`: cobertura geográfica,
   frecuencia declarada, sector). AUTORITATIVA para todo lo que expone.

2. **Metadata API (por dataset)** — SOLO `numberOfComments` + `totalTimesRated`
   (Discovery no los tiene). En campos solapados manda Discovery.

3. **SODA `count(*)` (por dataset)** — `row_count` real (ninguna API lo da;
   antes el ETL guardaba un timestamp por error — ver migración 005).

Diseño:
- Pasada 1 (bulk): pagina Discovery, upsert idempotente en `datasets`/`dataset_tags`.
- Pasada 2 (enriquecimiento): por cada dataset, SODA count(*) + Metadata comments,
  con Semaphore para respetar rate limits. Tolera errores por dataset (datasets
  no tabulares / blobs → row_count queda NULL).

Uso:
    DATABASE_URL=... python -m scripts.etl_refresh_catalog               # todo
    DATABASE_URL=... python -m scripts.etl_refresh_catalog --limit 100   # sample
    DATABASE_URL=... python -m scripts.etl_refresh_catalog --no-enrich   # solo bulk
    DATABASE_URL=... python -m scripts.etl_refresh_catalog --enrich-only  # solo pasada 2
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import psycopg
from psycopg.types.json import Jsonb

from mcp_server.socrata.discovery_client import DiscoveryClient
from mcp_server.socrata.metadata_client import MetadataClient
from mcp_server.socrata.soda_client import SodaClient

log = logging.getLogger("etl_refresh_catalog")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DATABASE_URL = os.getenv("DATABASE_URL")
RATE_LIMIT = int(os.getenv("ETL_RATE_LIMIT", "5"))       # concurrent requests (pasada 2)
DISCOVERY_PAGE = int(os.getenv("ETL_DISCOVERY_PAGE", "1000"))
BATCH_PAUSE_MS = int(os.getenv("ETL_BATCH_PAUSE_MS", "200"))
# count(*) en datasets gigantes (SECOP, financieros) es lento; timeout amplio.
# Los que aún excedan quedan en row_count=NULL (honesto), nunca con basura.
SODA_COUNT_TIMEOUT = float(os.getenv("ETL_SODA_COUNT_TIMEOUT", "90"))

_SOCRATA_PAGE_URL = "https://www.datos.gov.co/d/{id}"
_SOCRATA_API_URL = "https://www.datos.gov.co/resource/{id}.json"


# ----------------------------------------------------------------------
# Parsers
# ----------------------------------------------------------------------


def _parse_iso(raw: Any) -> datetime | None:
    """Discovery devuelve fechas ISO ('2024-01-18T17:30:09.000Z')."""
    if not raw:
        return None
    try:
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(int(raw), tz=timezone.utc)
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (ValueError, OSError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError):
        return None


def _domain_metadata_dict(classification: dict[str, Any]) -> dict[str, str]:
    """Aplana `classification.domain_metadata` ([{key,value}]) a dict plano."""
    out: dict[str, str] = {}
    for item in classification.get("domain_metadata") or []:
        k = item.get("key")
        v = item.get("value")
        if k is not None and v is not None:
            out[str(k)] = str(v)
    return out


def _find_by_token(dm: dict[str, str], token: str) -> str | None:
    """Busca el primer valor cuya clave contiene `token` (case-insensitive)."""
    tl = token.lower()
    for k, v in dm.items():
        if tl in k.lower():
            return v
    return None


def _extract_discovery(result: dict[str, Any]) -> dict[str, Any] | None:
    """Mapea un `result` de la Discovery API a las columnas de `datasets`."""
    resource = result.get("resource") or {}
    classification = result.get("classification") or {}
    result_meta = result.get("metadata") or {}

    dataset_id = resource.get("id")
    if not dataset_id:
        return None

    pv = resource.get("page_views") or {}
    dm = _domain_metadata_dict(classification)

    # Frecuencia declarada (español) — fuente canónica datos.gov.co. Alimenta
    # también `update_frequency` para que el semáforo use la frecuencia que
    # la entidad declaró (parse_frequency_days en db ya entiende español).
    frecuencia = _find_by_token(dm, "frecuencia")

    data_updated = _parse_iso(resource.get("data_updated_at"))

    return {
        "dataset_id": dataset_id,
        "name": resource.get("name") or "",
        "entity_raw": resource.get("attribution") or "",
        "category": classification.get("domain_category") or resource.get("category"),
        "description": (resource.get("description") or "")[:2000],
        # rows_updated_at = fecha del DATO (no del metadata) → semáforo correcto.
        "rows_updated_at": data_updated,
        "data_updated_at": data_updated,
        "metadata_updated_at": _parse_iso(resource.get("metadata_updated_at")),
        "publication_date": _parse_iso(resource.get("publication_date")),
        "created_at_socrata": _parse_iso(resource.get("createdAt")),
        "update_frequency": frecuencia,
        # Engagement
        "download_count": _safe_int(resource.get("download_count")),
        "view_count": _safe_int(pv.get("page_views_total")),
        "page_views_total": _safe_int(pv.get("page_views_total")),
        "page_views_last_week": _safe_int(pv.get("page_views_last_week")),
        "page_views_last_month": _safe_int(pv.get("page_views_last_month")),
        # Confianza / apertura
        "provenance": resource.get("provenance"),
        "license": result_meta.get("license"),
        # Metadata estructurada colombiana
        "cobertura_geografica": _find_by_token(dm, "cobertura"),
        "frecuencia_declarada": frecuencia,
        "sector": _find_by_token(dm, "sector"),
        "domain_metadata": Jsonb(dm) if dm else None,
        # Tags (domain_tags de la clasificación)
        "tags": [t for t in (classification.get("domain_tags") or []) if isinstance(t, str)][:25],
    }


# ----------------------------------------------------------------------
# Pasada 1 — Discovery bulk sweep
# ----------------------------------------------------------------------


async def _discovery_sweep(
    client: DiscoveryClient, limit_total: int | None
) -> AsyncIterator[dict[str, Any]]:
    """Pagina todo el dominio. Se detiene en página vacía o al alcanzar limit_total."""
    offset = 0
    yielded = 0
    while True:
        page = min(DISCOVERY_PAGE, (limit_total - yielded) if limit_total else DISCOVERY_PAGE)
        if page <= 0:
            return
        results = await client.search(query=None, limit=page, offset=offset)
        if not results:
            return
        for r in results:
            yield r
            yielded += 1
            if limit_total and yielded >= limit_total:
                return
        offset += len(results)
        await asyncio.sleep(BATCH_PAUSE_MS / 1000)


# ----------------------------------------------------------------------
# Entity resolver (igual que antes: match por prefijo de nombre)
# ----------------------------------------------------------------------


def _build_entity_resolver(conn: psycopg.Connection):
    with conn.cursor() as cur:
        cur.execute("SELECT entity_id, name, abbrev FROM entities")
        rows = cur.fetchall()
    catalog = [(eid, name.lower(), (abbrev or "").lower()) for eid, name, abbrev in rows]
    cache: dict[str, int | None] = {}

    def resolve(entity_raw: str) -> int | None:
        key = (entity_raw or "").strip().lower()
        if not key:
            return None
        if key in cache:
            return cache[key]
        best: int | None = None
        for eid, name, abbrev in catalog:
            if name and (name in key or key in name):
                best = eid
                break
            if abbrev and abbrev in key:
                best = eid
                break
        cache[key] = best
        return best

    return resolve


def _upsert_dataset(cur: psycopg.Cursor, rec: dict[str, Any], entity_id: int | None) -> None:
    cur.execute(
        """
        INSERT INTO datasets (
            dataset_id, name, entity_id, entity_raw, category, description,
            rows_updated_at, update_frequency, view_count,
            created_at_socrata, socrata_url, api_url, last_refreshed_at,
            download_count, page_views_total, page_views_last_week,
            page_views_last_month, data_updated_at, metadata_updated_at,
            publication_date, provenance, license, cobertura_geografica,
            frecuencia_declarada, sector, domain_metadata
        ) VALUES (
            %(dataset_id)s, %(name)s, %(entity_id)s, %(entity_raw)s,
            %(category)s, %(description)s, %(rows_updated_at)s,
            %(update_frequency)s, %(view_count)s,
            %(created_at_socrata)s, %(socrata_url)s, %(api_url)s, NOW(),
            %(download_count)s, %(page_views_total)s, %(page_views_last_week)s,
            %(page_views_last_month)s, %(data_updated_at)s, %(metadata_updated_at)s,
            %(publication_date)s, %(provenance)s, %(license)s, %(cobertura_geografica)s,
            %(frecuencia_declarada)s, %(sector)s, %(domain_metadata)s
        )
        ON CONFLICT (dataset_id) DO UPDATE SET
            name = EXCLUDED.name,
            entity_id = EXCLUDED.entity_id,
            entity_raw = EXCLUDED.entity_raw,
            category = EXCLUDED.category,
            description = EXCLUDED.description,
            rows_updated_at = EXCLUDED.rows_updated_at,
            update_frequency = EXCLUDED.update_frequency,
            view_count = EXCLUDED.view_count,
            created_at_socrata = EXCLUDED.created_at_socrata,
            socrata_url = EXCLUDED.socrata_url,
            api_url = EXCLUDED.api_url,
            last_refreshed_at = NOW(),
            download_count = EXCLUDED.download_count,
            page_views_total = EXCLUDED.page_views_total,
            page_views_last_week = EXCLUDED.page_views_last_week,
            page_views_last_month = EXCLUDED.page_views_last_month,
            data_updated_at = EXCLUDED.data_updated_at,
            metadata_updated_at = EXCLUDED.metadata_updated_at,
            publication_date = EXCLUDED.publication_date,
            provenance = EXCLUDED.provenance,
            license = EXCLUDED.license,
            cobertura_geografica = EXCLUDED.cobertura_geografica,
            frecuencia_declarada = EXCLUDED.frecuencia_declarada,
            sector = EXCLUDED.sector,
            domain_metadata = EXCLUDED.domain_metadata
        """,
        {
            **rec,
            "entity_id": entity_id,
            "socrata_url": _SOCRATA_PAGE_URL.format(id=rec["dataset_id"]),
            "api_url": _SOCRATA_API_URL.format(id=rec["dataset_id"]),
        },
    )
    cur.execute("DELETE FROM dataset_tags WHERE dataset_id = %s", (rec["dataset_id"],))
    tags = rec.get("tags") or []
    if tags:
        cur.executemany(
            "INSERT INTO dataset_tags (dataset_id, tag) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            [(rec["dataset_id"], t) for t in tags],
        )


# ----------------------------------------------------------------------
# Pasada 2 — enriquecimiento por dataset (SODA count + Metadata comments)
# ----------------------------------------------------------------------


async def _enrich_one(
    soda: SodaClient,
    meta: MetadataClient,
    sem: asyncio.Semaphore,
    dataset_id: str,
    want_count: bool,
    want_comments: bool,
) -> tuple[str, int | None, int | None, int | None]:
    """Devuelve (id, row_count, number_of_comments, total_times_rated)."""
    row_count = n_comments = n_rated = None
    async with sem:
        if want_count:
            try:
                res = await soda.query(dataset_id, soql_query="SELECT count(*) AS n")
                if res:
                    row_count = _safe_int(res[0].get("n"))
            except Exception:  # noqa: BLE001 — datasets no tabulares / blobs
                pass
        if want_comments:
            try:
                m = await meta.get(dataset_id)
                n_comments = _safe_int(m.get("numberOfComments"))
                n_rated = _safe_int(m.get("totalTimesRated"))
            except Exception:  # noqa: BLE001
                pass
    return dataset_id, row_count, n_comments, n_rated


def _update_enrichment(cur: psycopg.Cursor, rows: list[tuple]) -> None:
    cur.executemany(
        """
        UPDATE datasets SET
            row_count = COALESCE(%s, row_count),
            number_of_comments = COALESCE(%s, number_of_comments),
            total_times_rated = COALESCE(%s, total_times_rated)
        WHERE dataset_id = %s
        """,
        [(rc, nc, nr, did) for (did, rc, nc, nr) in rows],
    )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


async def _run_bulk(conn: psycopg.Connection, limit_total: int | None) -> list[str]:
    """Pasada 1. Devuelve la lista de dataset_ids procesados."""
    client = DiscoveryClient()
    resolve_entity = _build_entity_resolver(conn)
    ids: list[str] = []
    succeeded = failed = 0
    buf: list[dict[str, Any]] = []

    async def flush() -> None:
        nonlocal succeeded, failed
        if not buf:
            return
        with conn.cursor() as cur:
            for rec in buf:
                try:
                    eid = resolve_entity(rec.get("entity_raw") or "")
                    _upsert_dataset(cur, rec, eid)
                    succeeded += 1
                except Exception as exc:  # noqa: BLE001
                    log.exception("Upsert falló %s: %s", rec.get("dataset_id"), exc)
                    failed += 1
        conn.commit()
        buf.clear()

    async for result in _discovery_sweep(client, limit_total):
        rec = _extract_discovery(result)
        if rec is None:
            failed += 1
            continue
        ids.append(rec["dataset_id"])
        buf.append(rec)
        if len(buf) >= 50:
            await flush()
            if len(ids) % 1000 == 0:
                log.info("Bulk: %d datasets procesados", len(ids))
    await flush()
    log.info("Pasada 1 (bulk) terminada. ok=%d fail=%d total=%d", succeeded, failed, len(ids))
    return ids


async def _run_enrich(
    conn: psycopg.Connection, ids: list[str], want_count: bool, want_comments: bool
) -> None:
    soda, meta = SodaClient(timeout=SODA_COUNT_TIMEOUT), MetadataClient()
    sem = asyncio.Semaphore(RATE_LIMIT)
    done = 0
    BATCH = 50
    for i in range(0, len(ids), BATCH):
        chunk = ids[i : i + BATCH]
        results = await asyncio.gather(
            *[_enrich_one(soda, meta, sem, did, want_count, want_comments) for did in chunk]
        )
        with conn.cursor() as cur:
            _update_enrichment(cur, results)
        conn.commit()
        done += len(chunk)
        if done % 500 == 0:
            log.info("Enriquecimiento: %d/%d datasets", done, len(ids))
        await asyncio.sleep(BATCH_PAUSE_MS / 1000)
    log.info("Pasada 2 (enriquecimiento) terminada. %d datasets", len(ids))


async def main(args: argparse.Namespace) -> int:
    if not DATABASE_URL:
        log.error("DATABASE_URL no definida. Aborto.")
        return 2

    with psycopg.connect(DATABASE_URL, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO etl_runs (script_name, datasets_total) VALUES (%s, %s) RETURNING run_id",
                ("etl_refresh_catalog", args.limit or 0),
            )
            run_id = cur.fetchone()[0]  # type: ignore[index]
        conn.commit()

        if args.enrich_only:
            with conn.cursor() as cur:
                sql = "SELECT dataset_id FROM datasets ORDER BY view_count DESC NULLS LAST"
                if args.limit:
                    sql += f" LIMIT {int(args.limit)}"
                cur.execute(sql)
                ids = [r[0] for r in cur.fetchall()]
        else:
            ids = await _run_bulk(conn, args.limit)

        if not args.no_enrich:
            await _run_enrich(
                conn, ids, want_count=not args.no_rowcount, want_comments=not args.no_comments
            )

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE etl_runs SET finished_at = NOW(), datasets_succeeded = %s WHERE run_id = %s",
                (len(ids), run_id),
            )
        conn.commit()

    log.info("ETL terminado. total=%d", len(ids))
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None, help="cap de datasets (sample)")
    p.add_argument("--no-enrich", action="store_true", help="solo pasada 1 (bulk Discovery)")
    p.add_argument("--enrich-only", action="store_true", help="solo pasada 2 sobre datasets existentes")
    p.add_argument("--no-rowcount", action="store_true", help="omitir count(*) SODA")
    p.add_argument("--no-comments", action="store_true", help="omitir comments/rating Metadata")
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(asyncio.run(main(_parse_args())))
