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
import re
import sys
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import httpx
import psycopg
from psycopg.types.json import Jsonb

from mcp_server.socrata.discovery_client import DiscoveryClient
from mcp_server.socrata.metadata_client import MetadataClient
from mcp_server.socrata.soda_client import SodaClient
from scripts.classify_quality_flag import mark_admin_only, normalize_categories

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


# Claves canónicas del estándar colombiano (datos.gov.co) por token. Si
# alguna existe en domain_metadata, gana sobre cualquier otra que solo
# CONTENGA el token. Evita la misma clase de bug que parse_frequency_days:
# una clave genérica que matchea por substring (ej. 'frecuencia_*' anidada)
# antes que la canónica.
_DM_PREFERRED_KEYS: dict[str, tuple[str, ...]] = {
    "frecuencia": (
        "Información-de-Datos_Frecuencia-de-Actualización",
        "frecuencia_declarada",
        "frecuencia_actualizacion",
    ),
    "cobertura": (
        "Información-de-Datos_Cobertura-Geográfica",
        "cobertura_geografica",
        "cobertura",
    ),
    "sector": (
        "Información-de-la-Entidad_Sector",
        "sector_administrativo",
        "sector",
    ),
}


def _find_by_token(dm: dict[str, str], token: str) -> str | None:
    """Resuelve una clave de `domain_metadata` por token con prioridad estable:

    1) Coincidencia EXACTA contra la whitelist de claves canónicas.
    2) Clave que EMPIEZA con el token (case-insensitive).
    3) Primera clave que CONTIENE el token (último recurso; preserva
       comportamiento histórico para portales que renombren claves).
    """
    if not dm:
        return None
    tl = token.lower()
    # (1) whitelist exacta — orden de la tupla = prioridad.
    for canonical in _DM_PREFERRED_KEYS.get(tl, ()):
        v = dm.get(canonical)
        if v is not None:
            return v
    # (2) startswith case-insensitive.
    for k, v in dm.items():
        if k.lower().startswith(tl):
            return v
    # (3) contiene (fallback histórico).
    for k, v in dm.items():
        if tl in k.lower():
            return v
    return None


# Plantilla Mustache sin diligenciar: el título llegó como "{{name}}" (o
# cualquier "{{...}}"). Ocurre cuando un portal federa a datos.gov.co con la
# metadata de plantilla vacía; el resultado es un dataset sin título ni
# descripción reales (y suele 404 en origen poco después). Se descarta.
_PLACEHOLDER_RE = re.compile(r"^\{\{.*\}\}$")


def _is_placeholder(value: str) -> bool:
    """True si el string es una plantilla Mustache sin diligenciar ({{...}})."""
    return bool(_PLACEHOLDER_RE.match(value.strip()))


def _scrub_placeholder(value: str | None) -> str | None:
    """El valor, o None si es una plantilla sin diligenciar.

    El caso {{name}} descarta la fila completa (arriba), pero un portal puede
    federar con el título bien y OTROS campos de plantilla vacíos (117 datasets
    llegaron con entity_raw='{{source}}', 2026-07-12): el dataset vale, el
    campo no.
    """
    if value and _is_placeholder(value):
        return None
    return value


