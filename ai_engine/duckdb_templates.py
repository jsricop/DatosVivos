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

import re

from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

from ai_engine.duckdb_executor import _safe_ident_dbq

ChipTipo = Literal["Cuántos", "Total", "Comparar", "Ranking", "Tendencia", "Mapa"]

_RATE_LIKE_RE = re.compile(
    r"tasa|porcentaje|porc(_|$)|[ií]ndice|promedio|media|per_?capita|variaci",
    re.IGNORECASE,
)
_ID_LIKE_RE = re.compile(
    r"(^|_)(id|ids|codigo|cod|nro|numero|num|consecutivo|registro|radicado)(_|\s|$)"
    r"|identificaci|expediente",
    re.IGNORECASE,
)

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
    """Primera columna del tipo semántico cuyo `col_name` quote-safely.

    Para `dimension`, evita columnas con nombre de IDENTIFICADOR (id,
    código, consecutivo…): agrupar por ellas produce una barra por registro
    (ciclo ciudadano c07, 2026-07-12). Si solo hay tipo ID, cae a la primera."""
    fallback = None
    for c in columns:
        if c.get("semantic_type") != stype:
            continue
        if not _safe_ident_dbq(c.get("col_name") or ""):
            continue
        if stype == "dimension" and _ID_LIKE_RE.search(c["col_name"]):
            fallback = fallback or c
            continue
        if stype == "metrica" and _RATE_LIKE_RE.search(c["col_name"]):
            # Una TASA/porcentaje/promedio no se suma con sentido: sumar
            # "tasa de interés" dio 67.11 como "deuda pública" (2026-07-13).
            # Se prefiere una métrica de monto; si solo hay tasas, cae a ella.
            fallback = fallback or c
            continue
        return c
    return fallback


def _from_clause(url: str) -> str:
    # Devuelve el placeholder `{src}` que el executor sustituye por el
    # `read_csv(...)` con encoding adecuado (UTF-8 / latin-1 / utf-16).
    # La URL se conserva en el executor para que sepa qué archivo abrir.
    return "{src}"


def filter_conditions(filters: list[dict[str, Any]] | None) -> list[str]:
    """Condiciones WHERE de filtros de VALOR (ADR-024).

    Cada filtro es {"col", "kind" ('valor'|'anio'), "value"} YA VALIDADO
    contra `dataset_filter_values` por el caller (el valor EXISTE en el
    dato — el LLM/la UI solo eligen entre valores reales). Aquí solo se
    arma SQL seguro: identificador via `_safe_ident_dbq`, valor con
    comilla simple doblada. Filtros con columna insegura se omiten.
    """
    conds: list[str] = []
    for f in filters or []:
        q = _safe_ident_dbq(str(f.get("col") or ""))
        if not q:
            continue
        value = str(f.get("value") or "")
        if f.get("kind") == "anio":
            if not value.isdigit():
                continue
            conds.append(f"EXTRACT(YEAR FROM {q}) = {int(value)}")
        else:
            escaped = value.replace("'", "''")
            conds.append(f"{q} = '{escaped}'")
    return conds


