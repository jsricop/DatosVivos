"""ETL — refresca el catálogo de datasets desde Socrata Metadata API → Postgres.

Itera todos los IDs indexados en ChromaDB y persiste su `rowsUpdatedAt`,
`updateFrequency`, `viewCount`, etc. en la tabla `datasets` para alimentar
el dashboard PowerBI ejecutivo (ADR-014).

Diseño:
- Lee IDs en lotes desde ChromaDB (paginado).
- Llama `MetadataClient.get(id)` con un Semaphore para respetar rate limits.
- Mapea `attribution` → `entities` con tabla de aliases.
- Upsert idempotente en `datasets` y `dataset_tags`.
- Refresca telemetría del propio run en `etl_runs`.

Uso:
    DATABASE_URL=postgresql://dv:...@localhost:5432/datosvivos \\
        python -m scripts.etl_refresh_catalog
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg

from ai_engine.vector_index import VectorIndex
from mcp_server.socrata.metadata_client import MetadataClient

log = logging.getLogger("etl_refresh_catalog")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DATABASE_URL = os.getenv("DATABASE_URL")
RATE_LIMIT = int(os.getenv("ETL_RATE_LIMIT", "5"))  # concurrent requests
BATCH_PAUSE_MS = int(os.getenv("ETL_BATCH_PAUSE_MS", "200"))


_SOCRATA_PAGE_URL = "https://www.datos.gov.co/d/{id}"
_SOCRATA_API_URL = "https://www.datos.gov.co/resource/{id}.json"


def _iter_indexed_ids(index_path: Path | None = None) -> list[str]:
    """Devuelve todos los IDs indexados en ChromaDB (orden estable arbitrario)."""
    vi = VectorIndex.load(index_path)
    # Acceso al collection — chromadb soporta paginación con limit/offset.
    collection = vi._collection  # noqa: SLF001 — necesario, no hay API pública
    total = collection.count()
    log.info("ChromaDB tiene %d datasets indexados", total)
    ids: list[str] = []
    page = 1000
    for offset in range(0, total, page):
        out = collection.get(limit=page, offset=offset, include=[])
        batch = out.get("ids") or []
        ids.extend(batch)
    return ids


def _parse_ts(raw: Any) -> datetime | None:
    """Socrata devuelve `rowsUpdatedAt` como epoch UTC int o ISO string."""
    if raw is None:
        return None
    try:
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(int(raw), tz=timezone.utc)
        if isinstance(raw, str):
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, OSError):
        return None
    return None


def _extract_meta(meta: dict[str, Any]) -> dict[str, Any]:
    """Extrae los campos relevantes para el dashboard de un dump de Metadata API."""
    return {
        "dataset_id": meta.get("id"),
        "name": meta.get("name") or "",
        "entity_raw": meta.get("attribution") or "",
        "category": meta.get("category"),
        "description": (meta.get("description") or "")[:2000],
        "rows_updated_at": _parse_ts(meta.get("rowsUpdatedAt")),
        "update_frequency": _resolve_frequency(meta),
        "row_count": _safe_int(meta.get("rowsCount") or meta.get("viewLastModified")),
        "view_count": _safe_int(meta.get("viewCount")),
        "created_at_socrata": _parse_ts(meta.get("createdAt")),
        "tags": [t for t in (meta.get("tags") or []) if isinstance(t, str)][:25],
    }


def _resolve_frequency(meta: dict[str, Any]) -> str | None:
    """Socrata expone la frecuencia en `metadata.custom_fields` con clave libre
    o como campo de primer nivel `updateFrequency`/`accrualPeriodicity`.
    Búsqueda tolerante en orden de probabilidad."""
    direct = meta.get("updateFrequency") or meta.get("accrualPeriodicity")
    if direct:
        return str(direct)
    custom = meta.get("metadata") or {}
    custom_fields = custom.get("custom_fields") or {}
    for section in custom_fields.values():
        if not isinstance(section, dict):
            continue
        for k, v in section.items():
            kl = str(k).lower()
            if v and any(token in kl for token in ("frecuencia", "frequency", "periodic")):
                return str(v)
    return None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


async def _fetch_one(
    client: MetadataClient, sem: asyncio.Semaphore, dataset_id: str
) -> tuple[str, dict[str, Any] | None, str | None]:
    async with sem:
        try:
            meta = await client.get(dataset_id)
            return dataset_id, _extract_meta(meta), None
        except Exception as exc:  # noqa: BLE001
            return dataset_id, None, str(exc)


def _upsert_dataset(
    cur: psycopg.Cursor, record: dict[str, Any], entity_id: int | None
) -> None:
    cur.execute(
        """
        INSERT INTO datasets (
            dataset_id, name, entity_id, entity_raw, category, description,
            rows_updated_at, update_frequency, row_count, view_count,
            created_at_socrata, socrata_url, api_url, last_refreshed_at
        ) VALUES (
            %(dataset_id)s, %(name)s, %(entity_id)s, %(entity_raw)s,
            %(category)s, %(description)s, %(rows_updated_at)s,
            %(update_frequency)s, %(row_count)s, %(view_count)s,
            %(created_at_socrata)s, %(socrata_url)s, %(api_url)s, NOW()
        )
        ON CONFLICT (dataset_id) DO UPDATE SET
            name = EXCLUDED.name,
            entity_id = EXCLUDED.entity_id,
            entity_raw = EXCLUDED.entity_raw,
            category = EXCLUDED.category,
            description = EXCLUDED.description,
            rows_updated_at = EXCLUDED.rows_updated_at,
            update_frequency = EXCLUDED.update_frequency,
            row_count = EXCLUDED.row_count,
            view_count = EXCLUDED.view_count,
            created_at_socrata = EXCLUDED.created_at_socrata,
            socrata_url = EXCLUDED.socrata_url,
            api_url = EXCLUDED.api_url,
            last_refreshed_at = NOW()
        """,
        {
            **record,
            "entity_id": entity_id,
            "socrata_url": _SOCRATA_PAGE_URL.format(id=record["dataset_id"]),
            "api_url": _SOCRATA_API_URL.format(id=record["dataset_id"]),
        },
    )

    # Tags: reemplazar todos (más simple que diff incremental).
    cur.execute("DELETE FROM dataset_tags WHERE dataset_id = %s", (record["dataset_id"],))
    tags = record.get("tags") or []
    if tags:
        cur.executemany(
            "INSERT INTO dataset_tags (dataset_id, tag) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            [(record["dataset_id"], t) for t in tags],
        )


def _build_entity_resolver(conn: psycopg.Connection):
    """Devuelve una función que mapea `entity_raw` → `entity_id` con cache.

    Estrategia: match por prefijo del nombre (case-insensitive). Si no hay match,
    NULL en `entity_id` y el dashboard lo agrupa bajo "Sin entidad mapeada".
    """
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


async def main() -> int:
    if not DATABASE_URL:
        log.error("DATABASE_URL no definida. Aborto.")
        return 2

    ids = _iter_indexed_ids()
    log.info("ETL inicia para %d datasets (rate=%d, pause=%dms)", len(ids), RATE_LIMIT, BATCH_PAUSE_MS)

    client = MetadataClient()
    sem = asyncio.Semaphore(RATE_LIMIT)

    succeeded = 0
    failed = 0
    failures: list[tuple[str, str]] = []

    with psycopg.connect(DATABASE_URL, autocommit=False) as conn:
        # Telemetría del run.
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO etl_runs (script_name, datasets_total) VALUES (%s, %s) RETURNING run_id",
                ("etl_refresh_catalog", len(ids)),
            )
            row = cur.fetchone()
            assert row is not None
            run_id = row[0]
        conn.commit()

        resolve_entity = _build_entity_resolver(conn)

        # Procesar en batches para no quedarnos sin file descriptors ni sobrecargar Socrata.
        BATCH = 50
        for i in range(0, len(ids), BATCH):
            batch_ids = ids[i : i + BATCH]
            tasks = [_fetch_one(client, sem, did) for did in batch_ids]
            results = await asyncio.gather(*tasks, return_exceptions=False)

            with conn.cursor() as cur:
                for dataset_id, record, err in results:
                    if err:
                        failed += 1
                        failures.append((dataset_id, err))
                        continue
                    if record is None:
                        failed += 1
                        continue
                    try:
                        entity_id = resolve_entity(record.get("entity_raw") or "")
                        _upsert_dataset(cur, record, entity_id)
                        succeeded += 1
                    except Exception as exc:  # noqa: BLE001
                        log.exception("Upsert falló para %s: %s", dataset_id, exc)
                        failed += 1
                        failures.append((dataset_id, str(exc)))
            conn.commit()

            log.info(
                "Batch %d-%d procesado. succeeded=%d failed=%d",
                i,
                i + len(batch_ids),
                succeeded,
                failed,
            )
            await asyncio.sleep(BATCH_PAUSE_MS / 1000)

        # Cierre del run.
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE etl_runs SET
                    finished_at = NOW(),
                    datasets_succeeded = %s,
                    datasets_failed = %s,
                    error = %s
                WHERE run_id = %s
                """,
                (
                    succeeded,
                    failed,
                    "\n".join(f"{d}: {e}" for d, e in failures[:20]) if failures else None,
                    run_id,
                ),
            )
        conn.commit()

    log.info("ETL terminado. succeeded=%d failed=%d total=%d", succeeded, failed, len(ids))
    return 0 if failed < len(ids) * 0.1 else 1  # tolera <10% fallos


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
