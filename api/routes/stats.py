"""Endpoint de estadísticas del catálogo.

GET /api/v1/stats/catalog — conteos agregados (total, origen, acceso, calidad)
calculados EN VIVO sobre `v_dataset_status_decisor`, la misma vista que alimenta
el tablero Power BI. Fuente única de verdad: así el frontend y el tablero nunca
se desfasan (evita números quemados como el viejo "más de 8.000 datasets").
"""

from __future__ import annotations

import os

import psycopg
from fastapi import APIRouter, HTTPException
from psycopg.rows import dict_row

from api.models.schemas import CatalogStats

router = APIRouter()


def _connect():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="DATABASE_URL no configurada")
    return psycopg.connect(url, row_factory=dict_row)


# Una sola pasada con FILTER — mismos CASE que definen es_federado/acceso_datos
# en la vista (migración 021), por lo que los conteos coinciden por construcción.
_STATS_SQL = """
    SELECT
        count(*)                                                            AS total,
        count(*) FILTER (WHERE es_federado = 'no')                          AS nativos,
        count(*) FILTER (WHERE es_federado = 'sí')                          AS federados,
        count(*) FILTER (WHERE acceso_datos = 'directo')                    AS directo,
        count(*) FILTER (WHERE acceso_datos = 'requiere_herramienta')       AS requiere_herramienta,
        count(*) FILTER (WHERE acceso_datos = 'solo_metadatos')             AS solo_metadatos,
        count(*) FILTER (WHERE acceso_datos IN ('directo','requiere_herramienta')) AS consultable_tabla,
        count(*) FILTER (WHERE quality_flag IS NULL OR quality_flag = 'ok') AS util,
        count(*) FILTER (WHERE quality_flag = 'admin_only')                 AS admin
    FROM v_dataset_status_decisor
"""


@router.get("/stats/catalog", response_model=CatalogStats)
def catalog_stats() -> CatalogStats:
    """Conteos del catálogo en vivo desde la vista del tablero."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(_STATS_SQL)
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="sin datos de catálogo")
    return CatalogStats(**row)
