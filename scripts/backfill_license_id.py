"""Backfill `datasets.license_id` para nativos.

Migración 017 añadió la columna pero el ETL solo la rellena en su pasada
2 cuando algo más cambia. Este script es puntual:

  - Lee todos los nativos (`source_type='socrata'`) con `license_id IS NULL`.
  - Consulta Views API (Metadata) por cada uno para obtener `licenseId`.
  - UPDATE en bloques de 100; commit incremental para no perder progreso
    si se interrumpe.

Federados no aplican (Socrata Metadata API no los expone con
`licenseId`; ya tenemos su `license` del Common-Core_License en
domain_metadata).

Uso (dentro del contenedor api):
    DATABASE_URL=... python -m scripts.backfill_license_id
    DATABASE_URL=... python -m scripts.backfill_license_id --limit 100  # sample
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

import psycopg
from psycopg.rows import dict_row

from mcp_server.socrata.metadata_client import MetadataClient

log = logging.getLogger("backfill_license_id")
DATABASE_URL = os.environ.get("DATABASE_URL")
CONCURRENCY = 16
BATCH_COMMIT = 100


async def _fetch_license(
    meta: MetadataClient, sem: asyncio.Semaphore, dataset_id: str
) -> tuple[str, str | None]:
    async with sem:
        try:
            m = await meta.get(dataset_id)
            lic = m.get("licenseId")
            if isinstance(lic, str) and lic.strip():
                return dataset_id, lic.strip()[:80]
        except Exception:  # noqa: BLE001
            pass
    return dataset_id, None


async def main(limit: int | None) -> None:
    if not DATABASE_URL:
        log.error("DATABASE_URL no definida")
        sys.exit(1)

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT dataset_id FROM datasets
                WHERE source_type = 'socrata' AND license_id IS NULL
                ORDER BY dataset_id
                """ + (f" LIMIT {int(limit)}" if limit else "")
            )
            ids = [row["dataset_id"] for row in cur.fetchall()]
    log.info("Por procesar: %d datasets", len(ids))

    meta = MetadataClient()
    sem = asyncio.Semaphore(CONCURRENCY)

    n_ok = n_null = n_err = 0
    buffer: list[tuple[str, str]] = []

    with psycopg.connect(DATABASE_URL, autocommit=False) as conn:
        for i in range(0, len(ids), CONCURRENCY * 4):
            chunk = ids[i:i + CONCURRENCY * 4]
            results = await asyncio.gather(
                *(_fetch_license(meta, sem, ds) for ds in chunk),
                return_exceptions=False,
            )
            for ds, lic in results:
                if lic:
                    n_ok += 1
                    buffer.append((lic, ds))
                else:
                    n_null += 1

            if len(buffer) >= BATCH_COMMIT:
                with conn.cursor() as cur:
                    cur.executemany(
                        "UPDATE datasets SET license_id=%s WHERE dataset_id=%s",
                        buffer,
                    )
                conn.commit()
                buffer.clear()

            done = i + len(chunk)
            if done % 500 == 0 or done == len(ids):
                log.info("Procesados %d/%d (ok=%d null=%d)", done, len(ids), n_ok, n_null)

        # Flush final.
        if buffer:
            with conn.cursor() as cur:
                cur.executemany(
                    "UPDATE datasets SET license_id=%s WHERE dataset_id=%s",
                    buffer,
                )
            conn.commit()

    log.info("Terminado. ok=%d null=%d", n_ok, n_null)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    asyncio.run(main(args.limit))
