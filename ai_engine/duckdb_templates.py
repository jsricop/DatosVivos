"""Plantillas DuckDB por TIPO de chip (Reto F.4).

Equivalente a `ai_engine/soql_templates.py` pero para datasets federados
que se consultan vía `read_csv_auto(<URL>)` en DuckDB. Reutiliza el mismo
contrato de columnas (list[dict] con `col_name`, `semantic_type`,
`semantic_subtype`, `socrata_data_type`).

Diferencias con SoQL:
- FROM: `read_csv_auto('<url>')` (embebida; URL validada upstream).
- Identificadores: rodeados con `"..."` (DuckDB) en vez de unquoted (SODA).
- Fecha mes-año: `date_trunc('month', try_cast(col AS TIMESTAMP))` en vez
  de `date_trunc_ym(col)`. `try_cast` evita errores si la columna trae
  strings no parseables.
- Sin LIMIT en el `read_csv_auto` (la limitación va al final).

Inyección: las URLs deben venir de `datasets.data_url` (no de input
usuario). Los nombres de columna se validan via `_safe_ident_dbq` antes
de embeberse.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

from ai_engine.duckdb_executor import _safe_ident_dbq

ChipTipo = Literal["Cuántos", "Comparar", "Ranking", "Tendencia", "Mapa"]

_DATE_DATATYPES = {
    "calendar_date", "date", "floating_timestamp",
    # DuckDB DESCRIBE devuelve nombres en mayúscula:
    "DATE", "TIMESTAMP", "TIMESTAMP WITH TIME ZONE", "TIMESTAMP_TZ",
}


@dataclass
class BuildResult:
    sql: str
    columns_used: list[str] = field(default_factory=list)
    error: str | None = None


def _pick(columns: Iterable[dict[str, Any]], stype: str) -> dict[str, Any] | None:
    """Primera columna del tipo semántico cuyo `col_name` quote-safely."""
    for c in columns:
        if c.get("semantic_type") != stype:
            continue
        if _safe_ident_dbq(c.get("col_name") or ""):
            return c
    return None


def _from_clause(url: str) -> str:
    # Devuelve el placeholder `{src}` que el executor sustituye por el
    # `read_csv(...)` con encoding adecuado (UTF-8 / latin-1 / utf-16).
    # La URL se conserva en el executor para que sepa qué archivo abrir.
    return "{src}"


def _fecha_expr(col: dict[str, Any]) -> str:
    name = col["col_name"]
    quoted = _safe_ident_dbq(name)
    subtype = (col.get("semantic_subtype") or "").lower()
    data_type = (col.get("socrata_data_type") or "").upper()
    # Si DuckDB ya lo infirió como DATE/TIMESTAMP, no necesitamos try_cast.
    if data_type in {dt.upper() for dt in _DATE_DATATYPES} and subtype == "date":
        return f"date_trunc('month', {quoted})"
    # Para texto que parezca fecha, try_cast a TIMESTAMP → NULL si falla.
    if subtype == "date":
        return f"date_trunc('month', try_cast({quoted} AS TIMESTAMP))"
    # year / period / other → group by raw.
    return quoted  # type: ignore[return-value]


def build_duckdb_sql(
    tipo: ChipTipo,
    columns: list[dict[str, Any]],
    url: str,
    *,
    use_metric: bool = True,
) -> BuildResult:
    """Construye SQL DuckDB para `tipo` sobre el CSV en `url`.

    Emite `{src}` como placeholder del FROM — el executor lo sustituye
    con `read_csv(...)` con encoding apropiado.
    """
    src = _from_clause(url)  # = "{src}", placeholder

    if tipo == "Cuántos":
        return BuildResult(
            sql=f"SELECT count(*) AS n FROM {src}",
            columns_used=[],
        )

    if tipo in ("Comparar", "Ranking"):
        dim_col = _pick(columns, "dimension")
        if not dim_col:
            return BuildResult(
                sql="", error=f"{tipo} requiere ≥1 columna de tipo `dimension`"
            )
        dim_q = _safe_ident_dbq(dim_col["col_name"])
        if tipo == "Ranking" and use_metric:
            metrica_col = _pick(columns, "metrica")
            if metrica_col:
                met_q = _safe_ident_dbq(metrica_col["col_name"])
                return BuildResult(
                    sql=(
                        f"SELECT {dim_q} AS categoria, "
                        f"sum(try_cast({met_q} AS DOUBLE)) AS total "
                        f"FROM {src} "
                        f"GROUP BY {dim_q} "
                        f"ORDER BY total DESC NULLS LAST "
                        f"LIMIT 10"
                    ),
                    columns_used=[dim_col["col_name"], metrica_col["col_name"]],
                )
        return BuildResult(
            sql=(
                f"SELECT {dim_q} AS categoria, count(*) AS n "
                f"FROM {src} "
                f"GROUP BY {dim_q} "
                f"ORDER BY n DESC "
                f"LIMIT 10"
            ),
            columns_used=[dim_col["col_name"]],
        )

    if tipo == "Tendencia":
        fecha_col = _pick(columns, "fecha")
        if not fecha_col:
            return BuildResult(
                sql="", error="Tendencia requiere ≥1 columna de tipo `fecha`"
            )
        expr = _fecha_expr(fecha_col)
        return BuildResult(
            sql=(
                f"SELECT {expr} AS periodo, count(*) AS n "
                f"FROM {src} "
                f"GROUP BY periodo "
                f"ORDER BY periodo "
                f"LIMIT 60"
            ),
            columns_used=[fecha_col["col_name"]],
        )

    if tipo == "Mapa":
        geo_col = _pick(columns, "geo")
        if not geo_col:
            return BuildResult(
                sql="", error="Mapa requiere ≥1 columna de tipo `geo`"
            )
        geo_q = _safe_ident_dbq(geo_col["col_name"])
        return BuildResult(
            sql=(
                f"SELECT {geo_q} AS region, count(*) AS n "
                f"FROM {src} "
                f"GROUP BY {geo_q} "
                f"ORDER BY n DESC "
                f"LIMIT 32"
            ),
            columns_used=[geo_col["col_name"]],
        )

    return BuildResult(sql="", error=f"TIPO desconocido: {tipo!r}")
