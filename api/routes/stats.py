"""Endpoints de estadísticas del catálogo.

GET /api/v1/stats/catalog — conteos agregados (total, origen, acceso, calidad)
calculados EN VIVO sobre `v_dataset_status_decisor`, la misma vista que alimenta
el tablero Power BI. Fuente única de verdad: así el frontend y el tablero nunca
se desfasan (evita números quemados como el viejo "más de 8.000 datasets").

GET /api/v1/stats/panorama — panorama nacional para la home (ADR-023): totales,
semáforo de frescura, acceso, por sector y por departamento DIVIPOLA. Todas las
cifras con el filtro de calidad estándar (quality_flag NULL/'ok'). Cacheado en
memoria con TTL (`PANORAMA_TTL_SECONDS`, default 300s) porque la agregación por
departamento expande JSONB sobre ~25k filas.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import psycopg
from fastapi import APIRouter, HTTPException
from psycopg.rows import dict_row

from api.models.schemas import (
    CatalogStats,
    DeptCount,
    PanoramaStats,
    PortalCount,
    SectorCount,
    YearCumulative,
)
from api.routes.divipola import _DEPT_NAMES

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


# ----------------------------------------------------------------------
# Panorama nacional (ADR-023)
# ----------------------------------------------------------------------

# Línea editorial sobre el CATÁLOGO COMPLETO (decisión 2026-07-10): mismos
# totales que /stats/catalog. La composición temáticos/administrativos se
# muestra como una dimensión más (Ley 1712), no como filtro previo.

_PANORAMA_TOTALS_SQL = """
    SELECT
        count(*)                                                      AS total,
        count(DISTINCT entity_id)                                     AS n_entidades,
        count(*) FILTER (WHERE status = 'verde')                      AS verde,
        count(*) FILTER (WHERE status = 'amarillo')                   AS amarillo,
        count(*) FILTER (WHERE status = 'rojo')                       AS rojo,
        count(*) FILTER (WHERE status = 'desconocido'
                            OR status IS NULL)                        AS desconocido,
        count(*) FILTER (WHERE acceso_datos = 'directo')              AS directo,
        count(*) FILTER (WHERE acceso_datos = 'requiere_herramienta') AS requiere_herramienta,
        count(*) FILTER (WHERE acceso_datos = 'solo_metadatos')       AS solo_metadatos,
        count(*) FILTER (WHERE quality_flag = 'admin_only')           AS administrativos
    FROM v_dataset_status_decisor
"""

# Federados de datos.gov.co no declaran sector (0% cobertura) → quedan fuera;
# el frontend lo anota como "entre los que declaran sector".
_PANORAMA_SECTOR_SQL = """
    SELECT sector,
           count(*)                  AS n_datasets,
           count(DISTINCT entity_id) AS n_entidades
    FROM v_dataset_status_decisor
    WHERE sector IS NOT NULL AND sector != ''
    GROUP BY sector
    ORDER BY n_datasets DESC
    LIMIT 10
"""

# Sobre la TABLA datasets: la vista _decisor no expone jurisdiccion_geo_codes.
# Códigos DIVIPOLA: 2 dígitos = departamento, 5 = municipio → LEFT(code, 2).
# DISTINCT obligatorio: un dataset multi-municipio del mismo dpto contaría doble.
_PANORAMA_DEPT_SQL = """
    SELECT LEFT(code, 2) AS codigo,
           count(DISTINCT d.dataset_id) AS n_datasets
    FROM datasets d
    CROSS JOIN LATERAL jsonb_array_elements_text(d.jurisdiccion_geo_codes) AS code
    WHERE d.jurisdiccion_geo_codes IS NOT NULL
    GROUP BY 1
    ORDER BY n_datasets DESC
"""

_PANORAMA_SIN_GEO_SQL = """
    SELECT count(*) AS n
    FROM datasets
    WHERE jurisdiccion_geo_codes IS NULL
"""

# Línea de tiempo del catálogo: cuándo se creó cada dataset EN SU PORTAL DE
# ORIGEN (created_at_socrata; publication_date de respaldo). Para los
# anteriores al registro de DatosVivos es un estimado del origen — para los
# nuevos coincide con su ingreso. La cola 2008-2015 (9 datasets) se agrupa
# en el primer punto para no alargar la gráfica con años vacíos.
_PANORAMA_CRECIMIENTO_SQL = """
    SELECT GREATEST(
             EXTRACT(YEAR FROM COALESCE(created_at_socrata, publication_date))::int,
             2015
           ) AS anio,
           count(*) AS n
    FROM datasets
    WHERE COALESCE(created_at_socrata, publication_date) IS NOT NULL
    GROUP BY 1
    ORDER BY 1
