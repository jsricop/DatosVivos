"""Cálculo determinista de estadísticas a partir de rows SODA.

Sirve dos propósitos:
1. Generar líneas de resumen humanas en es-CO para mostrar al ciudadano
   en el bloque "Datos verificados" (cero margen de alucinación).
2. Construir una *whitelist* de cifras que el LLM puede citar en su
   narrativa interpretativa. Toda cifra fuera de la whitelist será
   censurada por `_validate_numbers` en `analyzer.py`.

Diseño:
- Stateless: `StatsComputer.compute(rows, soql) -> Statistics`.
- Auto-cast de strings de SODA a numéricos / fechas con `pd.to_numeric`
  / `pd.to_datetime`. SODA siempre devuelve strings.
- Normalización canónica de números (`_normalize_number`) para que la
  whitelist matchee tanto formato es-CO (125.000) como inglés (125000).
- Sin LLM, sin red, sin estado mutable — determinista por construcción.

Reutiliza patrones probados en `app/components/accessibility/chart_narrator.py`.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

log = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Datatypes
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class ColumnSummary:
    """Resumen estadístico de una columna del result set."""

    name: str
    kind: str  # "numeric" | "categorical" | "datetime" | "id" | "empty"
    n_non_null: int
    n_unique: int | None = None
    min: Any | None = None
    max: Any | None = None
    mean: float | None = None
    # Para columnas categóricas: lista de (valor, count, pct) ordenada desc.
    top_values: list[tuple[Any, int, float]] | None = None


@dataclass(frozen=True)
class Statistics:
    """Resultado de un cálculo estadístico determinista."""

    total_rows: int
    soql_used: str
    column_summaries: list[ColumnSummary] = field(default_factory=list)
    aggregate_hits: list[str] = field(default_factory=list)
    summary_lines: list[str] = field(default_factory=list)
    whitelist_numbers: frozenset[str] = frozenset()
    derived_numbers: frozenset[str] = frozenset()


# ----------------------------------------------------------------------
# Number normalization (es-CO ↔ canonical)
# ----------------------------------------------------------------------


_NUMBER_TOKEN_RE = re.compile(r"(?<![A-Za-z_-])-?\d[\d\.\,\s]*\d|(?<![A-Za-z_-])-?\d")


def _normalize_number(s: str) -> str:
    """Convierte una cadena numérica (es-CO o inglesa) a forma canónica.

    Reglas (heurística pragmática para es-CO + inglés):
    - Quita espacios.
    - El último separador (.,) seguido por **1-2 dígitos al final** se trata
      como decimal. Tres o más dígitos al final → separador de miles.
    - Si solo hay un separador y el grupo final es de 3 dígitos, se asume
      separador de miles (convención es-CO `125.000` = 125 mil).
    - Elimina ceros a la derecha en la parte decimal.

    Si el string no parsea como número, devuelve el string trimmed (no crashea).
    """
    if s is None:
        return ""
    raw = str(s).strip()
    if not raw:
        return ""

    sign = ""
    if raw.startswith("-"):
        sign = "-"
        raw = raw[1:]

    # Determinar separador decimal: el último '.' o ',' seguido por 1-2 dígitos
    # solo al final (3+ dígitos → separador de miles).
    decimal_sep = None
    for sep in (".", ","):
        idx = raw.rfind(sep)
        if idx == -1:
            continue
        tail = raw[idx + 1 :]
        if tail.isdigit() and 1 <= len(tail) <= 2:
            # Si hay OTRO separador (.,) DESPUÉS de este, este no es decimal.
            after = raw[idx + 1 :]
            if not any(c in after for c in ".,"):
                decimal_sep = sep
                break

    if decimal_sep is None:
        # Sin decimal: quitar separadores de miles + espacios.
        canonical = re.sub(r"[\.\,\s]", "", raw)
    else:
        int_part, dec_part = raw.rsplit(decimal_sep, 1)
        int_part = re.sub(r"[\.\,\s]", "", int_part)
        dec_part = dec_part.strip()
        canonical = f"{int_part}.{dec_part}" if dec_part else int_part

    if not canonical or not re.match(r"^-?\d+(\.\d+)?$", canonical):
        return raw  # no parseable; devolver tal cual para no romper

    # Reducir decimales: quitar trailing zeros ("125.0" → "125", "125.50" → "125.5")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
        if not canonical or canonical == "-":
            canonical = "0"

    return sign + canonical


def _format_es_co(value: float | int) -> str:
    """Formatea un número con separador de miles punto y decimal coma (es-CO)."""
    if isinstance(value, float):
        if value.is_integer():
            int_part = int(value)
            return f"{int_part:,}".replace(",", ".")
        formatted = f"{value:,.2f}"
        int_part, dec_part = formatted.split(".")
        return int_part.replace(",", ".") + "," + dec_part
    return f"{value:,}".replace(",", ".")


# ----------------------------------------------------------------------
# Helpers de tipado
# ----------------------------------------------------------------------


def _classify_column(series: pd.Series) -> str:
    """Devuelve el `kind` semántico de la columna ya cast'eada."""
    if series.dropna().empty:
        return "empty"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    # Heurística: si los valores parecen IDs (alfanuméricos con guion / códigos
    # cortos), trátelos como id. Si no, categórico.
    sample = series.dropna().astype(str).head(20)
    id_like = sample.str.match(r"^[a-z0-9]{4}-[a-z0-9]{4}$|^\d{1,5}$").mean() > 0.8
    if id_like:
        return "id"
    return "categorical"