def _extract_discovery(result: dict[str, Any]) -> dict[str, Any] | None:
    """Mapea un `result` de la Discovery API a las columnas de `datasets`."""
    resource = result.get("resource") or {}
    classification = result.get("classification") or {}
    result_meta = result.get("metadata") or {}

    dataset_id = resource.get("id")
    if not dataset_id:
        return None

    # Guarda anti-placeholder: no ingerir filas cuyo título es un {{...}} sin
    # diligenciar — son metadata muerta que contamina el catálogo y el tablero.
    if _is_placeholder(resource.get("name") or ""):
        log.debug("Descartado %s: nombre placeholder %r", dataset_id, resource.get("name"))
        return None

    pv = resource.get("page_views") or {}
    dm = _domain_metadata_dict(classification)
    is_federated = resource.get("type") == "federated_href"

    # Federados publican vía DCAT (claves Common-Core_*). Nativos usan el
    # estándar colombiano (Información-de-Datos_*). Para no duplicar lógica,
    # _find_by_token cubre los nativos y aquí caemos a Common-Core_* si el
    # dataset es federado y el token canónico no estuvo.
    if is_federated:
        frecuencia = (
            _find_by_token(dm, "frecuencia")
            or dm.get("Common-Core_Update-Frequency")
        )
        cobertura = (
            _find_by_token(dm, "cobertura")
            or dm.get("Common-Core_Spatial")
        )
        sector = _find_by_token(dm, "sector")  # DCAT no tiene equivalente directo
        category_val = (
            classification.get("domain_category")
            or resource.get("category")
            or dm.get("Common-Core_Theme")
        )
        entity_raw_val = (
            resource.get("attribution")
            or dm.get("Common-Core_Publisher")
            or ""
        )
        license_val = result_meta.get("license") or dm.get("Common-Core_License")
        # URL del CSV externo, si el publicador lo declara en access_points.
        access_points = result_meta.get("access_points") or {}
        data_url = access_points.get("text/csv") or access_points.get("text/json")
        if data_url and "csv" in (access_points.get("text/csv") or "").lower():
            data_format = "csv"
        elif data_url:
            data_format = "json"
        else:
            data_format = None
        federated_status = "ok" if data_url else "no_csv"
    else:
        frecuencia = _find_by_token(dm, "frecuencia")
        cobertura = _find_by_token(dm, "cobertura")
        sector = _find_by_token(dm, "sector")
        category_val = classification.get("domain_category") or resource.get("category")
        entity_raw_val = resource.get("attribution") or ""
        license_val = result_meta.get("license")
        data_url = None
        data_format = None
        federated_status = None

    data_updated = _parse_iso(resource.get("data_updated_at"))

    return {
        "dataset_id": dataset_id,
        "name": resource.get("name") or "",
        "entity_raw": _scrub_placeholder(entity_raw_val) or "",
        "category": _scrub_placeholder(category_val),
        "description": (_scrub_placeholder(resource.get("description")) or "")[:2000],
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
        "license": license_val,
        # Metadata estructurada colombiana
        "cobertura_geografica": cobertura,
        "frecuencia_declarada": frecuencia,
        "sector": sector,
        "domain_metadata": Jsonb(dm) if dm else None,
        # Tags
        "tags": [t for t in (classification.get("domain_tags") or []) if isinstance(t, str)][:25],
        # Federación
        "source_type": "federated" if is_federated else "socrata",
        "data_url": data_url,
        "data_format": data_format,
        "federated_status": federated_status,
    }


# ----------------------------------------------------------------------
# Pasada 1 — Discovery bulk sweep
# ----------------------------------------------------------------------


async def _discovery_sweep(
    client: DiscoveryClient, limit_total: int | None
) -> AsyncIterator[dict[str, Any]]:
    """Pagina dos veces: nativos (`only=dataset`) y federados (`only=federated_href`).

    Se detiene en página vacía dentro de cada pasada o al alcanzar limit_total.
    Total de resultados conserva el límite global si se pasó.
    """
    yielded = 0
    for only_type in ("dataset", "federated_href"):
        offset = 0
        while True:
            page = min(
                DISCOVERY_PAGE,
                (limit_total - yielded) if limit_total else DISCOVERY_PAGE,
            )
            if page <= 0:
                return
            try:
                results = await client.search(
                    query=None, limit=page, offset=offset, only=only_type
                )
            except httpx.HTTPStatusError as e:
                # Discovery topea offset+limit ≈ 10.000. Llegado el cap,
                # paramos esa pasada y seguimos con la siguiente.
                if e.response.status_code == 400 and offset >= 9000:
                    log.warning(
                        "Discovery cap alcanzado (only=%s, offset=%d). "
                        "Cierro pasada.", only_type, offset
                    )
                    break
                raise
            if not results:
                break
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


# Word-boundary "no-letra" para español: cualquier char que NO sea letra/dígito
# (incluye espacios, puntuación, guiones, paréntesis, comas, etc.). Más permisivo
# que \b para no romper con acentos.
_TOKEN_BOUNDARY = re.compile(r"[a-záéíóúñ0-9]", re.IGNORECASE)


def _word_match(needle: str, haystack: str) -> bool:
    """True si `needle` aparece como token completo en `haystack` (ambos ya en
    lower). Evita falsos positivos como abbrev 'ICA' matcheando 'antioqu**ica**'
    o 'única' o 'pública'.
    """
    if not needle or not haystack:
        return False
    # construir patrón con boundary "no-letra-ni-dígito" antes y después
    pattern = (
        r"(?:^|[^a-záéíóúñ0-9])"
        + re.escape(needle)
        + r"(?:$|[^a-záéíóúñ0-9])"
    )
    return bool(re.search(pattern, haystack))