"""

# Portales de ORIGEN del catálogo integrado. Criterio único (decisión
# 2026-07-10): cada dataset se atribuye al portal donde su entidad lo publica
# originalmente, sin importar la ruta de cosecha. En orden:
#   1. Cosechado directo de un portal regional → ese portal (source_portal).
#   2. Federado vía datos.gov.co pero con data_url en un portal regional
#      conocido → ese portal (son las copias del solapamiento cross-portal).
#   3. Federado vía datos.gov.co publicado por el IGAC → Colombia en Mapas
#      (su geoportal; "agust_n" con comodín esquiva la tilde en ILIKE).
#   4. Resto → datos.gov.co (nativos + demás federados sin portal propio
#      identificable en los datos; no se inventa atribución sin evidencia).
# Los hosts se canonizan sin "www." para no partir un portal en dos claves.
_PANORAMA_PORTAL_SQL = """
    WITH base AS (
        SELECT
            d.source_type,
            regexp_replace(COALESCE(d.source_portal, ''), '^www\\.', '') AS sp,
            regexp_replace(
                COALESCE(substring(d.data_url FROM 'https?://([^/]+)'), ''),
                '^www\\.', ''
            ) AS durl_host,
            (e.name ILIKE '%agust_n codazzi%' OR e.name ILIKE '%IGAC%'
             OR d.entity_raw ILIKE '%agust_n codazzi%'
             OR d.entity_raw ILIKE '%IGAC%') AS es_igac
        FROM datasets d
        LEFT JOIN entities e ON e.entity_id = d.entity_id
    )
    SELECT CASE
             WHEN sp != '' AND sp != 'datos.gov.co' THEN sp
             WHEN source_type = 'federated'
              AND durl_host IN ('datosabiertos.bogota.gov.co', 'datos.cali.gov.co',
                                'medata.gov.co', 'datosabiertos.valledelcauca.gov.co')
               THEN durl_host
             WHEN source_type = 'federated' AND es_igac
               THEN 'colombiaenmapas.igac.gov.co'
             ELSE 'datos.gov.co'
           END AS portal,
           count(*) AS n_datasets
    FROM base
    GROUP BY 1
    ORDER BY n_datasets DESC
"""

# Caché módulo-level sin locks: peor caso bajo carga = cómputo duplicado,
# aceptable. Se invalida por TTL, no por escritura (el ETL corre 1 vez/día).
_PANORAMA_TTL = float(os.environ.get("PANORAMA_TTL_SECONDS", "300"))
_panorama_cache: tuple[float, PanoramaStats] | None = None


def _compute_panorama() -> PanoramaStats:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(_PANORAMA_TOTALS_SQL)
        totals = cur.fetchone()
        if not totals:
            raise HTTPException(status_code=500, detail="sin datos de catálogo")

        cur.execute(_PANORAMA_SECTOR_SQL)
        sectores = cur.fetchall()

        cur.execute(_PANORAMA_DEPT_SQL)
        dptos = cur.fetchall()

        cur.execute(_PANORAMA_SIN_GEO_SQL)
        sin_geo = cur.fetchone()

        cur.execute(_PANORAMA_PORTAL_SQL)
        portales = cur.fetchall()

        # La fecha de actualización REAL del catálogo es el cierre de la
        # última corrida del ETL, no el momento de cómputo de este caché.
        cur.execute("SELECT max(finished_at) AS t FROM etl_runs")
        last_etl = (cur.fetchone() or {}).get("t")

        # Uso e interacción ciudadana: el contraste ES el hallazgo — se
        # descarga masivamente, no se dialoga (68 datasets con comentarios
        # de 25k, medido 2026-07-13).
        cur.execute(
            """
            SELECT
              COALESCE(sum(download_count), 0)::bigint AS descargas_totales,
              count(*) FILTER (WHERE page_views_last_month > 0) AS consultados_mes,
              count(*) FILTER (WHERE number_of_comments > 0) AS con_comentarios
            FROM datasets
            """
        )
        interaccion_row = cur.fetchone() or {}

        cur.execute(_PANORAMA_CRECIMIENTO_SQL)
        acumulado = 0
        crecimiento = []
        for r in cur.fetchall():
            acumulado += r["n"]
            crecimiento.append(YearCumulative(anio=r["anio"], acumulado=acumulado))

    return PanoramaStats(
        total=totals["total"],
        n_entidades=totals["n_entidades"],
        composicion={
            "tematicos": totals["total"] - totals["administrativos"],
            "administrativos": totals["administrativos"],
        },
        semaforo={
            "verde": totals["verde"],
            "amarillo": totals["amarillo"],
            "rojo": totals["rojo"],
            "desconocido": totals["desconocido"],
        },
        acceso={
            "directo": totals["directo"],
            "requiere_herramienta": totals["requiere_herramienta"],
            "solo_metadatos": totals["solo_metadatos"],
        },
        por_sector=[SectorCount(**r) for r in sectores],
        por_departamento=[
            DeptCount(
                codigo=r["codigo"],
                nombre=_DEPT_NAMES[r["codigo"]],
                n_datasets=r["n_datasets"],
            )
            # Defensivo: descartar códigos fuera del catálogo DIVIPOLA canónico.
            for r in dptos
            if r["codigo"] in _DEPT_NAMES
        ],
        por_portal=[PortalCount(**r) for r in portales],
        nacional_sin_geo=(sin_geo or {}).get("n", 0),
        generated_at=datetime.now(timezone.utc).isoformat(),
        last_etl_at=last_etl.isoformat() if last_etl else None,
        crecimiento=crecimiento,
        interaccion={
            "descargas_totales": int(interaccion_row.get("descargas_totales") or 0),
            "consultados_mes": int(interaccion_row.get("consultados_mes") or 0),
            "con_comentarios": int(interaccion_row.get("con_comentarios") or 0),
        },
    )


@router.get("/stats/panorama", response_model=PanoramaStats)
def panorama_stats() -> PanoramaStats:
    """Panorama nacional para la home, cacheado con TTL en memoria."""
    global _panorama_cache
    now = time.monotonic()
    if _panorama_cache is not None and (now - _panorama_cache[0]) < _PANORAMA_TTL:
        return _panorama_cache[1]
    stats = _compute_panorama()
    _panorama_cache = (now, stats)
    return stats