def _autocast(df: pd.DataFrame) -> pd.DataFrame:
    """Castea columnas string de SODA a numérico/fecha cuando >50% parsea.

    Nota: pandas 3.0 usa dtype `str` (PyArrow) por default, no `object`.
    Skip solo si la columna YA está cast'eada a numérico o datetime.
    """
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_datetime64_any_dtype(s):
            continue

        as_num = pd.to_numeric(s, errors="coerce")
        if as_num.notna().sum() > 0 and as_num.notna().sum() >= 0.5 * len(s):
            df[col] = as_num
            continue

        try:
            as_dt = pd.to_datetime(s, errors="coerce", utc=True, format="mixed")
        except Exception:  # noqa: BLE001
            as_dt = pd.Series([pd.NaT] * len(s))
        if as_dt.notna().sum() > 0 and as_dt.notna().sum() >= 0.5 * len(s):
            df[col] = as_dt

    return df


# ----------------------------------------------------------------------
# Per-column summarization
# ----------------------------------------------------------------------


def _summarize_column(series: pd.Series) -> ColumnSummary:
    """Construye `ColumnSummary` para una serie. Determinista."""
    name = str(series.name)
    kind = _classify_column(series)
    non_null = series.dropna()
    n_non_null = int(non_null.size)

    if kind == "empty" or n_non_null == 0:
        return ColumnSummary(name=name, kind=kind, n_non_null=0)

    if kind == "numeric":
        return ColumnSummary(
            name=name,
            kind=kind,
            n_non_null=n_non_null,
            n_unique=int(non_null.nunique()),
            min=float(non_null.min()),
            max=float(non_null.max()),
            mean=float(non_null.mean()),
        )

    if kind == "datetime":
        return ColumnSummary(
            name=name,
            kind=kind,
            n_non_null=n_non_null,
            n_unique=int(non_null.nunique()),
            min=non_null.min(),
            max=non_null.max(),
        )

    # Categórico / id: top values con conteo y % sobre filas no nulas.
    vc = non_null.astype(str).value_counts()
    top = []
    total = float(n_non_null)
    for value, count in vc.head(5).items():
        pct = round(100.0 * count / total, 2) if total else 0.0
        top.append((value, int(count), pct))
    return ColumnSummary(
        name=name,
        kind=kind,
        n_non_null=n_non_null,
        n_unique=int(non_null.nunique()),
        top_values=top,
    )


# ----------------------------------------------------------------------
# Aggregate detection from SoQL
# ----------------------------------------------------------------------


_AGG_RE = re.compile(
    r"\b(count|sum|avg|min|max)\s*\(\s*([\*A-Za-z_][A-Za-z0-9_]*)?\s*\)(?:\s+AS\s+(\w+))?",
    re.IGNORECASE,
)


def _detect_aggregates(soql: str, df: pd.DataFrame) -> list[str]:
    """Identifica agregaciones en el SoQL y produce líneas explicativas.

    Si el SoQL pide `count(*) AS n` y el df tiene columna `n`, la primera
    fila usualmente contiene el conteo total — lo reportamos como agregado.
    """
    hits: list[str] = []
    for match in _AGG_RE.finditer(soql or ""):
        fn = match.group(1).lower()
        target = (match.group(2) or "*").strip()
        alias = match.group(3)

        col_to_read = alias or (target if target and target != "*" else None)
        if not col_to_read:
            continue
        if col_to_read not in df.columns:
            continue

        series = df[col_to_read].dropna()
        if series.empty:
            continue

        # Si hay una sola fila, es el "total"; si hay varias, es agregación por grupo.
        if len(df) == 1:
            value = series.iloc[0]
            display = _format_value(value)
            target_disp = "*" if target == "*" else target
            hits.append(f"{fn}({target_disp}) total = {display}")
    return hits