def _build_entity_resolver(conn: psycopg.Connection):
    # ORDER BY length(name) DESC → matches más específicos ganan antes.
    with conn.cursor() as cur:
        cur.execute(
            "SELECT entity_id, name, abbrev FROM entities ORDER BY length(name) DESC NULLS LAST"
        )
        rows = cur.fetchall()
    catalog = [
        (eid, (name or "").lower(), (abbrev or "").lower())
        for eid, name, abbrev in rows
    ]
    cache: dict[str, int | None] = {}

    def resolve(entity_raw: str) -> int | None:
        key = (entity_raw or "").strip().lower()
        if not key:
            return None
        if key in cache:
            return cache[key]
        best: int | None = None
        # Paso 1: nombre exacto o contención con word boundary.
        for eid, name, _abbrev in catalog:
            if name and (name == key or _word_match(name, key)):
                best = eid
                break
        # Paso 2: abreviatura con word boundary (>=3 chars; las de 2 chars son
        # demasiado ambiguas, p.ej. 'PN', 'BR').
        if best is None:
            for eid, _name, abbrev in catalog:
                if abbrev and len(abbrev) >= 3 and _word_match(abbrev, key):
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
            frecuencia_declarada, sector, domain_metadata,
            source_type, data_url, data_format, federated_status
        ) VALUES (
            %(dataset_id)s, %(name)s, %(entity_id)s, %(entity_raw)s,
            %(category)s, %(description)s, %(rows_updated_at)s,
            %(update_frequency)s, %(view_count)s,
            %(created_at_socrata)s, %(socrata_url)s, %(api_url)s, NOW(),
            %(download_count)s, %(page_views_total)s, %(page_views_last_week)s,
            %(page_views_last_month)s, %(data_updated_at)s, %(metadata_updated_at)s,
            %(publication_date)s, %(provenance)s, %(license)s, %(cobertura_geografica)s,
            %(frecuencia_declarada)s, %(sector)s, %(domain_metadata)s,
            %(source_type)s, %(data_url)s, %(data_format)s, %(federated_status)s
        )
        ON CONFLICT (dataset_id) DO UPDATE SET
            name = EXCLUDED.name,
            entity_id = EXCLUDED.entity_id,
            entity_raw = EXCLUDED.entity_raw,
            -- COALESCE+NULLIF: si la fuente no declara categoría, se conserva
            -- la existente (puede ser inferida por backfill_categories.py) en
            -- vez de pisarla con NULL cada noche.
            category = COALESCE(NULLIF(EXCLUDED.category, ''), datasets.category),
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
            domain_metadata = EXCLUDED.domain_metadata,
            source_type = EXCLUDED.source_type,
            data_url = EXCLUDED.data_url,
            data_format = EXCLUDED.data_format,
            federated_status = EXCLUDED.federated_status
        """,
        {
            **rec,
            "entity_id": entity_id,
            # Para federados, el `api_url` SODA no aplica (datos viven en `data_url`).
            "socrata_url": _SOCRATA_PAGE_URL.format(id=rec["dataset_id"]),
            "api_url": (
                None if rec.get("source_type") == "federated"
                else _SOCRATA_API_URL.format(id=rec["dataset_id"])
            ),
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
) -> tuple[str, int | None, int | None, int | None, str | None]:
    """Devuelve (id, row_count, number_of_comments, total_times_rated,
    license_id). license_id viene de Views API (`licenseId`); el ETL lo
    captura en la pasada 2 de enriquecimiento.
    """
    row_count = n_comments = n_rated = None
    license_id: str | None = None
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
                lic = m.get("licenseId")
                if isinstance(lic, str) and lic.strip():
                    license_id = lic.strip()[:80]
            except Exception:  # noqa: BLE001
                pass
    return dataset_id, row_count, n_comments, n_rated, license_id


def _update_enrichment(cur: psycopg.Cursor, rows: list[tuple]) -> None:
    cur.executemany(
        """
        UPDATE datasets SET
            row_count = COALESCE(%s, row_count),
            number_of_comments = COALESCE(%s, number_of_comments),
            total_times_rated = COALESCE(%s, total_times_rated),
            license_id = COALESCE(%s, license_id)
        WHERE dataset_id = %s
        """,
        [(rc, nc, nr, lid, did) for (did, rc, nc, nr, lid) in rows],
    )


# ----------------------------------------------------------------------
# Incremental: decidir qué recontar
# ----------------------------------------------------------------------


def _load_existing(conn: psycopg.Connection) -> dict[str, tuple[Any, int | None]]:
    """{dataset_id: (data_updated_at, row_count)} — base para el diff incremental."""
    with conn.cursor() as cur:
        cur.execute("SELECT dataset_id, data_updated_at, row_count FROM datasets")
        return {r[0]: (r[1], r[2]) for r in cur.fetchall()}


def _needs_enrichment(
    rec: dict[str, Any], existing: dict[str, tuple[Any, int | None]] | None
) -> bool:
    """Modo incremental: recontar solo si es NUEVO, el DATO cambió, o nunca se contó.
    Modo full (existing=None): siempre.

    Federados (`source_type=='federated'`) NO entran a enriquecimiento: el
    SODA `count(*)` no aplica (la data vive en un CSV externo, no en SODA)
    y la Metadata API tampoco trae `numberOfComments`/`totalTimesRated`
    útiles para ellos. Se cuentan vía DuckDB en Hito 2 F.4.
    """
    if rec.get("source_type") == "federated":
        return False
    if existing is None:
        return True
    prev = existing.get(rec["dataset_id"])
    if prev is None:
        return True  # nuevo
    prev_updated, prev_rowcount = prev
    if prev_rowcount is None or prev_updated is None:
        return True  # nunca contado / sin fecha previa
    new_updated = rec.get("data_updated_at")
    return bool(new_updated is not None and new_updated > prev_updated)  # el dato cambió


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


async def _run_bulk(
    conn: psycopg.Connection,
    limit_total: int | None,
    existing: dict[str, tuple[Any, int | None]] | None = None,
) -> tuple[list[str], list[str]]:
    """Pasada 1 (bulk). Devuelve (todos_los_ids, ids_a_enriquecer).

    En incremental (`existing` no es None) `ids_a_enriquecer` son solo los
    nuevos/cambiados/sin contar; en full, son todos.
    """
    client = DiscoveryClient()
    resolve_entity = _build_entity_resolver(conn)
    ids: list[str] = []
    to_enrich: list[str] = []
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
        if _needs_enrichment(rec, existing):
            to_enrich.append(rec["dataset_id"])
        buf.append(rec)
        if len(buf) >= 50:
            await flush()
            if len(ids) % 1000 == 0:
                log.info("Bulk: %d datasets procesados", len(ids))
    await flush()
    log.info("Pasada 1 (bulk) terminada. ok=%d fail=%d total=%d", succeeded, failed, len(ids))
    return ids, to_enrich


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
            # Incremental + enrich-only: solo los que nunca se contaron (row_count NULL).
            where = " WHERE row_count IS NULL" if args.incremental else ""
            with conn.cursor() as cur:
                sql = f"SELECT dataset_id FROM datasets{where} ORDER BY view_count DESC NULLS LAST"
                if args.limit:
                    sql += f" LIMIT {int(args.limit)}"
                cur.execute(sql)
                ids = [r[0] for r in cur.fetchall()]
            to_enrich = ids
        else:
            existing = _load_existing(conn) if args.incremental else None
            ids, to_enrich = await _run_bulk(conn, args.limit, existing)
            if args.incremental:
                log.info(
                    "Incremental: %d de %d datasets requieren recuento (nuevos/cambiados/sin contar)",
                    len(to_enrich), len(ids),
                )

        if not args.no_enrich:
            await _run_enrich(
                conn, to_enrich, want_count=not args.no_rowcount, want_comments=not args.no_comments
            )

        # Clasificación de calidad: re-aplica admin_only (Ley 1712) sobre los nombres ya
        # ingestados. Idempotente. Antes era un script manual desacoplado → se desfasaba con
        # cada ingesta. Solo admin_only (NO no_rows: los sin-conteo son federados no-tabulares).
        n_admin = mark_admin_only(conn)
        conn.commit()
        log.info("Clasificación calidad: admin_only marcados/actualizados=%d", n_admin)

        # Grafías de categoría: la fuente re-declara variantes cada noche
        # ("Función Pública"/"Función pública") → se re-unifican a la dominante.
        n_norm = normalize_categories(conn)
        conn.commit()
        log.info("Categorías normalizadas (grafía dominante): %d", n_norm)

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE etl_runs SET finished_at = NOW(), datasets_succeeded = %s WHERE run_id = %s",
                (len(ids), run_id),
            )
        conn.commit()

    log.info("ETL terminado. total=%d", len(ids))

    # Farmeo: regla diaria de la bodega Parquet (entra-uno-sale-uno, migración
    # 027). Corre DESPUÉS de cerrar etl_runs: acotado en tiempo, con advisory
    # lock, y un fallo suyo jamás afecta al ETL (run_daily nunca lanza).
    if not args.no_farm:
        from scripts.farm_datasets import run_daily
        run_daily()
        # Perfil de filtrables (ADR-024): tras el farmeo, re-perfila los
        # parquets nuevos/refrescados. Incremental, acotado, nunca lanza.
        from scripts.profile_filter_values import run_daily as profile_daily
        profile_daily()
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None, help="cap de datasets (sample)")
    p.add_argument("--no-enrich", action="store_true", help="solo pasada 1 (bulk Discovery)")
    p.add_argument("--enrich-only", action="store_true", help="solo pasada 2 sobre datasets existentes")
    p.add_argument("--incremental", action="store_true",
                   help="recontar solo nuevos/cambiados (compara data_updated_at); para refresco recurrente")
    p.add_argument("--no-rowcount", action="store_true", help="omitir count(*) SODA")
    p.add_argument("--no-comments", action="store_true", help="omitir comments/rating Metadata")
    p.add_argument("--no-farm", action="store_true",
                   help="omitir la regla diaria de la bodega Parquet (farmeo)")
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(asyncio.run(main(_parse_args())))
