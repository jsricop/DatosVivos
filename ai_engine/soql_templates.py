"""Constructor SoQL determinista por TIPO de chip (Hito 1, Fase B).

Plantillas puras: dado un TIPO y la lista de columnas curadas del dataset
(`dataset_columns_curated`), devuelve la query SoQL exacta a enviar a SODA.
Sin LLM, sin IO. La lista de columnas debe venir YA ordenada por
confidence DESC (la consulta de B.1 lo hace).

Decisión de diseño (memoria `project_soql_count_default`): `COUNT(*)` es
la métrica DEFAULT en cada TIPO. `SUM(métrica)` se usa SOLO si el dataset
tiene una columna curada como `metrica` Y el TIPO lo soporta (Ranking).

Decisión adicional (smoke 2026-05-29): la curación marca algunas columnas
como `semantic_type='fecha'` aunque su `socrata_data_type` sea `number`
(años como entero) o `text`. En esos casos `date_trunc_ym(col)` falla en
SODA (type-mismatch). Para `Tendencia`:
  - subtype='date' Y data_type ∈ {calendar_date, date, floating_timestamp}
    → date_trunc_ym(col).
  - subtype='year' o data_type='number'
    → GROUP BY col directo (ya es un periodo discreto).
  - resto (subtype='period', data_type='text')
    → GROUP BY col directo.

Plantillas:
  Cuántos    → SELECT count(*) AS n
  Comparar   → SELECT {dim}, count(*) AS n GROUP BY {dim} ORDER BY n DESC LIMIT 10
  Ranking    → idem Comparar (default) o con SUM(metrica) si aplica
  Tendencia  → SELECT {fecha_expr} AS periodo, count(*) AS n GROUP BY periodo ORDER BY periodo LIMIT 60
  Mapa       → SELECT {geo}, count(*) AS n GROUP BY {geo} ORDER BY n DESC LIMIT 32
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

ChipTipo = Literal["Cuántos", "Comparar", "Ranking", "Tendencia", "Mapa"]

# Identificador SoQL válido — coincide con `columns_field_name` snake_case.
_IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_DATE_DATATYPES = {"calendar_date", "date", "floating_timestamp"}


@dataclass
class BuildResult:
    """Resultado de `build_soql`: query + columnas usadas + error si falló."""

    soql: str
    columns_used: list[str] = field(default_factory=list)
    error: str | None = None


def _safe_ident(name: str | None) -> str | None:
    if not name or not _IDENT_RE.match(name):
        return None
    return name


def _pick(columns: Iterable[dict[str, Any]], stype: str) -> dict[str, Any] | None:
    """Devuelve el primer col-dict del tipo semántico solicitado cuyo
    `col_name` es identificador SoQL válido. Asume orden de confidence DESC."""
    for c in columns:
        if c.get("semantic_type") != stype:
            continue
        if _safe_ident(c.get("col_name")):
            return c
    return None


def _fecha_expr(col: dict[str, Any]) -> str:
    """Devuelve la expresión SoQL para agrupar por periodo según subtype y
    data_type. Para columnas que SODA reconoce como fecha, usa date_trunc_ym;
    si la fecha está como número (año entero) o texto, agrupa por el valor
    crudo."""
    name = col["col_name"]
    subtype = (col.get("semantic_subtype") or "").lower()
    data_type = (col.get("socrata_data_type") or "").lower()
    if subtype == "date" and data_type in _DATE_DATATYPES:
        return f"date_trunc_ym({name})"
    return name


def build_soql(
    tipo: ChipTipo,
    columns: list[dict[str, Any]],
    *,
    use_metric: bool = True,
) -> BuildResult:
    """Construye la query SoQL para el `tipo` solicitado.

    Args:
        tipo: uno de los 5 chips de TIPO.
        columns: lista de col-dicts con al menos `col_name` y
            `semantic_type`. Opcionalmente `semantic_subtype` y
            `socrata_data_type` para decisiones data-type-aware
            (Tendencia). Orden = preferencia (confidence DESC).
        use_metric: si True (default), Ranking usa SUM(metrica) cuando hay
            columna métrica; si False, fuerza COUNT(*).
    """
    if tipo == "Cuántos":
        return BuildResult(soql="SELECT count(*) AS n", columns_used=[])

    if tipo in ("Comparar", "Ranking"):
        dim_col = _pick(columns, "dimension")
        if not dim_col:
            return BuildResult(
                soql="", error=f"{tipo} requiere ≥1 columna de tipo `dimension`"
            )
        dim = dim_col["col_name"]
        if tipo == "Ranking" and use_metric:
            metrica_col = _pick(columns, "metrica")
            if metrica_col:
                metrica = metrica_col["col_name"]
                return BuildResult(
                    soql=(
                        f"SELECT {dim} AS categoria, "
                        f"sum({metrica}) AS total "
                        f"GROUP BY {dim} "
                        f"ORDER BY total DESC "
                        f"LIMIT 10"
                    ),
                    columns_used=[dim, metrica],
                )
        return BuildResult(
            soql=(
                f"SELECT {dim} AS categoria, count(*) AS n "
                f"GROUP BY {dim} "
                f"ORDER BY n DESC "
                f"LIMIT 10"
            ),
            columns_used=[dim],
        )

    if tipo == "Tendencia":
        fecha_col = _pick(columns, "fecha")
        if not fecha_col:
            return BuildResult(
                soql="", error="Tendencia requiere ≥1 columna de tipo `fecha`"
            )
        expr = _fecha_expr(fecha_col)
        return BuildResult(
            soql=(
                f"SELECT {expr} AS periodo, count(*) AS n "
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
                soql="", error="Mapa requiere ≥1 columna de tipo `geo`"
            )
        geo = geo_col["col_name"]
        return BuildResult(
            soql=(
                f"SELECT {geo} AS region, count(*) AS n "
                f"GROUP BY {geo} "
                f"ORDER BY n DESC "
                f"LIMIT 32"
            ),
            columns_used=[geo],
        )

    return BuildResult(soql="", error=f"TIPO desconocido: {tipo!r}")
