"""Construye el índice vectorial inicial desde Discovery API (~8.000 datasets).

Itera la Discovery API paginando, extrae metadatos relevantes, y los inserta
en `VectorIndex` con `upsert` (idempotente — re-correr no duplica).

Uso:
    # Build completo (~8k datasets, 10-15 min en CPU)
    python -m scripts.build_index

    # Build parcial (útil para dev/tests)
    python -m scripts.build_index --limit 500

    # Output path custom
    python -m scripts.build_index --output ./mi_indice

Diseño:
- Idempotente: `VectorIndex.upsert_many` usa `id` como clave, re-correr
  actualiza pero no duplica.
- Progreso: imprime cada `progress_every` datasets indexados.
- Robusto: errores transitorios de red (timeout, 5xx) NO matan el proceso;
  el batch se salta con warning y se continúa.
- Batch: agrupa N datasets antes de generar embeddings para amortizar la
  carga del modelo (más eficiente que 1 a 1).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

import httpx

# Permitir ejecución como script directo o como módulo
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_engine.vector_index import VectorIndex  # noqa: E402
from mcp_server.socrata.discovery_client import DiscoveryClient  # noqa: E402

log = logging.getLogger(__name__)


def _shape_discovery_result(r: dict[str, Any]) -> dict[str, Any]:
    """Aplana un objeto Discovery a la forma que VectorIndex acepta."""
    resource = r.get("resource", {}) or {}
    classification = r.get("classification", {}) or {}
    return {
        "id": resource.get("id"),
        "name": resource.get("name") or "",
        "description": (resource.get("description") or "").strip(),
        "entity": resource.get("attribution"),
        "category": classification.get("domain_category"),
        "tags": resource.get("columns_field_name") or [],
    }


async def _fetch_page(
    client: DiscoveryClient, offset: int, page_size: int, retries: int = 3
) -> list[dict[str, Any]]:
    """Trae una página con reintentos básicos en errores transitorios."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return await client.search(query=None, limit=page_size, offset=offset)
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError) as exc:
            last_exc = exc
            wait = 2**attempt
            log.warning(
                "Fetch falló en offset=%d (intento %d/%d): %s. Reintentando en %ds...",
                offset,
                attempt + 1,
                retries,
                exc,
                wait,
            )
            await asyncio.sleep(wait)
    log.error("Fetch definitivo fallido en offset=%d: %s — saltando página.", offset, last_exc)
    return []


async def _build_index_async(
    output_path: Path,
    limit: int | None,
    page_size: int = 100,
    progress_every: int = 100,
) -> int:
    """Implementación async del build. Retorna número de datasets nuevos indexados.

    Semántica de `limit`: máximo de items PROCESADOS del catálogo (incluyendo los
    que ya estaban indexados). Esto hace que correr dos veces con el mismo límite
    sea idempotente — la segunda corrida visita los mismos items y no agrega nada.
    Para indexar todo el catálogo, pasar `limit=None`.
    """
    idx = VectorIndex(path=output_path)
    initial = len(idx)
    log.info("Índice inicial: %d datasets en %s", initial, output_path)

    client = DiscoveryClient()
    processed = 0  # items visitados desde Discovery (nuevos + ya existentes)
    added_total = 0  # solo los realmente nuevos insertados
    offset = 0

    while True:
        if limit and processed >= limit:
            break
        this_page_size = min(page_size, (limit - processed)) if limit else page_size
        if this_page_size <= 0:
            break

        page = await _fetch_page(client, offset=offset, page_size=this_page_size)
        if not page:
            # Sin más resultados (o página falló tras reintentos)
            break

        items = [_shape_discovery_result(r) for r in page]
        items = [it for it in items if it["id"]]  # filtra sin id

        # Idempotencia: solo embebber + upsert los IDs que aún no están en el índice.
        # Esto evita el rebuild de HNSW de ChromaDB cuando re-corremos el script.
        incoming_ids = [str(it["id"]) for it in items]
        already_indexed = idx.existing_ids(incoming_ids)
        new_items = [it for it in items if str(it["id"]) not in already_indexed]
        skipped = len(items) - len(new_items)

        added = idx.upsert_many(new_items)
        added_total += added
        processed += len(page)
        offset += len(page)
        if skipped:
            log.debug("Saltados %d datasets ya indexados en esta página", skipped)

        if processed % progress_every < page_size or (limit and processed >= limit):
            print(
                f"  → {processed} procesados, {added_total} nuevos "
                f"(total en índice: {len(idx)})",
                flush=True,
            )

        # Si la API devolvió menos que el page_size pedido, ya no hay más
        if len(page) < this_page_size:
            break

    final = len(idx)
    print(
        f"\n✓ Build completo. Procesados: {processed}, nuevos: {added_total}. "
        f"Total en índice: {final} (era {initial})."
    )
    return added_total


def build_index(
    output_path: Path | None = None,
    limit: int | None = None,
    page_size: int = 100,
) -> int:
    """Entry point síncrono usable desde scripts o tests.

    Args:
        output_path: dónde persistir ChromaDB. Default: `./data/vector_index`.
        limit: máximo de datasets a indexar (None = todos los disponibles).
        page_size: tamaño de página al Discovery API.

    Returns:
        Número de datasets indexados en esta corrida.
    """
    out = output_path or Path("./data/vector_index")
    return asyncio.run(_build_index_async(out, limit=limit, page_size=page_size))


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Construye el índice vectorial de datos.gov.co")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./data/vector_index"),
        help="Ruta donde persistir el índice (default: ./data/vector_index)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Máximo de datasets a indexar (default: todos)",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="Tamaño de página Discovery API (default: 100)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Log DEBUG")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    count = build_index(output_path=args.output, limit=args.limit, page_size=args.page_size)
    sys.exit(0 if count > 0 else 1)


if __name__ == "__main__":
    _cli()
