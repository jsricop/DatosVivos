"""Schemas Pydantic del Dashboard Spec (PLAN_DASHBOARD §3 y §7.1).

El LLM 7B/14B genera un JSON que el frontend Next.js renderiza dinámicamente.
Espejo en TypeScript: `web/src/lib/schemas/dashboard.ts` (con zod).

Si cambias acá, también allá — el contrato se mantiene sincronizado.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

# --- Tipos base ---

LayoutKind = Literal["grid", "stack"]
KpiFormat = Literal["number_es_co", "percent", "currency_cop"]
ChartKind = Literal["bar", "line", "area", "scatter", "pie", "donut"]
SortDir = Literal["asc", "desc", "none"]
ChoroplethLevel = Literal["dpto", "mpio"]
AggFn = Literal["sum", "count", "mean"]


# --- Bloques ---


class KPIBlock(BaseModel):
    type: Literal["kpi"]
    title: str = Field(..., max_length=120)
    value_from: str = Field(..., max_length=80)
    format: KpiFormat = "number_es_co"
    delta: dict | None = None


class ChartBlock(BaseModel):
    type: ChartKind
    title: str = Field(..., max_length=120)
    x_column: str = Field(..., max_length=80)
    y_column: str = Field(..., max_length=80)
    groupby: str | None = Field(default=None, max_length=80)
    agg: AggFn | None = None
    sort: SortDir | None = None
    limit: int | None = Field(default=None, ge=1, le=100)
    stacked: bool | None = None


class MapBlock(BaseModel):
    type: Literal["choropleth"]
    title: str = Field(..., max_length=120)
    level: ChoroplethLevel
    code_column: str = Field(..., max_length=80)
    metric_column: str = Field(..., max_length=80)
    legend_format: Literal["number_es_co", "percent"] = "number_es_co"


class TableBlock(BaseModel):
    type: Literal["table"]
    title: str = Field(..., max_length=120)
    columns: list[str] = Field(..., min_length=1, max_length=20)
    max_rows: int | None = Field(default=None, ge=1, le=500)


Block = Annotated[
    KPIBlock | ChartBlock | MapBlock | TableBlock,
    Field(discriminator="type"),
]


class DashboardSpec(BaseModel):
    """Especificación generada por el LLM. Versionada para evolución segura."""

    version: Literal["1"]
    title: str = Field(..., max_length=200)
    subtitle: str | None = Field(default=None, max_length=300)
    layout: LayoutKind = "grid"
    blocks: list[Block] = Field(..., min_length=1, max_length=6)
    caveats: list[str] | None = Field(default=None, max_length=10)

    def column_names_referenced(self) -> set[str]:
        """Conjunto de columnas que los blocks referencian — para validar contra rows reales."""
        names: set[str] = set()
        for block in self.blocks:
            if isinstance(block, ChartBlock):
                names.add(block.x_column)
                names.add(block.y_column)
                if block.groupby:
                    names.add(block.groupby)
            elif isinstance(block, MapBlock):
                names.add(block.code_column)
                names.add(block.metric_column)
            elif isinstance(block, TableBlock):
                names.update(block.columns)
        return names

    @model_validator(mode="after")
    def _no_empty_blocks(self) -> "DashboardSpec":
        if not self.blocks:
            msg = "blocks no puede estar vacío"
            raise ValueError(msg)
        return self
