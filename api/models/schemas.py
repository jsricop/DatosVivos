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
