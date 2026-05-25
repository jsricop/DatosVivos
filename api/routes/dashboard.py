"""Endpoints públicos de datos para el tablero PowerBI (vía C3).

Postgres vive tras VPN y no es alcanzable desde la nube de Power BI, y la VM es
Linux (sin On-premises Data Gateway, que es Windows-only). Como los datos del
tablero son metadata pública del catálogo `datos.gov.co` (sin PII), la vía más
simple con nuestra infra (Cloudflare Tunnel + nginx ya exponen la API) es servir
las views como CSV en URLs públicos y que Power BI Service refresque (Import)
desde ahí, SIN gateway.

    GET /api/v1/dashboard/datasets.csv   — v_dataset_status (tabla maestra)
    GET /api/v1/dashboard/entities.csv   — v_entity_summary (resumen por entidad)
    GET /api/v1/dashboard/top.csv        — v_top_datasets

Whitelist estricta de vistas: el path NO se interpola crudo a SQL.
"""

from __future__ import annotations

import os

import psycopg
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter()

# name del path → view real. Whitelist: evita inyección y expone solo lo curado.
_VIEWS = {
    "datasets": "v_dataset_status",
    "entities": "v_entity_summary",
    "top": "v_top_datasets",
}


def _connect():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="DATABASE_URL no configurada")
    return psycopg.connect(url)


def _view_to_csv(view: str) -> bytes:
    """Exporta una view a CSV vía COPY (streaming, eficiente)."""
    out = bytearray()
    with _connect() as conn, conn.cursor() as cur:
        with cur.copy(f"COPY (SELECT * FROM {view}) TO STDOUT WITH CSV HEADER") as copy:
            for chunk in copy:
                out += bytes(chunk)
    return bytes(out)


@router.get("/dashboard/{name}.csv")
async def dashboard_csv(name: str) -> Response:
    """CSV público de una view del tablero. Anónimo a propósito (Power BI lo
    refresca sin gateway; los datos son públicos sin PII)."""
    view = _VIEWS.get(name)
    if not view:
        raise HTTPException(status_code=404, detail=f"recurso desconocido: {name}")
    csv_bytes = _view_to_csv(view)
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'inline; filename="{name}.csv"',
            # Cache 1h: alinea con el refresco diario; alivia hits repetidos.
            "Cache-Control": "public, max-age=3600",
        },
    )
