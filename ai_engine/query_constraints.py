"""Extracción de restricciones semánticas desde la pregunta NL (ADR-022 §1.3, Fase 2).

Función pura, sin LLM y sin IO: traduce la pregunta del ciudadano a un conjunto de
restricciones VERIFICABLES que el SoQL generado debe cumplir. Es la entrada de la
capa 3 del verificador (`soql_verifier.verify_static`), que comprueba que la consulta
realmente responde la pregunta (no que devuelva un número plausible-equivocado).

Reusa la taxonomía de TIPO de `soql_templates.ChipTipo` (las 5 formas deterministas).
`detect_tipo()` es la versión determinista de la detección que `nl_to_chips` delega al
LLM (allí los keywords viven en el prompt); acá los aplicamos como reglas para tener
una señal sin costo ni latencia.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from ai_engine.soql_templates import ChipTipo


def _norm(s: str | None) -> str:
    """lowercase + sin acentos, para robustez 'cuántos'/'cuantos'."""
    if not s:
        return ""
    stripped = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    return stripped.lower().strip()


def _has(text: str, patterns: tuple[str, ...]) -> bool:
    return any(p in text for p in patterns)


# Keywords es-CO por intención (mismos que el prompt de nl_to_chips, deterministas acá).
_COUNT_KW = ("cuanto", "cuantos", "cuantas", "numero de", "total de", "cantidad de", "que cantidad")
_GROUPBY_KW = ("compara", "comparar", "comparacion", "por departamento", "por municipio",
               "por cada", "en cada", "por entidad", "por categoria", "por tipo",
               "distribucion", "desglos", "por sexo", "por genero", "por edad")
_RANKING_KW = ("top", "ranking", "los mayores", "los menores", "mejores", "peores",
               "mas alto", "mas alta", "mas bajo", "mas baja", "los 5", "los 10",
               "los primeros", "los ultimos", "que mas", "que menos", "mayor numero")
_DISTINCT_KW = ("unicos", "unicas", "distintos", "distintas", "diferentes")
_TEMPORAL_KW = ("tendencia", "evolucion", "serie de tiempo", "por año", "por ano",
                "anual", "año a año", "ano a ano", "historico", "cada año", "cada ano",
                "a lo largo del tiempo", "desde 20", "entre 20")
_MAPA_KW = ("mapa", "geografico", "por departamento", "por municipio", "por region",
            "territorial", "donde hay")


def detect_tipo(question: str) -> ChipTipo | None:
    """Detecta la forma de consulta (una de las 5) por reglas. None si no es claro.

    Orden de prioridad: Tendencia > Ranking > Comparar/Mapa > Cuántos. Una pregunta
    puede disparar varios; se elige la más específica.
    """
    t = _norm(question)
    if not t:
        return None
    if _has(t, _TEMPORAL_KW):
        return "Tendencia"
    if _has(t, _RANKING_KW):
        return "Ranking"
    if _has(t, _MAPA_KW):
        return "Mapa"
    if _has(t, _GROUPBY_KW):
        return "Comparar"
    if _has(t, _COUNT_KW):
        return "Cuántos"
    return None


@dataclass(frozen=True)
class QueryConstraints:
    """Restricciones que el SoQL generado debe cumplir para responder la pregunta."""

    tipo: ChipTipo | None
    requires_count: bool
    requires_groupby: bool
    requires_orderby_limit: bool
    requires_distinct: bool
    requires_temporal: bool
    requires_geo_filter: bool
    # Tipos semánticos de los que AL MENOS UNO debe aparecer agrupado/usado en el SoQL.
    # Ej. Tendencia → {"fecha"}; Mapa → {"geo"}; Comparar/Ranking → {"dimension","geo"}.
    expected_semantic_types: frozenset[str]

    def is_empty(self) -> bool:
        """True si no se extrajo ninguna señal (no hay nada que verificar)."""
        return not any(
            (
                self.requires_count,
                self.requires_groupby,
                self.requires_orderby_limit,
                self.requires_distinct,
                self.requires_temporal,
                self.requires_geo_filter,
            )
        )


def extract_constraints(
    question: str,
    *,
    has_geo_filter: bool = False,
) -> QueryConstraints:
    """Extrae `QueryConstraints` de la pregunta NL.

    Args:
        question: pregunta del ciudadano en lenguaje natural.
        has_geo_filter: True si el `GeoResolver` resolvió un territorio (dpto/mpio),
            lo que implica que el SoQL debe filtrar por la columna geográfica.
    """
    t = _norm(question)
    tipo = detect_tipo(question)

    requires_temporal = _has(t, _TEMPORAL_KW) or tipo == "Tendencia"
    requires_ranking = _has(t, _RANKING_KW) or tipo == "Ranking"
    requires_groupby = (
        _has(t, _GROUPBY_KW)
        or _has(t, _MAPA_KW)
        or requires_ranking
        or tipo in ("Comparar", "Ranking", "Mapa")
    )
    requires_count = _has(t, _COUNT_KW) or tipo == "Cuántos"
    requires_distinct = _has(t, _DISTINCT_KW)

    expected: set[str] = set()
    if requires_temporal:
        expected.add("fecha")
    if tipo == "Mapa" or _has(t, _MAPA_KW):
        expected.add("geo")
    if requires_groupby and not requires_temporal:
        # Una comparación/ranking genérico agrupa por una dimensión o por geografía.
        expected.update({"dimension", "geo"})

    return QueryConstraints(
        tipo=tipo,
        requires_count=requires_count,
        requires_groupby=requires_groupby,
        requires_orderby_limit=requires_ranking,
        requires_distinct=requires_distinct,
        requires_temporal=requires_temporal,
        requires_geo_filter=has_geo_filter,
        expected_semantic_types=frozenset(expected),
    )
