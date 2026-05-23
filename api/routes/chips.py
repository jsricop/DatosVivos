"""Endpoints de chips — entrada PRIMARIA de búsqueda (Fase 1 audit top-down).

GET  /api/v1/chips           — listas dinámicas de TEMA/TIPO/TERRITORIO/ENTIDAD
GET  /api/v1/chips/refine    — sub-tags refinadores del subset (capa 2, A.1)
POST /api/v1/query/chips     — recibe combinación, devuelve subset filtrado

Diseño: SQL determinista, sin retrieval ML. La narrativa LLM solo entra al
final si el endpoint avanza a ejecución (TIPO marcado → SoQL → narrativa).

Telemetría: cada query con chips registra dataset_top1_id y los chips usados
para que el eval harness y dashboards midan adopción.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException, Query
from psycopg.rows import dict_row

from api.models.schemas import (
    ChipOption,
    ChipsCandidateDataset,
    ChipsQueryRequest,
    ChipsQueryResponse,
    ChipsRefineResponse,
    ChipsResponse,
)

router = APIRouter()
log = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Constantes — TIPO hardcoded (no viene del catálogo), TERRITORIO armado
# ----------------------------------------------------------------------


# Values DEBEN coincidir con el Literal `ChipTipo` en api/models/schemas.py
# para que POST /query/chips acepte sin necesidad de mapping. Slugs como
# "cuantos"/"comparar" fueron eliminados por consistencia (ver fix #36).
_TIPO_OPTIONS = [
    ChipOption(value="Cuántos", label="Cuántos",
               hint="Conteo simple: cuántos X hay"),
    ChipOption(value="Comparar", label="Comparar",
               hint="Diferencias entre dos o más territorios/categorías"),
    ChipOption(value="Ranking", label="Ranking",
               hint="Top N por una métrica"),
    ChipOption(value="Tendencia", label="Tendencia",
               hint="Evolución temporal"),
    ChipOption(value="Mapa", label="Mapa",
               hint="Distribución geográfica (coroplético)"),
]

# Macroregiones — para chips que agrupan dptos. Códigos DIVIPOLA por región
# (basado en DANE). Se prependen a la lista de chips TERRITORIO.
_MACRO_REGIONES = {
    "macro:caribe": ("Caribe", ["08", "13", "20", "23", "44", "47", "70", "88"]),
    "macro:pacifico": ("Pacífico", ["19", "27", "52", "76"]),
    "macro:andina": ("Andina", ["05", "11", "15", "17", "18", "19", "25",
                                 "41", "50", "54", "63", "66", "68", "73"]),
    "macro:amazonia": ("Amazonía", ["18", "86", "91", "94", "95", "97"]),
    "macro:orinoquia": ("Orinoquía", ["50", "81", "85", "99"]),
}

# Tags administrativos genéricos que aparecen en muchos datasets pero NO son
# útiles como sub-temas semánticos (Ley de Transparencia, esquemas de
# publicación, ITA, etc.). Se filtran del top de `dataset_tags` para que la
# capa 2 de chips refleje temas reales (matrícula, cobertura, deforestación)
# y no obligaciones administrativas.
_TAG_STOPLIST = frozenset({
    "activos de información",
    "activos de informacion",
    "esquema de publicación",
    "esquema de publicacion",
    "esquema de publicación de la información",
    "esquema de publicacion de la informacion",
    "indice de información clasificada y reservada",
    "indice de informacion clasificada y reservada",
    "índice de información clasificada y reservada",
    "ley 1712",
    "ley de transparencia",
    "transparencia",
    "ita",
    "gestión documental",
    "gestion documental",
    "notaria",
    "notaría",
    "categoría",
    "categoria",
    "tabla de retención documental",
    "trd",
    "informe de gestión",
    "informe de gestion",
})

# Cap del subset que tiene sentido refinar — si el subset es enorme (>500),
# los tags del top reflejan ruido del catálogo más que del query.
_REFINE_SUBSET_MAX = 500

# Pesos del score compuesto del ELEGIDO (A.2 del roadmap).
# Reemplaza el `ORDER BY view_count DESC, rows_updated_at DESC` crudo por
# una combinación normalizada que premia datasets populares Y recientes.
#   view: log-normalized contra el max del subset → estable cuando hay outliers
#         con cientos de miles de vistas.
#   freshness: decae linealmente hasta 0 a los `_FRESHNESS_HALF_LIFE_DAYS`*2
#         días. 0 si nunca actualizado (rows_updated_at IS NULL).
# Pesos deliberadamente parejos: la popularidad por sí sola elegía datasets
# administrativos antiguos pero muy vistos (ej. Esquema de Publicación).
_SCORE_W_VIEW = 0.55
_SCORE_W_FRESHNESS = 0.45
_FRESHNESS_HALF_LIFE_DAYS = 365  # 1 año = score 0.5; 2 años = score 0


# ----------------------------------------------------------------------
# Conexión Postgres — lazy single connection (lecturas chicas)
# ----------------------------------------------------------------------


def _connect():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="DATABASE_URL no configurada")
    return psycopg.connect(url, row_factory=dict_row)


# ----------------------------------------------------------------------
# GET /api/v1/chips
# ----------------------------------------------------------------------


@router.get("/chips", response_model=ChipsResponse)
async def list_chips() -> ChipsResponse:
    """Devuelve las 4 listas de chips construidas dinámicamente desde la DB.

    - TEMA: top-12 categorías (`datasets.category`) por count.
    - TIPO: 5 fijos (UI determina forma de respuesta).
    - TERRITORIO: Nacional + 32 dptos + 5 macroregiones (ordenados).
    - ENTIDAD: top-20 entities por uso real (telemetría dataset_top1_id).
    """
    with _connect() as conn:
        # TEMA
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT category, COUNT(*) AS c
                FROM datasets
                WHERE category IS NOT NULL AND category != ''
                GROUP BY category
                ORDER BY c DESC
                LIMIT 12
                """
            )
            temas = [
                ChipOption(value=r["category"], label=r["category"], count=r["c"])
                for r in cur.fetchall()
            ]

        # ENTIDAD — top por uso si hay telemetría, sino por count en datasets
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT e.entity_id, e.name AS entity_name, COUNT(d.dataset_id) AS c
                FROM entities e
                LEFT JOIN datasets d ON d.entity_id = e.entity_id
                GROUP BY e.entity_id, e.name
                HAVING COUNT(d.dataset_id) > 0
                ORDER BY c DESC
                LIMIT 20
                """
            )
            entidades = [
                ChipOption(value=str(r["entity_id"]), label=r["entity_name"], count=r["c"])
                for r in cur.fetchall()
            ]

    # TERRITORIO — armado en código
    territorios = [ChipOption(value="nacional", label="Nacional",
                              hint="Cobertura para todo el país")]
    # Macroregiones (5)
    for k, (name, _codes) in _MACRO_REGIONES.items():
        territorios.append(ChipOption(value=k, label=name,
                                      hint="Macroregión (agrupa varios dptos)"))
    # Dptos canónicos — desde DEPARTAMENTOS de geo_resolver
    from ai_engine.geo_resolver import DEPARTAMENTOS
    for canon, code, _syn in DEPARTAMENTOS:
        territorios.append(ChipOption(value=code, label=canon))

    return ChipsResponse(
        tema=temas,
        tipo=_TIPO_OPTIONS,
        territorio=territorios,
        entidad=entidades,
    )


# ----------------------------------------------------------------------
# POST /api/v1/query/chips
# ----------------------------------------------------------------------


def _territory_codes(value: str) -> list[str] | None:
    """Convierte un valor de chip TERRITORIO a lista de códigos DIVIPOLA.

    Returns None si "nacional" (no filtrar por geo).
    """
    if value == "nacional":
        return None
    if value.startswith("macro:"):
        macro = _MACRO_REGIONES.get(value)
        return macro[1] if macro else []
    return [value]  # código directo (dpto o mpio)


def _suggest_chips(req: ChipsQueryRequest) -> list[str]:
    """Sugerencias de chips a marcar a continuación cuando el subset es grande."""
    suggestions = []
    if not req.entidad:
        suggestions.append("entidad")
    if not req.territorio:
        suggestions.append("territorio")
    if not req.tipo:
        suggestions.append("tipo")
    return suggestions


def _build_chips_where(
    tema: str | None,
    entidad: str | None,
    territorio: str | None,
    subtags: list[str] | None = None,
    refinador: str | None = None,
) -> tuple[str, list[Any]]:
    """Arma la cláusula WHERE compartida entre /query/chips y /chips/refine.

    Devuelve `(where_sql, params)` listos para usar con %s. `where_sql` ya
    incluye `WHERE` cuando hay condiciones, o `TRUE` si no.
    """
    where: list[str] = []
    params: list[Any] = []

    if tema:
        where.append("category = %s")
        params.append(tema)

    if entidad:
        try:
            ent_id = int(entidad)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"entidad inválida: {entidad}")
        where.append("entity_id = %s")
        params.append(ent_id)

    if territorio:
        codes = _territory_codes(territorio)
        if codes is not None:  # None = nacional, no filtrar
            placeholders = ", ".join(["%s"] * len(codes))
            where.append(
                f"(jurisdiccion_geo_codes ?| array[{placeholders}] "
                f"OR EXISTS (SELECT 1 FROM jsonb_array_elements_text(jurisdiccion_geo_codes) c "
                f"          WHERE c LIKE ANY(array[{placeholders}])))"
            )
            params.extend(codes)
            params.extend([f"{c}%" for c in codes])

    if subtags:
        # Multi-subtags = intersection: el dataset debe tener TODOS los tags
        # marcados. Se logra con un EXISTS por cada subtag.
        for tag in subtags:
            where.append(
                "EXISTS (SELECT 1 FROM dataset_tags dt "
                "WHERE dt.dataset_id = d.dataset_id AND dt.tag = %s)"
            )
            params.append(tag)

    if refinador:
        where.append("(d.name ILIKE %s OR d.description ILIKE %s)")
        ref_like = f"%{refinador}%"
        params.append(ref_like)
        params.append(ref_like)

    where_sql = " AND ".join(where) if where else "TRUE"
    return where_sql, params


# ----------------------------------------------------------------------
# GET /api/v1/chips/refine — capa 2 sub-tags refinadores (A.1)
# ----------------------------------------------------------------------


@router.get("/chips/refine", response_model=ChipsRefineResponse)
async def refine_chips(
    tema: str | None = Query(default=None),
    territorio: str | None = Query(default=None),
    entidad: str | None = Query(default=None),
    limit: int = Query(default=15, ge=1, le=30),
) -> ChipsRefineResponse:
    """Devuelve los tags más frecuentes del subset filtrado por chips capa 1.

    Se aplica una stoplist de tags administrativos genéricos (Ley 1712, ITA,
    activos de información, etc.) para que los chips reflejen temas reales.

    Si el subset es muy grande (>500 datasets), retorna lista vacía para no
    devolver tags-ruido del catálogo entero.
    """
    if not any([tema, territorio, entidad]):
        return ChipsRefineResponse(subset_total=0, subtags=[])

    where_sql, params = _build_chips_where(tema, entidad, territorio)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS c FROM datasets d WHERE {where_sql}", params)
            row = cur.fetchone()
            total = (row["c"] if row else 0) if isinstance(row, dict) else (row[0] if row else 0)

        if total == 0 or total > _REFINE_SUBSET_MAX:
            return ChipsRefineResponse(subset_total=total, subtags=[])

        # Tags top del subset. Excluimos stoplist en SQL para no traer
        # entries que después tendríamos que descartar.
        stoplist_sql = "%s, " * len(_TAG_STOPLIST)
        stoplist_sql = stoplist_sql.rstrip(", ")
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT dt.tag, COUNT(DISTINCT d.dataset_id) AS c
                FROM datasets d
                JOIN dataset_tags dt ON dt.dataset_id = d.dataset_id
                WHERE {where_sql}
                  AND lower(dt.tag) NOT IN ({stoplist_sql})
                  AND length(dt.tag) BETWEEN 3 AND 60
                GROUP BY dt.tag
                ORDER BY c DESC, dt.tag ASC
                LIMIT %s
                """,
                params + [t.lower() for t in _TAG_STOPLIST] + [limit],
            )
            rows = cur.fetchall()

    subtags = [
        ChipOption(value=r["tag"], label=r["tag"], count=r["c"])
        for r in rows
    ]
    return ChipsRefineResponse(subset_total=total, subtags=subtags)


