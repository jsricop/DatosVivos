"""Endpoints de chips — entrada PRIMARIA de búsqueda (Fase 1 audit top-down).

GET  /api/v1/chips                  — listas dinámicas TEMA/TIPO/TERRITORIO/ENTIDAD
GET  /api/v1/chips/refine           — sub-tags refinadores del subset (capa 2, A.1)
POST /api/v1/query/chips            — recibe combinación, devuelve subset filtrado
POST /api/v1/query/chips/execute    — ejecuta SoQL determinista del TIPO sobre el dataset elegido (Fase B)

Diseño: SQL determinista, sin retrieval ML. La narrativa LLM solo entra al
final si el endpoint avanza a ejecución (TIPO marcado → SoQL → narrativa).

Telemetría: cada query con chips registra dataset_top1_id y los chips usados
para que el eval harness y dashboards midan adopción.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

import httpx
import psycopg
from fastapi import APIRouter, HTTPException, Query
from psycopg.rows import dict_row

from ai_engine.chips_telemetry import emit_event
from ai_engine.duckdb_executor import (
    describe_csv,
    describe_parquet,
    execute_csv,
    execute_parquet,
)
from ai_engine.duckdb_templates import build_duckdb_sql
from ai_engine.llm_backend import get_backend, model_for_task
from ai_engine.nl_to_chips import map_nl_to_chips
from ai_engine.soql_templates import build_soql
from api.models.schemas import (
    ChipOption,
    ChipsCandidateDataset,
    ChipsExecuteRequest,
    ChipsExecuteResponse,
    ChipsExplainRequest,
    ChipsExplainResponse,
    ChipsFromNLRequest,
    ChipsFromNLResponse,
    ChipsQueryRequest,
    ChipsQueryResponse,
    ChipsRefineResponse,
    ChipsResponse,
)
from mcp_server.socrata.soda_client import SodaClient

# Timeout más generoso (60s) que el default 30s del cliente — los datasets
# gigantes (ej. SECOPII con 28M filas) toman >30s en GROUP BY. 60s sigue
# protegiendo de abusos pero cubre el long-tail real del catálogo.
_soda_client = SodaClient(timeout=60.0)

router = APIRouter()

# Índice vectorial para el re-ranking semántico de candidatos (lazy: el
# modelo e5 pesa ~280 MB y solo se carga si algún request lo necesita).
# Umbral más permisivo que el del camino generativo: aquí NO decide si hay
# respuesta — solo reordena un subset ya filtrado por chips.
_vindex = None


def _get_vindex():
    global _vindex
    if _vindex is None:
        from ai_engine.vector_index import VectorIndex

        _vindex = VectorIndex(min_score=float(os.getenv("CHIPS_RERANK_MIN_SCORE", "0.78")))
    return _vindex
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
    ChipOption(value="Total", label="Total",
               hint="Suma del valor principal: cuánto vale/cuesta en total"),
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

    - TEMA: todas las categorías canónicas (`datasets.category`) por count.
    - TIPO: 5 fijos (UI determina forma de respuesta).
    - TERRITORIO: Nacional + 32 dptos + 5 macroregiones (ordenados).
    - ENTIDAD: top-20 entities por uso real (telemetría dataset_top1_id).
    """
    with _connect() as conn:
        # TEMA — counts solo de datasets útiles (excluye admin_only).
        # El usuario ve "Educación 1015" representando datos útiles, no
        # esquemas de publicación inflando el número.
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT category, COUNT(*) AS c
                FROM datasets
                WHERE category IS NOT NULL AND category != ''
                  AND (quality_flag IS NULL OR quality_flag = 'ok')
                GROUP BY category
                ORDER BY c DESC
                -- 30 cubre el vocabulario completo (25 canónicas tras la
                -- consolidación de 2026-07-12 + geospatial). El LIMIT 12
                -- original era para el vocabulario sucio de 60+ variantes;
                -- dejaba fuera Agricultura y Seguridad y Defensa, y el
                -- mapper NL no podía elegirlas aunque la pregunta fuera
                -- inequívoca ("producción agrícola" → caía en Comercio).
                LIMIT 30
                """
            )
            temas = [
                ChipOption(value=r["category"], label=r["category"], count=r["c"])
                for r in cur.fetchall()
            ]

        # ENTIDAD — counts solo de datasets útiles. Sin esto, notarías y
        # entidades con muchos esquemas de publicación inflaban el top-20.
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT e.entity_id, e.name AS entity_name, COUNT(d.dataset_id) AS c
                FROM entities e
                LEFT JOIN datasets d ON d.entity_id = e.entity_id
                    AND (d.quality_flag IS NULL OR d.quality_flag = 'ok')
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
    include_low_quality: bool = False,
) -> tuple[str, list[Any]]:
    """Arma la cláusula WHERE compartida entre /query/chips y /chips/refine.

    Devuelve `(where_sql, params)` listos para usar con %s. `where_sql` ya
    incluye `WHERE` cuando hay condiciones, o `TRUE` si no.

    Por default oculta los datasets con `quality_flag` no-NULL (admin_only,
    no_rows, etc.). Pasar `include_low_quality=True` para auditoría.
    """
    where: list[str] = []
    params: list[Any] = []

    if not include_low_quality:
        # NULL = ok = visible. quality_flag asignado = oculto.
        where.append("(d.quality_flag IS NULL OR d.quality_flag = 'ok')")

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
            detail="Marca al menos un chip antes de buscar.",
        )

    # El refinador NO filtra el subset (2026-07-11): a menudo es la palabra
    # clave de la pregunta ("estudiantes") inventada o extraída por el mapper,
    # y como filtro ILIKE literal vaciaba subsets válidos o —peor— al
    # descartarlo se perdía la semántica y se contaba un dataset arbitrario.
    # Ahora es un BOOST de ranking en el score: los datasets que lo mencionan
    # quedan de primeros, y si nada lo menciona el orden normal se mantiene.
    where_sql, params = _build_chips_where(
        tema=req.tema,
        entidad=req.entidad,
        territorio=req.territorio,
        subtags=req.subtags,
        refinador=None,
    )

    # Conteo + top-10
    # Texto del boost de ranking (None → el CASE del SQL rinde 0 para todos).
    refinador_boost = (req.refinador or "").strip() or None

    # Boost POR PALABRAS, no por frase exacta: "tarifas de energía por
    # estrato" debe premiar títulos que contengan "tarifas" y "energía"
    # aunque la frase completa no exista en ningún nombre (con frase exacta
    # el boost valía 0 y ganaba el dataset más popular del tema — caso
    # "prestadores de salud" → medicamentos, 2026-07-12). Palabras de ≥4
    # letras, máximo 5, insensibles a tildes (mismo translate del
    # clasificador 1712); cada una aporta una fracción igual de 0.5.
    _norm_sql = "translate(lower({col}), 'áéíóúüñ', 'aeiouun')"
    palabras = [
        w.lower().translate(str.maketrans("áéíóúüñ", "aeiouun"))
        for w in re.split(r"\W+", refinador_boost or "")
        if len(w) >= 4
    ][:5]
    if palabras:
        frac = round(0.5 / len(palabras), 4)
        boost_sql = " + ".join(
            f"CASE WHEN {_norm_sql.format(col='s.name')} LIKE %s"
            f" OR {_norm_sql.format(col='s.description')} LIKE %s"
            f" THEN {frac} ELSE 0 END"
            for _ in palabras
        )
        boost_params: list = []
        for w in palabras:
            boost_params += [f"%{w}%", f"%{w}%"]
    else:
        boost_sql = "0"
        boost_params = []

    # Preguntas DEPARTAMENTALES prefieren datasets de alcance departamental o
    # nacional: con territorio='05' el subset incluye datasets de cada
    # municipio de Antioquia y el top ciego elegía uno ("Instituciones
    # Educativas de Yondó" para "¿cuántas IE hay en Antioquia?", 2026-07-12).
    # Es un boost, no un filtro: los municipales siguen como candidatos.
    # Simétrico para las NACIONALES: "homicidios en Colombia" caía en el
    # dataset de Cali (43 filas presentadas como cifra nacional, ciclo
    # ciudadano c13 2026-07-12).
    es_dpto = bool(req.territorio and re.fullmatch(r"\d{2}", req.territorio))
    es_nacional = req.territorio == "nacional"

    def _run(where_sql: str, params: list) -> tuple[int, list]:
        """Conteo + top-10 con score compuesto para un WHERE dado."""
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
                # NaN. El COALESCE EXTERNO del término de popularidad es clave:
                # si TODO el subset es federado sin view_count, max_view=1 →
                # LN(1)=0 → NULLIF lo vuelve NULL y sin COALESCE el score entero
                # quedaba NULL para todos (orden degradado a popularidad cruda).
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
                           s.source_type, s.federated_status,
                           (
                             COALESCE(
                               %s * (LN(GREATEST(COALESCE(s.view_count, 0), 1)) /
                                     NULLIF(LN((SELECT max_view FROM stats)), 0)),
                               0
                             )
                             +
                             %s * GREATEST(0, 1 - LEAST(1,
                                EXTRACT(EPOCH FROM (NOW() - s.rows_updated_at)) /
                                (%s * 2 * 86400)
                             ))
                             +
                             ({boost_sql})
                             +
                             CASE WHEN %s AND s.jurisdiccion_nivel IN
                                    ('departamental', 'nacional')
                                  THEN 0.3 ELSE 0 END
                             +
                             CASE WHEN %s AND s.jurisdiccion_nivel = 'nacional'
                                  THEN 0.3 ELSE 0 END
                           ) AS score
                    FROM subset s
                    ORDER BY score DESC NULLS LAST,
                             s.view_count DESC NULLS LAST,
                             s.rows_updated_at DESC NULLS LAST
                    LIMIT 50
                    """,
                    params + [
                        _SCORE_W_VIEW, _SCORE_W_FRESHNESS, _FRESHNESS_HALF_LIFE_DAYS,
                    ] + boost_params + [es_dpto, es_nacional],
                )
                rows = cur.fetchall()
        return total, rows

    total, rows = _run(where_sql, params)

    # ---- Re-ranking SEMÁNTICO (ciclo ciudadano 2026-07-12) ----
    # El score SQL (popularidad + palabras del refinador) no acota
    # semánticamente: cuando ninguna palabra matchea, gana el dataset más
    # popular del tema ("¿parques nacionales?" → Lotería de Santander). El
    # índice vectorial e5 YA rankea por significado en el camino generativo;
    # aquí re-rankea el top-50 del subset: el chip filtra, el embedding
    # ordena. Falla silenciosa → queda el orden SQL.
    aviso_lejania: str | None = None
    if refinador_boost and rows:
        try:
            hits = {
                h.id: h.score
                for h in _get_vindex().search(refinador_boost, k=100)
            }
            if not hits:
                # Honestidad: nada del catálogo se parece semánticamente a lo
                # pedido. Se responde igual (el más relacionado del tema) pero
                # SIN fingir que es exactamente lo que se buscó.
                aviso_lejania = (
                    f"Ningún dataset del catálogo coincide de cerca con "
                    f"«{refinador_boost}»; te muestro lo más relacionado del tema."
                )
            if hits:
                s_min, s_max = min(hits.values()), max(hits.values())
                rango = (s_max - s_min) or 1.0

                def _score_final(r: dict) -> float:
                    sql_score = float(r.get("score") or 0)
                    sem = hits.get(r["dataset_id"])
                    if sem is None:
                        return sql_score
                    return sql_score + 1.2 * ((sem - s_min) / rango + 0.25)

                rows = sorted(rows, key=_score_final, reverse=True)
                for r in rows:
                    r["score"] = round(_score_final(r), 4)
        except Exception as exc:  # noqa: BLE001
            log.warning("Re-rank semántico falló (%s) — orden SQL", exc)
    rows = rows[:10]

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

    if aviso_lejania:
        msg = aviso_lejania

    if req.force_dataset_id:
        chosen = req.force_dataset_id
    elif total == 0:
        msg = "Ningún dataset coincide con esta combinación de chips. Prueba quitar alguno."
    elif total <= 10 or req.tipo:
        # Subset manejable o usuario ya marcó TIPO → ejecutar sobre el primer
        # candidato QUE PUEDA PRODUCIR DATOS. Un federado solo_metadatos
        # (no_csv) no tiene filas que contar: elegirlo devolvía cifra None
        # silenciosa (caso real n6k3-wycd, 2026-07-11).
        ejecutables = [
            r for r in rows
            if r.get("source_type") == "socrata" or r.get("federated_status") == "ok"
        ]
        # El elegido además debe SOPORTAR el TIPO pedido: Tendencia necesita
        # una columna fecha y Mapa una geo. Elegir el top ciego producía
        # errores honestos evitables ("evolución de homicidios" → dataset sin
        # fecha) cuando el candidato #2 sí podía responder (2026-07-12). Solo
        # se conoce el esquema curado de los nativos; los federados quedan
        # como respaldo (su CSV puede tener la columna). Si ninguno soporta
        # el TIPO, cae al comportamiento anterior (error honesto).
        necesita = {"Tendencia": "fecha", "Mapa": "geo"}.get(req.tipo or "")
        if necesita and ejecutables:
            nativos = [r["dataset_id"] for r in ejecutables
                       if r.get("source_type") == "socrata"]
            capaces: set[str] = set()
            if nativos:
                with _connect() as conn, conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT DISTINCT dataset_id FROM dataset_columns_curated
                        WHERE dataset_id = ANY(%s) AND semantic_type = %s
                        """,
                        (nativos, necesita),
                    )
                    capaces = {r["dataset_id"] for r in cur.fetchall()}
            compatible = next(
                (r for r in ejecutables if r["dataset_id"] in capaces), None
            ) or next(
                (r for r in ejecutables if r.get("source_type") == "federated"),
                None,
            )
            if compatible is not None:
                ejecutables = [compatible]
        if ejecutables:
            chosen = ejecutables[0]["dataset_id"]
        elif candidates:
            msg = (
                "Estos datasets solo son consultables en su portal de origen "
                "(no exponen tabla de datos). Abre la fuente para verlos."
            )
    else:
        # Subset grande sin TIPO marcado → sugerir refinar
        msg = f"Hay {total} datasets que coinciden. Marca otro chip para verlos más específicos."
        suggested = _suggest_chips(req)

    return ChipsQueryResponse(
        total_in_subset=total,
        candidates=candidates,
        chosen_dataset_id=chosen,
        suggested_chips=suggested,
        message=msg,
    )


# ----------------------------------------------------------------------
# POST /api/v1/query/chips/execute (Fase B — motor SoQL determinista)
# ----------------------------------------------------------------------


import time as _time


def _merge_categorias_duplicadas(resp: ChipsExecuteResponse) -> ChipsExecuteResponse:
    """Funde filas de Comparar/Ranking cuya categoría difiere solo en
    mayúsculas/tildes ("Transporte" + "TRANSPORTE" del SIIF, 2026-07-12).

    El dato de origen viene sucio y el GROUP BY los separa; para el ciudadano
    son la misma barra. Se queda la etiqueta de la variante con mayor valor y
    se suman los valores. Solo toca la forma {categoria, n|total}.
    """
    if resp.tipo not in ("Comparar", "Ranking") or not resp.rows:
        return resp
    metrica = "total" if "total" in resp.rows[0] else "n"
    if "categoria" not in resp.rows[0] or metrica not in resp.rows[0]:
        return resp
    tabla = str.maketrans("áéíóúüñ", "aeiouun")
    grupos: dict[str, dict] = {}
    for r in resp.rows:
        cat = str(r.get("categoria") or "")
        try:
            val = float(r.get(metrica) or 0)
        except (TypeError, ValueError):
            return resp  # métrica no numérica: no tocar
        clave = cat.strip().lower().translate(tabla)
        g = grupos.setdefault(clave, {"categoria": cat, "valor": 0.0, "mayor": -1.0})
        g["valor"] += val
        if val > g["mayor"]:
            g["mayor"] = val
            g["categoria"] = cat
    if len(grupos) == len(resp.rows):
        return resp  # no había duplicados
    fundidas = sorted(grupos.values(), key=lambda g: g["valor"], reverse=True)
    resp.rows = [
        {"categoria": g["categoria"],
         metrica: int(g["valor"]) if g["valor"].is_integer() else g["valor"]}
        for g in fundidas
    ]
    resp.row_count = len(resp.rows)
    return resp


@router.post("/query/chips/execute", response_model=ChipsExecuteResponse)
async def query_chips_execute(req: ChipsExecuteRequest) -> ChipsExecuteResponse:
    return _merge_categorias_duplicadas(await _query_chips_execute_impl(req))


async def _query_chips_execute_impl(req: ChipsExecuteRequest) -> ChipsExecuteResponse:
    """Ejecuta una consulta SoQL determinista sobre el dataset elegido.

    Flujo:
      1. Lee `source_type` y columnas curadas del dataset desde Postgres.
      2. Si el dataset NO es nativo (`source_type='socrata'`) → 400 con
         explicación (los federados se ejecutan vía DuckDB en Reto F.4).
      3. Construye SoQL con `build_soql(tipo, by_type)` — pura Python.
      4. Ejecuta vía `SodaClient.query()` contra `https://www.datos.gov.co`.
      5. Devuelve `{soql, columns_used, rows, row_count}` para transparencia.

    Errores comunes:
      404 si dataset no existe o no tiene curación.
      400 si dataset es federated_href o si TIPO no se puede construir
          (falta una columna semántica requerida).
      502 si SODA falla (timeout / SoQL inválido).
    """
    t0 = _time.time()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.source_type, d.row_count, d.data_url, d.federated_status,
                       s.parquet_path,
                       (s.status = 'downloaded'
                        AND s.parquet_path IS NOT NULL
                        AND s.source_updated_at IS NOT DISTINCT FROM d.rows_updated_at
                       ) AS snapshot_fresco
                FROM datasets d
                LEFT JOIN dataset_snapshots s USING (dataset_id)
                WHERE d.dataset_id = %s
                """,
                (req.dataset_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Dataset {req.dataset_id!r} no existe en el catálogo",
                )
            source_type = row["source_type"]
            local_row_count = row["row_count"]
            data_url = row["data_url"]
            federated_status = row["federated_status"]

            # ---- Rama BODEGA (farmeo): Parquet local, sin red, milisegundos ----
            # Mecanismo de decisión bodega-vs-vivo: si el dataset está en la
            # bodega Y su snapshot es FRESCO (source_updated_at == el
            # rows_updated_at actual del catálogo — la regla diaria lo
            # mantiene), se consulta el Parquet local. Si el catálogo dice que
            # la fuente cambió y la bodega aún no refresca, se cae al camino
            # VIVO (SODA/CSV) — preferimos el dato más nuevo a la velocidad.
            # Cualquier fallo local degrada silenciosamente al camino vivo.
            # Mapa NUNCA va a la bodega: el choropleth casa por código
            # DIVIPOLA y el heurístico sobre el Parquet elige columnas de
            # NOMBRE ("Departamento" → 'ANTIOQUIA'), que el mapa no pinta.
            # El camino vivo (columnas curadas SODA) sí produce códigos.
            if row["snapshot_fresco"] and req.tipo != "Mapa":
                try:
                    lake_cols = describe_parquet(row["parquet_path"])
                    built = build_duckdb_sql(req.tipo, lake_cols, row["parquet_path"])
                    if not built.error:
                        rows_out = execute_parquet(row["parquet_path"], built.sql)
                        rows_norm = [
                            {k: (v if isinstance(v, (str, int, float, bool, type(None))) else str(v))
                             for k, v in r.items()}
                            for r in rows_out
                        ]
                        emit_event(
                            endpoint="execute", dataset_id=req.dataset_id,
                            tipo=req.tipo, source_type="lake",
                            elapsed_ms=int((_time.time()-t0)*1000),
                            row_count=len(rows_norm), soql_chars=len(built.sql),
                        )
                        return ChipsExecuteResponse(
                            dataset_id=req.dataset_id,
                            tipo=req.tipo,
                            soql=built.sql,
                            columns_used=built.columns_used,
                            rows=rows_norm,
                            row_count=len(rows_norm),
                        )
                except Exception as exc:  # noqa: BLE001 — degradar a vivo
                    log.warning(
                        "Bodega falló para %s (%s) — degradando a vivo",
                        req.dataset_id, exc,
                    )

            # ---- Rama FEDERADO (Reto F.4 — DuckDB sobre CSV externo) ----
            if source_type == "federated":
                if federated_status != "ok" or not data_url:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Dataset {req.dataset_id!r} es federado pero no "
                            "expone CSV consultable (federated_status="
                            f"{federated_status!r}). Sólo es descubrible."
                        ),
                    )
                # Guarda de tamaño: consultar en vivo un CSV federado gigante
                # revienta el timeout del gateway (502 con gwqv-sqvs,
                # 2026-07-12). Si el origen declara Content-Length por encima
                # del tope, respuesta honesta inmediata en vez de colgarse.
                try:
                    head = httpx.head(data_url, follow_redirects=True, timeout=6)
                    fed_bytes = int(head.headers.get("content-length") or 0)
                except Exception:  # noqa: BLE001 — sin HEAD, se intenta igual
                    fed_bytes = 0
                if fed_bytes > 250 * 1024 * 1024:
                    friendly = (
                        "El archivo de este dataset pesa "
                        f"{fed_bytes / (1024 * 1024):.0f} MB — demasiado para "
                        "consultarlo en vivo. Descárgalo desde su portal de origen."
                    )
                    emit_event(
                        endpoint="execute", dataset_id=req.dataset_id, tipo=req.tipo,
                        source_type="federated",
                        elapsed_ms=int((_time.time()-t0)*1000),
                        row_count=0, error=friendly,
                    )
                    return ChipsExecuteResponse(
                        dataset_id=req.dataset_id,
                        tipo=req.tipo,
                        soql="",
                        columns_used=[],
                        rows=[],
                        row_count=0,
                        error=friendly,
                    )
                # Descubrir columnas via DuckDB DESCRIBE (sin descargar filas).
                try:
                    fed_cols = describe_csv(data_url)
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "DuckDB DESCRIBE %s falló: %s", req.dataset_id, exc
                    )
                    # HTTP errors (403/404/timeout) → mensaje legible en
                    # `error` con 200, no 502. El frontend ya tiene un
                    # panel apropiado para mostrarlo.
                    msg = str(exc)
                    if "HTTP" in msg or "403" in msg or "404" in msg:
                        friendly = (
                            "El portal del federado no devolvió el archivo "
                            "(probablemente protegido o caducado)."
                        )
                    elif "encod" in msg.lower() or "unicode" in msg.lower():
                        friendly = (
                            "El CSV tiene una codificación que no pudimos "
                            "leer (no UTF-8 / latin-1 / UTF-16)."
                        )
                    else:
                        friendly = f"No pudimos leer el CSV federado: {msg[:120]}"
                    emit_event(
                        endpoint="execute", dataset_id=req.dataset_id, tipo=req.tipo,
                        source_type="federated",
                        elapsed_ms=int((_time.time()-t0)*1000),
                        row_count=0, error=friendly,
                    )
                    return ChipsExecuteResponse(
                        dataset_id=req.dataset_id,
                        tipo=req.tipo,
                        soql="",
                        columns_used=[],
                        rows=[],
                        row_count=0,
                        error=friendly,
                    )
                built = build_duckdb_sql(req.tipo, fed_cols, data_url)
                if built.error:
                    emit_event(
                        endpoint="execute", dataset_id=req.dataset_id, tipo=req.tipo,
                        source_type="federated",
                        elapsed_ms=int((_time.time()-t0)*1000),
                        row_count=0, error=built.error,
                    )
                    return ChipsExecuteResponse(
                        dataset_id=req.dataset_id,
                        tipo=req.tipo,
                        soql="",
                        columns_used=[],
                        rows=[],
                        row_count=0,
                        error=built.error,
                    )
                try:
                    rows_out = execute_csv(data_url, built.sql)
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "DuckDB execute %s falló: %s", req.dataset_id, exc
                    )
                    emit_event(
                        endpoint="execute", dataset_id=req.dataset_id, tipo=req.tipo,
                        source_type="federated",
                        elapsed_ms=int((_time.time()-t0)*1000),
                        soql_chars=len(built.sql), error=str(exc)[:200],
                    )
                    raise HTTPException(
                        status_code=502, detail=str(exc)
                    ) from exc
                # Normaliza valores no-JSON (datetime, Decimal) a string.
                rows_norm = [
                    {k: (v if isinstance(v, (str, int, float, bool, type(None))) else str(v))
                     for k, v in r.items()}
                    for r in rows_out
                ]
                emit_event(
                    endpoint="execute", dataset_id=req.dataset_id, tipo=req.tipo,
                    source_type="federated",
                    elapsed_ms=int((_time.time()-t0)*1000),
                    row_count=len(rows_norm), soql_chars=len(built.sql),
                )
                return ChipsExecuteResponse(
                    dataset_id=req.dataset_id,
                    tipo=req.tipo,
                    soql=built.sql,
                    columns_used=built.columns_used,
                    rows=rows_norm,
                    row_count=len(rows_norm),
                )

            # ---- Rama NATIVO (Fase B — SoQL contra SODA) ----
            if source_type != "socrata":
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Dataset {req.dataset_id!r} tiene source_type "
                        f"{source_type!r} no soportado."
                    ),
                )

            # Fast-path para Cuántos: Hito Q.7.b probó que `row_count` local
            # tiene 0% drift vs SODA live (293/293 muestras). Sirvo desde
            # Postgres → instantáneo y cubre datasets de >10M filas que
            # excederían el timeout 60s del SodaClient (ej. SECOPII 28M).
            if req.tipo == "Cuántos" and local_row_count is not None:
                soql = "SELECT count(*) AS n"
                emit_event(
                    endpoint="execute", dataset_id=req.dataset_id, tipo=req.tipo,
                    source_type="socrata",
                    elapsed_ms=int((_time.time()-t0)*1000),
                    row_count=1, soql_chars=len(soql),
                )
                return ChipsExecuteResponse(
                    dataset_id=req.dataset_id,
                    tipo=req.tipo,
                    soql=soql,
                    columns_used=[],
                    rows=[{"n": str(local_row_count)}],
                    row_count=1,
                )

            cur.execute(
                """
                SELECT col_name, semantic_type, semantic_subtype, socrata_data_type
                FROM dataset_columns_curated
                WHERE dataset_id = %s
                ORDER BY
                    CASE confidence WHEN 'high' THEN 0 WHEN 'medium' THEN 1
                                    WHEN 'low' THEN 2 ELSE 3 END,
                    col_name
                """,
                (req.dataset_id,),
            )
            cols = cur.fetchall()

    built = build_soql(req.tipo, list(cols))
    if built.error:
        # No es 5xx — el dataset no soporta este TIPO. El cliente puede
        # ofrecer otro TIPO o explicar al usuario por qué falla.
        emit_event(
            endpoint="execute", dataset_id=req.dataset_id, tipo=req.tipo,
            source_type="socrata", elapsed_ms=int((_time.time()-t0)*1000),
            row_count=0, error=built.error,
        )
        return ChipsExecuteResponse(
            dataset_id=req.dataset_id,
            tipo=req.tipo,
            soql="",
            columns_used=[],
            rows=[],
            row_count=0,
            error=built.error,
        )

    try:
        rows = await _soda_client.query(req.dataset_id, soql_query=built.soql)
    except httpx.HTTPStatusError as exc:
        log.warning(
            "SODA %s falló (%s): %s",
            req.dataset_id, exc.response.status_code, built.soql,
        )
        emit_event(
            endpoint="execute", dataset_id=req.dataset_id, tipo=req.tipo,
            source_type="socrata", elapsed_ms=int((_time.time()-t0)*1000),
            soql_chars=len(built.soql),
            error=f"SODA {exc.response.status_code}",
        )
        raise HTTPException(
            status_code=502,
            detail=f"SODA respondió {exc.response.status_code}",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        log.warning("SODA %s falló: %s", req.dataset_id, exc)
        emit_event(
            endpoint="execute", dataset_id=req.dataset_id, tipo=req.tipo,
            source_type="socrata", elapsed_ms=int((_time.time()-t0)*1000),
            soql_chars=len(built.soql), error=str(exc)[:200],
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    emit_event(
        endpoint="execute", dataset_id=req.dataset_id, tipo=req.tipo,
        source_type="socrata", elapsed_ms=int((_time.time()-t0)*1000),
        row_count=len(rows), soql_chars=len(built.soql),
    )
    return ChipsExecuteResponse(
        dataset_id=req.dataset_id,
        tipo=req.tipo,
        soql=built.soql,
        columns_used=built.columns_used,
        rows=rows,
        row_count=len(rows),
    )


# ----------------------------------------------------------------------
# POST /api/v1/query/chips/explain (Hito 1 Fase D — narrativa LLM)
# ----------------------------------------------------------------------


import json as _json
import re as _re


# Token numérico = secuencia continua de dígitos y separadores (punto/coma).
# Capturamos como un solo grupo cifras con miles formateados ("9.192.802.561.842")
# en vez de partirlas en pedacitos.
_NUMBER_TOKEN_RE = _re.compile(r"-?\d[\d.,]*")

# Denominadores estadísticos ambient — el LLM los usa como contexto
# ("por cada 1000 habitantes", "del 100%") sin que vengan de los datos.
_AMBIENT_DENOMINATORS = {"100", "1000", "10000", "100000", "1000000"}


def _normalize_digits(token: str) -> str:
    """Quita todos los separadores. '9.192.802.561.842' → '9192802561842'."""
    return _re.sub(r"[.,]", "", token.lstrip("-"))


def _allowed_numbers(rows: list[dict]) -> set[str]:
    """Conjunto de strings de SOLO DÍGITOS de cualquier valor numérico que
    aparezca en las filas. También incluye los prefijos de >= 4 dígitos
    (cubre cuando el LLM redondea/trunca, ej. devuelve "9 billones" cuando
    el valor real es 9192802561842)."""
    out: set[str] = set()
    for row in rows or []:
        for v in row.values():
            if v is None:
                continue
            s = str(v)
            for m in _NUMBER_TOKEN_RE.finditer(s):
                norm = _normalize_digits(m.group(0))
                if not norm:
                    continue
                out.add(norm)
    return out


def _validate_numbers(narrative: str, rows: list[dict]) -> list[str]:
    """Lista los números en la narrativa que NO aparecen en `rows`.
    Vacía → narrativa segura.

    Acepta:
      * Años 1900-2099 sin verificar.
      * Números de 1 dígito (0-9) — el LLM los usa como cardinales ("3 categorías")
        sin que sean cifras del catálogo; son ruido inevitable.
    """
    allowed = _allowed_numbers(rows)
    flagged: list[str] = []
    for m in _NUMBER_TOKEN_RE.finditer(narrative):
        token = m.group(0)
        norm = _normalize_digits(token)
        if not norm or not norm.isdigit():
            continue
        if len(norm) == 1:
            continue
        if len(norm) == 4 and 1900 <= int(norm) <= 2099:
            continue
        if norm in _AMBIENT_DENOMINATORS:
            continue
        if norm in allowed:
            continue
        flagged.append(token)
    return flagged


def _format_for_prompt(rows: list[dict]) -> str:
    """Pre-formatea cifras grandes en castellano legible para que el LLM no
    tenga que contar ceros. Solo afecta el texto que ve el modelo —
    la validación corre contra los `rows` originales."""
    out = []
    for r in rows:
        clone: dict[str, str] = {}
        for k, v in r.items():
            if v is None:
                clone[k] = "null"
                continue
            s = str(v)
            try:
                # Detectar enteros grandes (con o sin separadores).
                n = int(_normalize_digits(s)) if s.replace(".", "").replace(",", "").isdigit() else None
            except Exception:
                n = None
            if n is None or n < 1_000_000:
                clone[k] = s
            else:
                # Formatear con separadores de miles para que el LLM no
                # tenga que decidir cuántos ceros poner.
                clone[k] = f"{n:,}".replace(",", ".")
        out.append(clone)
    return _json.dumps(out, ensure_ascii=False)


_EXPLAIN_PROMPT = """Eres un explicador de cifras públicas colombianas para ciudadanos.

Dataset: {dataset_name}
TIPO de consulta: {tipo}
Datos resultantes (JSON):
{rows_json}

Reglas estrictas:
- 2 frases en español neutro. NO uses listas.
- Empieza con la cifra principal.
- NO INVENTES números. Cada cifra que menciones DEBE estar en los datos arriba.
- Si la cifra es 0 o vacía, di "no se reportaron datos" sin más.

Respuesta:"""


@router.post("/query/chips/explain", response_model=ChipsExplainResponse)
async def query_chips_explain(req: ChipsExplainRequest) -> ChipsExplainResponse:
    """Narrativa corta sobre el resultado YA verificado. ADR-017: el LLM
    razona sobre un substrato determinista — nunca produce la cifra."""
    t0 = _time.time()
    if not req.rows:
        emit_event(
            endpoint="explain", dataset_id=req.dataset_id, tipo=req.tipo,
            elapsed_ms=int((_time.time()-t0)*1000), row_count=0,
        )
        return ChipsExplainResponse(
            dataset_id=req.dataset_id,
            tipo=req.tipo,
            narrative="No se reportaron datos para esta combinación.",
            model="(skipped)",
        )

    # Recorta filas para no inflar el prompt: top-10 es suficiente para
    # cualquier TIPO (Cuántos=1, Comparar/Ranking=10, Mapa/Tendencia trunca).
    # Pre-formateamos cifras grandes para que el LLM no tenga que contar
    # ceros — esto reduce alucinaciones de magnitud en Ranking.
    sample = req.rows[:10]
    rows_json = _format_for_prompt(sample)
    prompt = _EXPLAIN_PROMPT.format(
        dataset_name=req.dataset_name,
        tipo=req.tipo,
        rows_json=rows_json,
    )

    backend = get_backend()
    model = model_for_task("narrative")
    try:
        narrative = await backend.generate(prompt, max_tokens=180, model=model)
    except Exception as exc:  # noqa: BLE001
        log.warning("LLM explain falló para %s: %s", req.dataset_id, exc)
        emit_event(
            endpoint="explain", dataset_id=req.dataset_id, tipo=req.tipo,
            elapsed_ms=int((_time.time()-t0)*1000),
            error=f"LLM: {str(exc)[:150]}",
        )
        return ChipsExplainResponse(
            dataset_id=req.dataset_id,
            tipo=req.tipo,
            narrative="",
            model=model,
            error=str(exc),
        )

    narrative = (narrative or "").strip()
    flagged = _validate_numbers(narrative, req.rows)
    if flagged:
        emit_event(
            endpoint="explain", dataset_id=req.dataset_id, tipo=req.tipo,
            elapsed_ms=int((_time.time()-t0)*1000),
            hallucinated=len(flagged),
            error="censored",
        )
        return ChipsExplainResponse(
            dataset_id=req.dataset_id,
            tipo=req.tipo,
            narrative="",
            hallucinated_numbers=flagged,
            model=model,
            error="Narrativa censurada: contiene cifras que no están en los datos.",
        )

    emit_event(
        endpoint="explain", dataset_id=req.dataset_id, tipo=req.tipo,
        elapsed_ms=int((_time.time()-t0)*1000),
    )
    return ChipsExplainResponse(
        dataset_id=req.dataset_id,
        tipo=req.tipo,
        narrative=narrative,
        model=model,
    )


# ----------------------------------------------------------------------
# Señales léxicas → TIPO. Orden = prioridad; "cuánt" es la más fuerte y
# además la única que puede SOBREESCRIBIR al LLM (ver chips_from_nl).
_TIPO_LEXICO: list[tuple[re.Pattern[str], str]] = [
    # "cuánto ha subido/bajado" pregunta por la EVOLUCIÓN de un valor, no por
    # un conteo — va antes que el resto (ciclo ciudadano c28, 2026-07-12).
    (re.compile(r"cu[aá]nto han? (subido|bajado|crecido|aumentado|cambiado|variado)",
                re.IGNORECASE), "Tendencia"),
    # "en qué gasta/invierte" pide el desglose, no el total (c19).
    (re.compile(r"en qu[eé] (se )?(gasta|invierte)", re.IGNORECASE), "Comparar"),
    # "cuánto vale/cuesta/cuánta plata" pide la SUMA del valor, no un
    # conteo de filas (ciclo ciudadano c17/c20/c50, 2026-07-12).
    (re.compile(r"cu[aá]nto (vale|cuesta|gana|debe|recauda|dinero)"
                r"|cu[aá]nta plata|a cu[aá]nto asciende|valor total|monto total",
                re.IGNORECASE), "Total"),
    # SOLO el plural es conteo: "¿cuántos contratos?" cuenta filas, pero
    # "¿cuánto vale la deuda?" pide un MONTO — forzar Cuántos ahí producía
    # conteos irrelevantes presentados como cifra verificada (c17, c20, c50).
    (re.compile(r"\bcu[aá]nt[oa]s\b", re.IGNORECASE), "Cuántos"),
    (re.compile(r"\b(comparar?|versus|vs\.?|frente a)\b", re.IGNORECASE), "Comparar"),
    (re.compile(r"\b(ranking|top \d+|top\b|mayores|m[aá]s alt[oa]s)\b", re.IGNORECASE), "Ranking"),
    (re.compile(r"\b(tendencia|evoluci[oó]n|hist[oó]rico|a lo largo)\b", re.IGNORECASE), "Tendencia"),
    (re.compile(r"\b(mapa|d[oó]nde)\b", re.IGNORECASE), "Mapa"),
]


def _infer_tipo_lexico(q: str) -> str | None:
    """TIPO por señal léxica inequívoca, o None si no hay ninguna."""
    for pattern, tipo in _TIPO_LEXICO:
        if pattern.search(q):
            return tipo
    return None


# Señales léxicas → TEMA. Solo entradas con evidencia de fallo del mapper
# (2026-07-12: "producción agrícola" → Comercio; "estaciones de policía" →
# Función pública). Inequívocas y cortas a propósito: un guardrail, no un
# clasificador. Solo aplican si el tema existe en las listas de la BD.
_TEMA_LEXICO: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"agr[ií]col|agricultur|cultivo|cosecha|ganader|pecuari",
                re.IGNORECASE), "Agricultura y Desarrollo Rural"),
    (re.compile(r"polic[ií]a|homicid|hurto|delito|secuestro|extorsi[oó]n",
                re.IGNORECASE), "Seguridad y Defensa"),
]


