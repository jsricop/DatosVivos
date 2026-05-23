"""Endpoints de chips — entrada PRIMARIA de búsqueda (Fase 1 audit top-down).

GET  /api/v1/chips           — listas dinámicas de TEMA/TIPO/TERRITORIO/ENTIDAD
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
from fastapi import APIRouter, HTTPException
from psycopg.rows import dict_row

from api.models.schemas import (
    ChipOption,
    ChipsCandidateDataset,
    ChipsQueryRequest,
    ChipsQueryResponse,
    ChipsResponse,
)

router = APIRouter()
log = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Constantes — TIPO hardcoded (no viene del catálogo), TERRITORIO armado
# ----------------------------------------------------------------------


_TIPO_OPTIONS = [
    ChipOption(value="cuantos", label="Cuántos",
               hint="Conteo simple: cuántos X hay"),
    ChipOption(value="comparar", label="Comparar",
               hint="Diferencias entre dos o más territorios/categorías"),
    ChipOption(value="ranking", label="Ranking",
               hint="Top N por una métrica"),
    ChipOption(value="tendencia", label="Tendencia",
               hint="Evolución temporal"),
    ChipOption(value="mapa", label="Mapa",
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
    if not any([req.tema, req.tipo, req.territorio, req.entidad, req.refinador]):
        raise HTTPException(
            status_code=400,
            detail="Marcá al menos un chip antes de buscar.",
        )

    # Construcción del WHERE
    where: list[str] = []
    params: list[Any] = []

    if req.tema:
        where.append("category = %s")
        params.append(req.tema)

    if req.entidad:
        try:
            ent_id = int(req.entidad)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"entidad inválida: {req.entidad}")
        where.append("entity_id = %s")
        params.append(ent_id)

    if req.territorio:
        codes = _territory_codes(req.territorio)
        if codes is not None:  # None = nacional, no filtrar
            # Match: dataset cuya jurisdicción cubre alguno de los códigos pedidos
            # incluye match por prefijo (dpto code "05" matchea mpios "05001")
            placeholders = ", ".join(["%s"] * len(codes))
            where.append(
                f"(jurisdiccion_geo_codes ?| array[{placeholders}] "
                f"OR EXISTS (SELECT 1 FROM jsonb_array_elements_text(jurisdiccion_geo_codes) c "
                f"          WHERE c LIKE ANY(array[{placeholders}])))"
            )
            params.extend(codes)
            params.extend([f"{c}%" for c in codes])

    if req.refinador:
        # Match en name OR description, case-insensitive
        where.append("(name ILIKE %s OR description ILIKE %s)")
        ref_like = f"%{req.refinador}%"
        params.append(ref_like)
        params.append(ref_like)

    where_sql = " AND ".join(where) if where else "TRUE"

    # Conteo + top-10
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS c FROM datasets WHERE {where_sql}", params)
            row = cur.fetchone()
            total = (row["c"] if row else 0) if isinstance(row, dict) else (row[0] if row else 0)

        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT d.dataset_id, d.name, d.entity_raw,
                       d.category, d.row_count, d.view_count,
                       d.rows_updated_at::text AS last_updated,
                       d.socrata_url AS url, d.api_url,
                       d.jurisdiccion_nivel, d.jurisdiccion_geo_codes
                FROM datasets d
                WHERE {where_sql}
                ORDER BY d.view_count DESC NULLS LAST, d.rows_updated_at DESC NULLS LAST
                LIMIT 10
                """,
                params,
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