@router.post("/query/chips", response_model=ChipsQueryResponse)
async def query_chips(req: ChipsQueryRequest) -> ChipsQueryResponse:
    """Filtra el catálogo por combinación de chips y devuelve top-N candidatos.

    Si el subset es grande (>10) y el usuario no marcó TIPO, devuelve la lista
    sin ejecutar SoQL — esperando que refine. Si subset es manejable o el
    usuario marcó TIPO, escoge el top-1 (por view_count) como `chosen_dataset_id`.

    La narrativa final NO se genera acá — el cliente que quiera respuesta
    completa hace un segundo POST a `/api/v1/query` con `q` derivada de los
    chips. Esto separa concerns y deja la narrativa LLM en su flujo SSE.
    """
    if not any([req.tema, req.tipo, req.territorio, req.entidad, req.refinador, req.subtags]):
        raise HTTPException(
            status_code=400,
            detail="Marcá al menos un chip antes de buscar.",
        )

    where_sql, params = _build_chips_where(
        tema=req.tema,
        entidad=req.entidad,
        territorio=req.territorio,
        subtags=req.subtags,
        refinador=req.refinador,
    )

    # Conteo + top-10
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS c FROM datasets d WHERE {where_sql}", params)
            row = cur.fetchone()
            total = (row["c"] if row else 0) if isinstance(row, dict) else (row[0] if row else 0)

        with conn.cursor() as cur:
            # Score compuesto (A.2): view_count log-normalizado contra el max
            # del subset + freshness lineal decay 2 años. Reemplaza ORDER BY
            # crudo que elegía datasets popular-pero-viejos.
            #
            # Estructura CTE:
            #   subset → todos los datasets que matchean los chips
            #   stats  → max(view_count) del subset (constante para
            #            normalización LN dentro del subset)
            #
            # max_view se calcula GREATEST(1) para que LN(0)=undefined no
            # rompa, y NULLIF para que datasets sin view_count no propaguen
            # NaN. last_updated NULL → freshness = 0.
            cur.execute(
                f"""
                WITH subset AS (
                  SELECT d.* FROM datasets d WHERE {where_sql}
                ),
                stats AS (
                  SELECT GREATEST(MAX(view_count), 1) AS max_view FROM subset
                )
                SELECT s.dataset_id, s.name, s.entity_raw,
                       s.category, s.row_count, s.view_count,
                       s.rows_updated_at::text AS last_updated,
                       s.socrata_url AS url, s.api_url,
                       s.jurisdiccion_nivel, s.jurisdiccion_geo_codes,
                       (
                         %s * (LN(GREATEST(COALESCE(s.view_count, 0), 1)) /
                               NULLIF(LN((SELECT max_view FROM stats)), 0))
                         +
                         %s * GREATEST(0, 1 - LEAST(1,
                            EXTRACT(EPOCH FROM (NOW() - s.rows_updated_at)) /
                            (%s * 2 * 86400)
                         ))
                       ) AS score
                FROM subset s
                ORDER BY score DESC NULLS LAST,
                         s.view_count DESC NULLS LAST,
                         s.rows_updated_at DESC NULLS LAST
                LIMIT 10
                """,
                params + [_SCORE_W_VIEW, _SCORE_W_FRESHNESS, _FRESHNESS_HALF_LIFE_DAYS],
            )
            rows = cur.fetchall()

    candidates = [
        ChipsCandidateDataset(
            dataset_id=r["dataset_id"],
            name=r["name"],
            entity=r.get("entity_raw"),
            category=r.get("category"),
            row_count=r.get("row_count"),
            view_count=r.get("view_count"),
            last_updated=r.get("last_updated"),
            url=r.get("url") or f"https://www.datos.gov.co/d/{r['dataset_id']}",
            api_url=r.get("api_url") or f"https://www.datos.gov.co/resource/{r['dataset_id']}.json",
            jurisdiccion_nivel=r.get("jurisdiccion_nivel"),
            jurisdiccion_geo_codes=r.get("jurisdiccion_geo_codes"),
            score=(round(float(r["score"]), 4) if r.get("score") is not None else None),
        )
        for r in rows
    ]

    # Decidir chosen_dataset_id
    chosen: str | None = None
    msg: str | None = None
    suggested: list[str] | None = None

    if req.force_dataset_id:
        chosen = req.force_dataset_id
    elif total == 0:
        msg = "Ningún dataset coincide con esta combinación de chips. Probá quitar alguno."
    elif total <= 10 or req.tipo:
        # Subset manejable o usuario ya marcó TIPO → ejecutar
        chosen = candidates[0].dataset_id if candidates else None
    else:
        # Subset grande sin TIPO marcado → sugerir refinar
        msg = f"Hay {total} datasets que coinciden. Marcá otro chip para verlos más específicos."
        suggested = _suggest_chips(req)

    return ChipsQueryResponse(
        total_in_subset=total,
        candidates=candidates,
        chosen_dataset_id=chosen,
        suggested_chips=suggested,
        message=msg,
    )
