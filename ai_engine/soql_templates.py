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

ChipTipo = Literal["Cuántos", "Total", "Comparar", "Ranking", "Tendencia", "Mapa"]

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


_RATE_LIKE_RE = re.compile(
    r"tasa|porcentaje|porc(_|$)|[ií]ndice|promedio|media|per_?capita|variaci",
    re.IGNORECASE,
)
_ID_LIKE_RE = re.compile(
    r"(^|_)(id|ids|codigo|cod|nro|numero|num|consecutivo|registro|radicado)(_|$)"
    r"|identificaci|expediente",
    re.IGNORECASE,
)


def _pick(columns: Iterable[dict[str, Any]], stype: str) -> dict[str, Any] | None:
    """Devuelve el primer col-dict del tipo semántico solicitado cuyo
    `col_name` es identificador SoQL válido. Asume orden de confidence DESC.

    Para `dimension`, evita columnas con nombre de IDENTIFICADOR (id, código,
    consecutivo…): agrupar por ellas produce una barra por registro (Saber
    Pro agrupó por código de estudiante, ciclo ciudadano c07 2026-07-12).
    Si solo hay dimensiones tipo ID, cae a la primera (mejor que nada)."""
    fallback = None
    for c in columns:
        if c.get("semantic_type") != stype:
            continue
        if not _safe_ident(c.get("col_name")):
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

    if tipo == "Total":
        # "¿Cuánto vale/cuesta X?" pide la SUMA del valor principal, no un
        # conteo de filas (ciclo ciudadano c17/c20/c50, 2026-07-12).
        metrica_col = _pick(columns, "metrica")
        if not metrica_col:
            return BuildResult(
                soql="",
                error="Total requiere ≥1 columna de tipo `metrica` (un valor sumable)",
            )
        met = metrica_col["col_name"]
        return BuildResult(
            soql=f"SELECT sum({met}) AS total",
            columns_used=[met],
        )

    if tipo in ("Comparar", "Ranking"):
        dim_col = _pick(columns, "dimension")
        if not dim_col:
            return BuildResult(
                soql="", error=f"{tipo} requiere ≥1 columna de tipo `dimension`"
            )
        dim = dim_col["col_name"]
        # Sin categorías-basura como barras ("NR: 19" en Pruebas ICFES, ciclo
        # ciudadano c07 2026-07-12). El NOT IN con upper() solo aplica a
        # columnas de texto — sobre numéricas rompería el SoQL completo.
        if (dim_col.get("socrata_data_type") or "").lower() == "text":
            sin_basura = (
                f"WHERE {dim} IS NOT NULL AND upper({dim}) NOT IN "
                f"('', 'NR', 'N/A', 'NA', 'N.A', 'N.A.', 'NULL', 'SIN DATO', "
                f"'SIN INFORMACION', 'SIN INFORMACIÓN', 'NO APLICA', 'NO REPORTA') "
            )
        else:
            sin_basura = f"WHERE {dim} IS NOT NULL "
        if tipo == "Ranking" and use_metric:
            metrica_col = _pick(columns, "metrica")
            if metrica_col:
                metrica = metrica_col["col_name"]
                return BuildResult(
                    soql=(
                        f"SELECT {dim} AS categoria, "
                        f"sum({metrica}) AS total "
                        f"{sin_basura}"
                        f"GROUP BY {dim} "
                        f"ORDER BY total DESC "
                        f"LIMIT 10"
                    ),
                    columns_used=[dim, metrica],
                )
        return BuildResult(
            soql=(
                f"SELECT {dim} AS categoria, count(*) AS n "
                f"{sin_basura}"
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
