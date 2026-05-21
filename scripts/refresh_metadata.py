"""Refresca SOLO la metadata (name, entity, description, category) de los
datasets ya indexados — sin re-embedder, sin agregar nuevos.

Caso de uso: cuando `_shape_discovery_result` cambia (ej. el fix de
`owner.display_name` vs `attribution` del 2026-05-21), el `build_index.py`
no lo refleja porque es idempotente sobre el ID (salta existentes).

Este script:
1. Recorre Discovery API en lotes.
2. Para cada hit, genera el shape actualizado (igual que build_index).
3. Si el ID ya está en ChromaDB, hace `collection.update(ids=, metadatas=)`
   SOLO actualizando metadata. Embeddings y documentos quedan intactos.
4. Si el ID no existe, lo saltea (no es responsabilidad de este script).

Uso:
    python -m scripts.refresh_metadata

Mucho más rápido que rebuild: ~5-8 min vs 30+ min porque no toca embeddings.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai_engine.vector_index import VectorIndex  # noqa: E402
from mcp_server.socrata.discovery_client import DiscoveryClient  # noqa: E402
from scripts.build_index import _fetch_page, _shape_discovery_result  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

PAGE_SIZE = 100


async def _refresh() -> tuple[int, int]:
    """Actualiza metadata de todos los datasets existentes.

    Returns:
        (updated, skipped) — IDs actualizados vs no presentes en el índice.
    """
    idx = VectorIndex.load()
    initial_count = len(idx)
    log.info("Índice cargado: %d datasets existentes", initial_count)

    # DiscoveryClient NO es async context manager — solo instanciarlo.
    client = DiscoveryClient()
    offset = 0
    updated = 0
    skipped = 0
    processed = 0
    try:
        while True:
            page = await _fetch_page(client, offset, PAGE_SIZE)
            if not page:
                break

            shaped = [_shape_discovery_result(r) for r in page]
            ids_in_page = [s["id"] for s in shaped if s["id"]]
            existing = idx.existing_ids(ids_in_page)

            # Solo actualizar los que YA están en el índice
            ids_to_update: list[str] = []
            metadatas_to_update: list[dict[str, Any]] = []
            for s in shaped:
                if not s["id"]:
                    continue
                if s["id"] not in existing:
                    skipped += 1
                    continue
                # Build metadata limpia (sin tags ni description en metadata —
                # description vive en el document text, no en metadata)
                metadatas_to_update.append({
                    "name": s["name"],
                    "entity": s["entity"] or "",
                    "category": s["category"] or "",
                    "description": s["description"] or "",
                })
                ids_to_update.append(s["id"])

            if ids_to_update:
                idx._collection.update(
                    ids=ids_to_update,
                    metadatas=metadatas_to_update,
                )
                updated += len(ids_to_update)

            processed += len(page)
            log.info(
                "  → %d procesados, %d actualizados (esta página: %d update / %d skip)",
                processed, updated, len(ids_to_update), len(page) - len(ids_to_update),
            )

            if len(page) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
    finally:
        # DiscoveryClient usa httpx.AsyncClient internamente; cerrar bien.
        close_method = getattr(client, "aclose", None) or getattr(client, "close", None)
        if close_method:
            result = close_method()
            if asyncio.iscoroutine(result):
                await result

    log.info("✓ Refresh completo. Actualizados: %d, no en índice: %d", updated, skipped)
    return updated, skipped


def main() -> int:
    asyncio.run(_refresh())
    return 0


if __name__ == "__main__":
    sys.exit(main())