def _infer_tema_lexico(q: str) -> str | None:
    """TEMA por señal léxica inequívoca, o None si no hay ninguna."""
    for pattern, tema in _TEMA_LEXICO:
        if pattern.search(q):
            return tema
    return None


# ----------------------------------------------------------------------
# POST /api/v1/chips/from-nl (Hito 1 Fase 2 — mapper NL→chips)
# ----------------------------------------------------------------------


@router.post("/chips/from-nl", response_model=ChipsFromNLResponse)
async def chips_from_nl(req: ChipsFromNLRequest) -> ChipsFromNLResponse:
    """Texto libre → combinación de chips pre-marcada.

    Pipeline:
      1. Carga chips disponibles (mismas listas que `GET /chips`).
      2. Pide al LLM mapear el texto a {tema, tipo, territorio, entidad,
         refinador} eligiendo SOLO valores presentes en las listas.
      3. Valida la respuesta y descarta opciones inválidas.

    El frontend usa la respuesta para navegar a
    `/buscar?tema=X&tipo=Y&...` y disparar el flujo de chips.
    """
    t0 = _time.time()
    chips = await list_chips()
    available = {
        "tema": [opt.value for opt in chips.tema],
        "territorio": [{"value": opt.value, "label": opt.label} for opt in chips.territorio],
        "entidad": [{"value": opt.value, "label": opt.label} for opt in chips.entidad],
    }
    mapped = await map_nl_to_chips(req.q, available)

    # Heurística léxica de TIPO (barata, determinista, corre después del LLM):
    # "¿Cuántos…?" es señal inequívoca de conteo y el mapper LLM la pierde o
    # la confunde con frecuencia (medido 2026-07-10: tipo=null o "Ranking"
    # para preguntas de conteo). La señal fuerte SIEMPRE gana; las demás solo
    # rellenan si el LLM no propuso tipo.
    tipo_lexico = _infer_tipo_lexico(req.q)
    if tipo_lexico in ("Cuántos", "Total"):
        # Señales inequívocas que SOBREESCRIBEN al LLM: el plural cuenta y
        # "cuánto vale/cuesta" suma — el mapper insistía en Cuántos para
        # montos (ciclo 3, 2026-07-13) y el conteo de filas es la respuesta
        # equivocada a una pregunta de plata.
        mapped["tipo"] = tipo_lexico
    elif tipo_lexico and not mapped.get("tipo"):
        mapped["tipo"] = tipo_lexico

    # Guardrail léxico de TEMA: señales inequívocas ganan al LLM (medido:
    # el mapper puso "producción agrícola" en Comercio y "policía" en
    # Función pública). Solo si el tema existe en las listas reales.
    tema_lexico = _infer_tema_lexico(req.q)
    if tema_lexico and tema_lexico in available["tema"]:
        mapped["tema"] = tema_lexico

    # "Mi ciudad / donde vivo" no es adivinable: en vez de responder con el
    # dato de OTRO municipio como si fuera el suyo (ciclo ciudadano c01/c06,
    # 2026-07-12), se pide el territorio explícito.
    hint = None
    if not mapped.get("territorio") and re.search(
        r"\bmi (ciudad|municipio|barrio|departamento|alcald[ií]a|localidad|regi[oó]n|eps)\b"
        r"|donde vivo|cerca de (mi casa|donde vivo)",
        req.q, re.IGNORECASE,
    ):
        hint = (
            "La pregunta habla de TU territorio y no puedo adivinarlo: "
            "márcalo en el chip Territorio para una respuesta local."
        )

    picked = sum(1 for v in mapped.values() if v is not None)
    emit_event(
        endpoint="from_nl",
        elapsed_ms=int((_time.time()-t0)*1000),
        nl_query=req.q,
        chips_picked=picked,
        tipo=mapped.get("tipo"),
    )
    return ChipsFromNLResponse(
        tema=mapped.get("tema"),
        tipo=mapped.get("tipo"),
        territorio=mapped.get("territorio"),
        entidad=mapped.get("entidad"),
        refinador=mapped.get("refinador"),
        hint=hint,
    )