def _and_where(base_where: str, conds: list[str]) -> str:
    """Combina el WHERE propio del template con las condiciones de filtro."""
    if not conds:
        return base_where
    extra = " AND ".join(conds)
    if base_where.strip():
        return f"{base_where} AND {extra}"
    return f"WHERE {extra}"


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
    filters: list[dict[str, Any]] | None = None,
) -> BuildResult:
    """Construye SQL DuckDB para `tipo` sobre el CSV en `url`.

    Emite `{src}` como placeholder del FROM — el executor lo sustituye
    con `read_csv(...)` con encoding apropiado.

    `filters`: filtros de valor YA validados contra el perfil de la bodega
    (ADR-024); se AND-ean al WHERE de cada plantilla.
    """
    src = _from_clause(url)  # = "{src}", placeholder
    fconds = filter_conditions(filters)
    fcols = [str(f["col"]) for f in filters or [] if f.get("col")]

    if tipo == "Cuántos":
        return BuildResult(
            sql=f"SELECT count(*) AS n FROM {src} {_and_where('', fconds)}".strip(),
            columns_used=fcols,
        )

    if tipo == "Total":
        # Suma del valor principal — "cuánto vale/cuesta X" (ciclo c17/c20).
        metrica_col = _pick(columns, "metrica")
        if not metrica_col:
            return BuildResult(
                sql="",
                error="Total requiere ≥1 columna de tipo `metrica` (un valor sumable)",
            )
        met_q = _safe_ident_dbq(metrica_col["col_name"])
        return BuildResult(
            sql=(
                f"SELECT sum(try_cast({met_q} AS DOUBLE)) AS total "
                f"FROM {src} {_and_where('', fconds)}"
            ).strip(),
            columns_used=[metrica_col["col_name"], *fcols],
        )

    if tipo in ("Comparar", "Ranking"):
        dim_col = _pick(columns, "dimension")
        if not dim_col:
            return BuildResult(
                sql="", error=f"{tipo} requiere ≥1 columna de tipo `dimension`"
            )
        dim_q = _safe_ident_dbq(dim_col["col_name"])
        # Sin categorías-basura: NULL, vacío y placeholders tipo "NR"/"N/A"
        # salían como barras ("NR: 19" en Pruebas ICFES, ciclo ciudadano c07
        # 2026-07-12). Se filtran ANTES de agrupar.
        sin_basura = (
            f"WHERE {dim_q} IS NOT NULL "
            f"AND upper(trim(CAST({dim_q} AS VARCHAR))) NOT IN "
            f"('', 'NR', 'N/A', 'NA', 'N.A', 'N.A.', 'NULL', 'SIN DATO', "
            f"'SIN INFORMACION', 'SIN INFORMACIÓN', 'NO APLICA', 'NO REPORTA')"
        )
        sin_basura = _and_where(sin_basura, fconds)
        if tipo == "Ranking" and use_metric:
            metrica_col = _pick(columns, "metrica")
            if metrica_col:
                met_q = _safe_ident_dbq(metrica_col["col_name"])
                return BuildResult(
                    sql=(
                        f"SELECT {dim_q} AS categoria, "
                        f"sum(try_cast({met_q} AS DOUBLE)) AS total "
                        f"FROM {src} {sin_basura} "
                        f"GROUP BY {dim_q} "
                        f"ORDER BY total DESC NULLS LAST "
                        f"LIMIT 10"
                    ),
                    columns_used=[dim_col["col_name"], metrica_col["col_name"], *fcols],
                )
        return BuildResult(
            sql=(
                f"SELECT {dim_q} AS categoria, count(*) AS n "
                f"FROM {src} {sin_basura} "
                f"GROUP BY {dim_q} "
                f"ORDER BY n DESC "
                f"LIMIT 10"
            ),
            columns_used=[dim_col["col_name"], *fcols],
        )

    if tipo == "Tendencia":
        fecha_col = _pick(columns, "fecha")
        if not fecha_col:
            return BuildResult(
                sql="", error="Tendencia requiere ≥1 columna de tipo `fecha`"
            )
        expr = _fecha_expr(fecha_col)
        # DESC: los ÚLTIMOS 60 periodos (ver nota en soql_templates.py).
        return BuildResult(
            sql=(
                f"SELECT {expr} AS periodo, count(*) AS n "
                f"FROM {src} {_and_where('', fconds)} "
                f"GROUP BY periodo "
                f"ORDER BY periodo DESC "
                f"LIMIT 60"
            ),
            columns_used=[fecha_col["col_name"], *fcols],
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
                f"FROM {src} {_and_where('', fconds)} "
                f"GROUP BY {geo_q} "
                f"ORDER BY n DESC "
                f"LIMIT 32"
            ),
            columns_used=[geo_col["col_name"], *fcols],
        )

    return BuildResult(sql="", error=f"TIPO desconocido: {tipo!r}")