def _format_value(value: Any) -> str:
    """Formato es-CO para mostrar al ciudadano."""
    if value is None:
        return "—"
    if isinstance(value, (pd.Timestamp,)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value.is_integer():
        return _format_es_co(int(value))
    if isinstance(value, (int, float)):
        return _format_es_co(value)
    return str(value)


# ----------------------------------------------------------------------
# Whitelist building
# ----------------------------------------------------------------------


def _add_number(target: set[str], value: Any) -> None:
    """Inserta `value` en `target` con todas sus formas equivalentes razonables."""
    if value is None:
        return
    if isinstance(value, (pd.Timestamp,)):
        # Año y representación ISO YYYY-MM-DD
        target.add(str(value.year))
        target.add(value.strftime("%Y-%m-%d"))
        return
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not value.is_integer():
            # Mantener canónico y un par de representaciones es-CO.
            canonical = _normalize_number(str(value))
            target.add(canonical)
            target.add(_format_es_co(value).replace(".", "").replace(",", "."))
            target.add(_format_es_co(value))
            return
        ival = int(value)
        canonical = str(ival)
        target.add(canonical)
        target.add(_format_es_co(ival))
        return
    s = str(value).strip()
    canonical = _normalize_number(s)
    if canonical:
        target.add(canonical)
    target.add(s)


def _build_whitelist(
    df: pd.DataFrame, summaries: list[ColumnSummary]
) -> tuple[frozenset[str], frozenset[str]]:
    """Construye whitelist_numbers y derived_numbers a partir del df + summaries."""
    whitelist: set[str] = set()
    derived: set[str] = set()

    # Filas literales (todos los números que aparecen en los rows).
    for col in df.columns:
        for v in df[col].dropna().tolist():
            _add_number(whitelist, v)

    # Stats por columna.
    for cs in summaries:
        if cs.kind == "numeric":
            for v in (cs.min, cs.max, cs.mean):
                _add_number(whitelist, v)
            # Delta max-min como derivado.
            if cs.min is not None and cs.max is not None:
                _add_number(derived, cs.max - cs.min)
        elif cs.kind == "datetime":
            _add_number(whitelist, cs.min)
            _add_number(whitelist, cs.max)
            if cs.min is not None and cs.max is not None:
                try:
                    delta_years = cs.max.year - cs.min.year
                    _add_number(derived, delta_years)
                except Exception:  # noqa: BLE001
                    pass
        elif cs.top_values:
            for _v, count, pct in cs.top_values:
                _add_number(whitelist, count)
                _add_number(whitelist, round(pct, 1))
                _add_number(whitelist, round(pct))
        if cs.n_unique is not None:
            _add_number(whitelist, cs.n_unique)
        _add_number(whitelist, cs.n_non_null)

    # Total filas — siempre en whitelist.
    _add_number(whitelist, len(df))

    # Tolerancia ±0.5 sobre porcentajes top (para que "33,3%" ≈ "33%").
    for cs in summaries:
        if cs.top_values:
            for _v, _c, pct in cs.top_values:
                _add_number(derived, round(pct))
                _add_number(derived, round(pct, 1))
                _add_number(derived, round(pct * 10) / 10)

    # Limpiar strings vacíos
    whitelist.discard("")
    derived.discard("")
    return frozenset(whitelist), frozenset(derived)


# ----------------------------------------------------------------------
# Summary line formatting
# ----------------------------------------------------------------------


def _format_lines(
    total_rows: int,
    summaries: list[ColumnSummary],
    aggregate_hits: list[str],
) -> list[str]:
    """Texto humano para el bloque "📊 Datos verificados"."""
    if total_rows == 0:
        return ["No se devolvieron filas con la consulta ejecutada."]

    lines = [f"Filas devueltas: {_format_es_co(total_rows)}"]
    for line in aggregate_hits:
        lines.append(line)

    for cs in summaries:
        if cs.kind == "numeric":
            min_s = _format_value(cs.min)
            max_s = _format_value(cs.max)
            mean_s = _format_value(cs.mean) if cs.mean is not None else "—"
            lines.append(
                f"Columna '{cs.name}' (numérica): {cs.n_non_null} valores, "
                f"min = {min_s}, max = {max_s}, media = {mean_s}"
            )
        elif cs.kind == "datetime":
            lines.append(
                f"Columna '{cs.name}' (fecha): {cs.n_non_null} valores, "
                f"desde {_format_value(cs.min)} hasta {_format_value(cs.max)}"
            )
        elif cs.kind in ("categorical", "id") and cs.top_values:
            top_items = "; ".join(
                f"'{v}' ({_format_es_co(c)} = {pct:.1f}%)" for v, c, pct in cs.top_values[:3]
            )
            lines.append(
                f"Columna '{cs.name}' ({cs.kind}): {cs.n_unique} valor(es) único(s) "
                f"sobre {cs.n_non_null} registros. Top: {top_items}"
            )
    return lines


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------


class StatsComputer:
    """Cálculo determinista de estadísticas sobre rows de SODA."""

    @staticmethod
    def compute(rows: list[dict[str, Any]], soql: str) -> Statistics:
        """Devuelve un `Statistics` con whitelist + summary listos para narrar."""
        if not rows:
            return Statistics(
                total_rows=0,
                soql_used=soql,
                summary_lines=["No se devolvieron filas con la consulta ejecutada."],
            )

        df = pd.DataFrame(rows)
        df = _autocast(df)
        summaries = [_summarize_column(df[c]) for c in df.columns]
        aggregate_hits = _detect_aggregates(soql, df)
        whitelist, derived = _build_whitelist(df, summaries)
        summary_lines = _format_lines(len(df), summaries, aggregate_hits)

        return Statistics(
            total_rows=len(df),
            soql_used=soql,
            column_summaries=summaries,
            aggregate_hits=aggregate_hits,
            summary_lines=summary_lines,
            whitelist_numbers=whitelist,
            derived_numbers=derived,
        )
