"""Clasificador heurístico de columnas Socrata por tipo semántico (D.6).

Dado (col_name, data_type, description), devuelve:
  (semantic_type, semantic_subtype, confidence, reason)

Tipos:
  geo        → code | name | coord
  fecha      → year | date | period
  metrica    → count | currency | rate | generic
  dimension  → demographic | administrative | educational | status | other
  exclude    → id | url | text_long | other

Confidence:
  high   → match unívoco (nombre canónico o description literal específica)
  medium → match por keyword + data_type consistente
  low    → solo data_type, sin signal de nombre/description

Diseño: reglas en cascada con cortocircuito. Las reglas más específicas
primero (description literal > nombre regex > data_type). Sin LLM.

Reutilizable desde scripts/curate_columns_heuristic.py y tests.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnClassification:
    semantic_type: str        # geo|fecha|metrica|dimension|exclude
    semantic_subtype: str | None
    confidence: str           # high|medium|low
    reason: str               # auditable trace de qué regla aplicó


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def _norm(s: str | None) -> str:
    if not s:
        return ""
    return _strip_accents(s).lower().strip()


# ----------------------------------------------------------------------
# Patrones por nombre column — alta especificidad primero
# ----------------------------------------------------------------------


# GEO: códigos DIVIPOLA. Nombres muy estandarizados en datasets colombianos.
_GEO_CODE_PATTERNS = [
    r"^cod[_-]?dane[_-]?(dpto|departamento|departament|departamiento)",
    r"^cod[_-]?dane[_-]?(mun|mpio|municipio|municipal)",
    r"^cod[_-]?(dpto|departamento|departamento_residencia|departament|depa|deptos?)$",
    r"^cod[_-]?(mun|mpio|municipio|mpio_residencia)$",
    r"^codigo[_-]?(dpto|departamento|mun|mpio|municipio)",
    r"^c_(dpto|mpio|mun)$",
    r"^id[_-]?(dpto|mpio|departamento|municipio)$",
    r"^divipola$",
    r"^cod_localidad$",
    r"^localidad_codigo$",
]
_GEO_NAME_PATTERNS = [
    r"^(nombre[_-]?)?(dpto|departamento|departament)(_residencia|_corte)?$",
    r"^(nombre[_-]?)?(mun|mpio|municipio|municipal)(_residencia|_corte)?$",
    r"^nom[_-]?(dpto|departamento|mun|mpio|municipio)$",
    r"^ciudad$",
    r"^localidad$",
    r"^region$",
    r"^ubicacion$",
    r"^direccion$",
]
_GEO_COORD_PATTERNS = [
    r"^lat(itud)?$",
    r"^lon(gitud)?$",
    r"^lng$",
    r"^coordenadas?$",
    r"^geo(_punto)?$",
    r"^punto_(referencia|geografico)$",
]

# FECHA
_FECHA_YEAR_PATTERNS = [
    r"^(an[oñ]o?|year|vigencia|periodo|periodo_anual|annio)$",
    r"^a[nñ]o(_corte|_reporte|_vigencia|_inicio)?$",
    r"^vigencia(_anual)?$",
]
_FECHA_DATE_PATTERNS = [
    r"^fecha(_de_)?[a-z_]*$",
    r"^date$",
    r"^timestamp$",
    r"^periodo[_-]?(inicio|fin|corte)$",
    r"^trimestre$",
    r"^mes(_corte)?$",
]
_FECHA_PERIOD_PATTERNS = [
    r"^periodo$",
    r"^semestre$",
]

# MÉTRICA — números que se SUMAN o promedian
_METRICA_COUNT_PATTERNS = [
    r"^(total|n_|num_|numero_|cantidad_|count_|conteo_)",
    r"^(personas|estudiantes|matriculados?|matriculas?|nacidos?|fallecidos?|casos|usuarios|beneficiarios|atendidos|graduados|inscritos|contratos|tramites|servicios|alumnos)$",
    r"_(total|count|n|num|cantidad|matriculas?)$",
]
_METRICA_CURRENCY_PATTERNS = [
    r"^(monto|valor|costo|precio|presupuesto|inversion|gasto|ingreso|salario|recaudo)",
    r"_(monto|valor|costo|precio|cop|usd|pesos)$",
    r"^valor_(contrato|adjudicado|estimado|total)$",
]
_METRICA_RATE_PATTERNS = [
    r"^(tasa|porcentaje|pct|ratio|indice|cobertura)",
    r"_(porcentaje|tasa|pct|ratio)$",
]

# DIMENSIONES por subgrupo
_DIM_DEMOGRAPHIC_PATTERNS = [
    r"^(genero|sexo)$",
    r"^edad(_grupo|_rango)?$",
    r"^grupo_etario$",
    r"^etnia$",
    r"^estado_civil$",
    r"^nivel_socioeconomico$",
]
_DIM_EDUCATIONAL_PATTERNS = [
    r"^nivel(_educativo|_academico|_formacion)?$",
    r"^jornada$",
    r"^modalidad$",
    r"^programa(_academico)?$",
    r"^facultad$",
    r"^carrera$",
    r"^grado$",
    r"^calendario$",
]
_DIM_ADMINISTRATIVE_PATTERNS = [
    r"^sector$",
    r"^tipo(_contrato|_documento|_servicio|_proceso|_solicitud|_persona)?$",
    r"^categoria$",
    r"^subcategoria$",
    r"^clasificacion$",
    r"^naturaleza$",
    r"^modalidad_(contrato|proceso)$",
    r"^estado(_proceso|_solicitud)?$",
    r"^entidad$",
]
_DIM_STATUS_PATTERNS = [
    r"^estado$",
    r"^activo$",
    r"^vigente$",
    r"^aprobado$",
]

# EXCLUIR
_EXCLUDE_ID_PATTERNS = [
    r"^id$",
    r"^id_[a-z_]+$",
    r"^[a-z_]+_id$",
    r"^uuid$",
    r"^codigo_unico$",
    r"^numero_documento$",
    r"^cedula$",
    r"^numero_radicado$",
]
_EXCLUDE_URL_PATTERNS = [
    r"^(url|enlace|link|sitio_web|pagina_web)$",
    r"^(url|link|enlace)_",
    r"_(url|link|enlace)$",
]
_EXCLUDE_TEXT_LONG_PATTERNS = [
    r"^(observacion|observaciones|descripcion|comentarios?|notas?|justificacion|motivo|detalle)$",
    r"_(observacion|descripcion|comentarios|notas)$",
]


# ----------------------------------------------------------------------
# Description-based signals (de Socrata column.description)
# ----------------------------------------------------------------------


_DESC_GEO_CODE = re.compile(
    r"\b(c[óo]digo|cod\.?)\b.{0,30}\b(dane|divipola|departamento|municipio|mpio|dpto)\b",
    re.IGNORECASE,
)
_DESC_GEO_NAME = re.compile(
    r"\b(nombre|denominaci[óo]n)\b.{0,20}\b(departamento|municipio|mpio|ciudad|localidad)\b",
    re.IGNORECASE,
)
_DESC_FECHA = re.compile(
    r"\b(fecha|a[nñ]o|periodo|vigencia|year)\b",
    re.IGNORECASE,
)
_DESC_METRICA = re.compile(
    r"\b(total|cantidad|n[uú]mero de|valor (en )?pesos|monto|tasa|porcentaje)\b",
    re.IGNORECASE,
)


# ----------------------------------------------------------------------
# Classifier principal
# ----------------------------------------------------------------------


def _match_any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def classify_column(
    col_name: str,
    data_type: str | None = None,
    description: str | None = None,
) -> ColumnClassification:
    """Clasifica una columna en uno de los 5 tipos semánticos."""
    name = _norm(col_name)
    if not name:
        return ColumnClassification("exclude", "other", "low", "empty name")

    dtype = (data_type or "").lower()
    desc = description or ""
    desc_norm = _norm(desc)

    # ------------------------------------------------------------------
    # 1. EXCLUDE primero (ids, urls, text_long) — para no clasificar como
    #    geo o métrica falsamente.
    # ------------------------------------------------------------------
    if _match_any(_EXCLUDE_ID_PATTERNS, name):
        return ColumnClassification("exclude", "id", "high",
                                    f"name match id pattern: {name}")
    if _match_any(_EXCLUDE_URL_PATTERNS, name):
        return ColumnClassification("exclude", "url", "high",
                                    f"name match url: {name}")
    if _match_any(_EXCLUDE_TEXT_LONG_PATTERNS, name):
        return ColumnClassification("exclude", "text_long", "high",
                                    f"name match text_long: {name}")

    # ------------------------------------------------------------------
    # 2. GEO
    # ------------------------------------------------------------------
    if _match_any(_GEO_CODE_PATTERNS, name):
        return ColumnClassification("geo", "code", "high",
                                    f"name match geo_code: {name}")
    if _match_any(_GEO_COORD_PATTERNS, name):
        return ColumnClassification("geo", "coord", "high",
                                    f"name match geo_coord: {name}")
    if _match_any(_GEO_NAME_PATTERNS, name):
        return ColumnClassification("geo", "name", "high",
                                    f"name match geo_name: {name}")
    if _DESC_GEO_CODE.search(desc):
        return ColumnClassification("geo", "code", "high",
                                    "description matches 'código DANE/DIVIPOLA'")
    if _DESC_GEO_NAME.search(desc):
        return ColumnClassification("geo", "name", "medium",
                                    "description matches 'nombre departamento/municipio'")
    if dtype in ("location", "point"):
        return ColumnClassification("geo", "coord", "high",
                                    f"data_type={dtype}")

    # ------------------------------------------------------------------
    # 3. FECHA
    # ------------------------------------------------------------------
    if _match_any(_FECHA_YEAR_PATTERNS, name):
        return ColumnClassification("fecha", "year", "high",
                                    f"name match year: {name}")
    if _match_any(_FECHA_DATE_PATTERNS, name):
        return ColumnClassification("fecha", "date", "high",
                                    f"name match date: {name}")
    if _match_any(_FECHA_PERIOD_PATTERNS, name):
        return ColumnClassification("fecha", "period", "high",
                                    f"name match period: {name}")
    if dtype in ("calendar_date", "calendardate", "datetime", "date"):
        return ColumnClassification("fecha", "date", "high",
                                    f"data_type={dtype}")
    if _DESC_FECHA.search(desc) and dtype in ("text", "number"):
        # description menciona fecha pero data_type es text → probable fecha
        # codificada como string. Confidence medium.
        return ColumnClassification("fecha", "date", "medium",
                                    "description mentions fecha/año/periodo")

    # ------------------------------------------------------------------
    # 4. MÉTRICA — solo si data_type es numérico
    # ------------------------------------------------------------------
    if dtype in ("number", "money", "numeric", "double", "int"):
        if _match_any(_METRICA_CURRENCY_PATTERNS, name):
            return ColumnClassification("metrica", "currency", "high",
                                        f"name match currency: {name}")
        if _match_any(_METRICA_RATE_PATTERNS, name):
            return ColumnClassification("metrica", "rate", "high",
                                        f"name match rate: {name}")
        if _match_any(_METRICA_COUNT_PATTERNS, name):
            return ColumnClassification("metrica", "count", "high",
                                        f"name match count: {name}")
        if _DESC_METRICA.search(desc):
            return ColumnClassification("metrica", "generic", "medium",
                                        "description mentions total/cantidad")
        # Number sin signal de nombre/desc → genérico low
        return ColumnClassification("metrica", "generic", "low",
                                    f"data_type=number, sin signal de nombre")

    # ------------------------------------------------------------------
    # 5. DIMENSIONS
    # ------------------------------------------------------------------
    if _match_any(_DIM_DEMOGRAPHIC_PATTERNS, name):
        return ColumnClassification("dimension", "demographic", "high",
                                    f"name match demographic: {name}")
    if _match_any(_DIM_EDUCATIONAL_PATTERNS, name):
        return ColumnClassification("dimension", "educational", "high",
                                    f"name match educational: {name}")
    if _match_any(_DIM_ADMINISTRATIVE_PATTERNS, name):
        return ColumnClassification("dimension", "administrative", "high",
                                    f"name match administrative: {name}")
    if _match_any(_DIM_STATUS_PATTERNS, name):
        return ColumnClassification("dimension", "status", "high",
                                    f"name match status: {name}")

    # ------------------------------------------------------------------
    # 6. Fallback — text corto sin signal → dimension other / low
    # ------------------------------------------------------------------
    if dtype == "text":
        return ColumnClassification("dimension", "other", "low",
                                    "text sin signal de nombre, asumido dim other")

    return ColumnClassification("exclude", "other", "low",
                                f"sin signal: name={name}, dtype={dtype}")
