"""Constructor SoQL determinista por TIPO de chip (Hito 1, Fase B).

Plantillas puras: dado un TIPO y el diccionario de columnas curadas
(`semantic_type → [col_name]`), devuelve la query SoQL exacta a enviar a
SODA. Sin LLM, sin IO. La selección de columna usa el primer nombre del
bucket — el caller debe entregar `by_type` ya ordenado por confidence
(B.1 lo hace).

Decisión de diseño (memoria `project_soql_count_default`): `COUNT(*)` es
la métrica DEFAULT en cada TIPO. `SUM(métrica)` se usa SOLO si el dataset
tiene una columna curada como `metrica` Y el TIPO lo soporta (Ranking).
Esto sube cobertura por TIPO de ~30% a ~60-70% (la mayoría de datasets
no tienen métrica sumable explícita).

Plantillas:
  Cuántos    → SELECT count(*) AS n
  Comparar   → SELECT {dim}, count(*) AS n GROUP BY {dim} ORDER BY n DESC LIMIT 10
  Ranking    → idem Comparar (default) o con SUM(metrica) si aplica
  Tendencia  → SELECT date_trunc_ym({fecha}) AS periodo, count(*) AS n GROUP BY periodo ORDER BY periodo LIMIT 60
  Mapa       → SELECT {geo}, count(*) AS n GROUP BY {geo} ORDER BY n DESC LIMIT 32
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

ChipTipo = Literal["Cuántos", "Comparar", "Ranking", "Tendencia", "Mapa"]
SemanticType = Literal["geo", "fecha", "metrica", "dimension", "exclude"]

# Identificador SoQL válido: letras/dígitos/guion bajo, debe empezar con letra
# o guion bajo. SoQL acepta más, pero esto es lo que produce el campo
# `columns_field_name` del Discovery (snake_case).
_IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


@dataclass
class BuildResult:
    """Resultado de `build_soql`: query + columnas usadas + error si falló."""

    soql: str
    columns_used: list[str] = field(default_factory=list)
    error: str | None = None


def _safe_ident(name: str) -> str | None:
    """Devuelve el name si es identificador SoQL válido; None si no."""
    if not name or not _IDENT_RE.match(name):
        return None
    return name


def _pick(by_type: dict[str, list[str]], stype: SemanticType) -> str | None:
    """Toma la primera columna del bucket (ya viene ordenada por confidence)."""
    candidates = by_type.get(stype) or []
    for c in candidates:
        s = _safe_ident(c)
        if s:
            return s
    return None


def build_soql(
    tipo: ChipTipo,
    by_type: dict[str, list[str]],
    *,
    use_metric: bool = True,
) -> BuildResult:
    """Construye la query SoQL para el `tipo` solicitado.

    Args:
        tipo: uno de los 5 chips de TIPO.
        by_type: índice `semantic_type → [col_name]` (de B.1 — ya ordenado
            por confidence DESC).
        use_metric: si True (default), Ranking usa SUM(metrica) cuando hay
            columna métrica; si False, fuerza COUNT(*).

    Returns:
        BuildResult con `soql` poblada si se pudo construir, o `error` con
        el motivo (ej. "Tendencia requiere columna fecha").
    """
    if tipo == "Cuántos":
        return BuildResult(soql="SELECT count(*) AS n", columns_used=[])

    if tipo in ("Comparar", "Ranking"):
        dim = _pick(by_type, "dimension")
        if not dim:
            return BuildResult(
                soql="",
                error=f"{tipo} requiere ≥1 columna de tipo `dimension`",
            )
        if tipo == "Ranking" and use_metric:
            metrica = _pick(by_type, "metrica")
            if metrica:
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
        # Default COUNT(*) — funciona para Comparar y Ranking sin métrica.
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
        fecha = _pick(by_type, "fecha")
        if not fecha:
            return BuildResult(
                soql="", error="Tendencia requiere ≥1 columna de tipo `fecha`"
            )
        return BuildResult(
            soql=(
                f"SELECT date_trunc_ym({fecha}) AS periodo, count(*) AS n "
                f"GROUP BY periodo "
                f"ORDER BY periodo "
                f"LIMIT 60"
            ),
            columns_used=[fecha],
        )

    if tipo == "Mapa":
        geo = _pick(by_type, "geo")
        if not geo:
            return BuildResult(
                soql="", error="Mapa requiere ≥1 columna de tipo `geo`"
            )
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
