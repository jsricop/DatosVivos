"""Modelos Pydantic para requests y responses de la API.

Contratos versionados bajo `/api/v1`. Si cambias acá, también cambia los
tipos espejo en `web/src/lib/types.ts`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Intent = Literal["search", "descriptive", "comparative", "temporal", "cross_source"]
Axis = Literal["tema", "tipo", "territorio", "entidad"]


class QueryRequest(BaseModel):
    """Cuerpo del POST /api/v1/query."""

    q: str = Field(..., min_length=1, max_length=500, description="Pregunta en lenguaje natural")
    filters: dict[str, list[str]] | None = Field(default=None)


class DatasetCitation(BaseModel):
    """Referencia citable a un dataset (alineado con AnalysisResult.dataset_references)."""

    index: int
    id: str
    name: str
    entity: str | None = None
    url: str
    api_url: str


class PopularQuery(BaseModel):
    question: str
    count: int
    intent: Intent | None = None


class SuggestOption(BaseModel):
    value: str
    label: str
    count: int | None = None
    kicker: str | None = None


class SuggestResponse(BaseModel):
    axis: Axis
    options: list[SuggestOption]


class DivipolaItem(BaseModel):
    code: str
    name: str
    dpto_code: str | None = None


class DivipolaResponse(BaseModel):
    departments: list[DivipolaItem] | None = None
    municipios: list[DivipolaItem] | None = None


class DatasetColumn(BaseModel):
    field_name: str
    name: str
    data_type: str
    description: str | None = None


class DatasetMetadata(BaseModel):
    id: str
    name: str
    entity: str | None
    description: str
    columns: list[DatasetColumn]
    row_count: int | None = None
    last_updated: str | None = None
    url: str
    api_url: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    backend: str
    detail: str | None = None


# ============================================================
# Fase 1 — Chips como entrada PRIMARIA (ADR-018 cuando exista)
# ============================================================


ChipTipo = Literal["Cuántos", "Comparar", "Ranking", "Tendencia", "Mapa"]


class ChipOption(BaseModel):
    """Opción de un chip (valor seleccionable). `value` es lo que viaja al
    backend; `label` es lo que ve el usuario."""

    value: str
    label: str
    # Información extra opcional para tooltips o cards.
    count: int | None = None  # cuántos datasets aplican a este chip
    hint: str | None = None


class ChipsResponse(BaseModel):
    """GET /api/v1/chips — listas dinámicas para la UI."""

    tema: list[ChipOption]          # desde DISTINCT datasets.category
    tipo: list[ChipOption]          # hardcoded 5
    territorio: list[ChipOption]    # Nacional + 32 dptos + macroregiones
    entidad: list[ChipOption]       # top-N por uso telemetría


class ChipsQueryRequest(BaseModel):
    """POST /api/v1/query/chips — combinación de chips elegida por el usuario."""

    tema: str | None = None         # category de Socrata
    tipo: ChipTipo | None = None
    territorio: str | None = None   # código DIVIPOLA "11", "05001", "macro:caribe", "nacional"
    entidad: str | None = None      # entity_id como string
    # Sub-tags refinadores (capa 2, ver GET /api/v1/chips/refine). Multi =
    # intersection: el dataset debe tener TODOS los tags marcados.
    subtags: list[str] | None = None
    refinador: str | None = Field(default=None, max_length=200,
                                  description="Texto libre opcional, refina dentro del subset")
    # Si el usuario explícitamente marcó un dataset (botón "Era este"):
    force_dataset_id: str | None = None


class ChipsRefineResponse(BaseModel):
    """GET /api/v1/chips/refine — capa 2 sub-tags refinadores del subset.

    `subtags` viene ordenado por frecuencia DESC, filtrado de tags
    administrativos genéricos (ver `_TAG_STOPLIST` en api/routes/chips.py).
    Vacío si el subset es >500 datasets (demasiado ruido) o 0.
    """

    subset_total: int                # # datasets que matchean los chips capa 1
    subtags: list[ChipOption]        # tags top con count


class ChipsCandidateDataset(BaseModel):
    """Dataset dentro del subset filtrado por chips."""

    dataset_id: str
    name: str
    entity: str | None
    category: str | None
    row_count: int | None
    view_count: int | None
    last_updated: str | None
    url: str
    api_url: str
    jurisdiccion_nivel: str | None
    jurisdiccion_geo_codes: list[str] | None
    # Score compuesto que decidió el ORDER BY (A.2). Sirve para auditar la
    # decisión del top-1 sin abrir Postgres. null si no calculable.
    score: float | None = None


class ChipsQueryResponse(BaseModel):
    """Respuesta inicial del POST /chips — la narrativa final llega vía SSE
    si el cliente pide streaming en un endpoint posterior."""

    total_in_subset: int           # # de datasets que matchean los chips
    candidates: list[ChipsCandidateDataset]  # top-N para mostrar
    chosen_dataset_id: str | None  # el seleccionado para ejecutar SoQL
    suggested_chips: list[str] | None = None  # ["entidad", "territorio"] si subset>10
    message: str | None = None     # ej. "Hay 746 datasets de Salud. Marcá otro chip para refinar."


# ============================================================
# Hito 1 / Fase B — Motor SoQL determinista
# ============================================================


SemanticType = Literal["geo", "fecha", "metrica", "dimension", "exclude"]
Confidence = Literal["high", "medium", "low"]


class CuratedColumn(BaseModel):
    """Una columna de un dataset, con su clasificación semántica curada
    (`dataset_columns_curated`, ver migración 004)."""

    col_name: str
    socrata_data_type: str | None = None
    socrata_description: str | None = None
    semantic_type: SemanticType
    semantic_subtype: str | None = None
    confidence: Confidence


class DatasetCuratedColumns(BaseModel):
    """GET /api/v1/datasets/{id}/columns — columnas tipadas para construir
    SoQL determinista por TIPO. `by_type` es un índice por semantic_type
    ordenado por confidence DESC (high → medium → low) para que el
    selector tome la columna más confiable primero."""

    dataset_id: str
    columns: list[CuratedColumn]
    by_type: dict[SemanticType, list[str]]


class ChipsExecuteRequest(BaseModel):
    """POST /api/v1/query/chips/execute — ejecutar la consulta SoQL sobre
    el dataset elegido + TIPO. Sin LLM: build_soql + SodaClient."""

    dataset_id: str
    tipo: ChipTipo
    # Territorio opcional como filtro adicional (DIVIPOLA code o "macro:*").
    territorio: str | None = None


class ChipsExecuteResponse(BaseModel):
    """Respuesta del ejecutor SoQL determinista."""

    dataset_id: str
    tipo: ChipTipo
    soql: str                   # query exacta enviada a SODA (para transparencia)
    columns_used: list[str]     # columnas que el template eligió
    rows: list[dict]            # filas crudas de SODA
    row_count: int              # len(rows), por conveniencia del cliente
    error: str | None = None    # mensaje si no se pudo construir o ejecutar
