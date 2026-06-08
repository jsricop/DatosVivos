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
#
# Vistas _decisor (Hito R 2026-06-08): versión curada con drop de duplicados
# literales (view_count, data_updated_at, frecuencia_declarada) + drop de
# columnas técnicas (api_url, last_refreshed_at). Mantienen el resto con
# lectura honesta de NULL (señal real, no censura). Coexisten con las viejas
# 2-4 semanas para migrar PowerBI sin romper el modelo M.
_VIEWS = {
    "datasets": "v_dataset_status",
    "entities": "v_entity_summary",
    "top": "v_top_datasets",
    "datasets_decisor": "v_dataset_status_decisor",
    "entities_decisor": "v_entity_summary_decisor",
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


def _max_last_refreshed() -> str | None:
    """MAX(last_refreshed_at) de `datasets` formateado como header HTTP-date
    (RFC 7231). Reemplaza `last_refreshed_at` que se dropeó de las vistas
    _decisor (Hito R FU.3): mover frescura del CSV al header."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT MAX(last_refreshed_at) FROM datasets")
        row = cur.fetchone()
    if not row or not row[0]:
        return None
    # RFC 7231: 'Day, DD Mon YYYY HH:MM:SS GMT'
    return row[0].astimezone().strftime("%a, %d %b %Y %H:%M:%S GMT")


@router.get("/dashboard/{name}.csv")
async def dashboard_csv(name: str) -> Response:
    """CSV público de una view del tablero. Anónimo a propósito (Power BI lo
    refresca sin gateway; los datos son públicos sin PII)."""
    view = _VIEWS.get(name)
    if not view:
        raise HTTPException(status_code=404, detail=f"recurso desconocido: {name}")
    csv_bytes = _view_to_csv(view)
    headers = {
        "Content-Disposition": f'inline; filename="{name}.csv"',
        # Cache 1h: alinea con el refresco diario; alivia hits repetidos.
        "Cache-Control": "public, max-age=3600",
    }
    last_mod = _max_last_refreshed()
    if last_mod:
        headers["Last-Modified"] = last_mod
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )
