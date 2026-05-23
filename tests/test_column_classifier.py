"""Tests para ai_engine/column_classifier.py.

Cubre las 5 categorías + sub-tipos + fallbacks. Smoke representativo de
patrones reales del catálogo Socrata colombiano.
"""

from __future__ import annotations

import pytest

from ai_engine.column_classifier import classify_column


# ---- GEO ----

@pytest.mark.parametrize("name,expected_sub", [
    ("cod_dpto", "code"),
    ("cod_dane_municipio", "code"),
    ("codigodepartamentoatencion", "code"),  # description-based
    ("codigomunicipio", "code"),
    ("c_dpto", "code"),
])
def test_geo_code_from_name(name, expected_sub):
    desc = "Código DANE del departamento" if "departamento" in name.lower() else None
    r = classify_column(name, "number", desc)
    assert r.semantic_type == "geo"
    assert r.semantic_subtype == expected_sub
    assert r.confidence == "high"


def test_geo_name():
    r = classify_column("nombre_municipio", "text")
    assert r.semantic_type == "geo"
    assert r.semantic_subtype == "name"


def test_geo_coord_by_name():
    r = classify_column("lat", "number")
    assert (r.semantic_type, r.semantic_subtype) == ("geo", "coord")


def test_geo_coord_by_data_type():
    r = classify_column("ubicacion_punto", "location")
    assert r.semantic_type == "geo"


# ---- FECHA ----

def test_fecha_year_by_name():
    r = classify_column("ano_corte", "number")
    assert (r.semantic_type, r.semantic_subtype) == ("fecha", "year")


def test_fecha_date_by_data_type():
    r = classify_column("fecha_reporte", "calendar_date")
    assert r.semantic_type == "fecha"


def test_fecha_date_text_with_description():
    r = classify_column("fecha_reporte_web", "text", "Fecha de publicación en sitio web")
    assert r.semantic_type == "fecha"
    assert r.confidence in ("high", "medium")


# ---- MÉTRICA ----

def test_metrica_count():
    r = classify_column("total_matriculas", "number")
    assert (r.semantic_type, r.semantic_subtype) == ("metrica", "count")


def test_metrica_currency():
    r = classify_column("valor_contrato", "number")
    assert (r.semantic_type, r.semantic_subtype) == ("metrica", "currency")


def test_metrica_rate():
    r = classify_column("porcentaje_cobertura", "number")
    assert (r.semantic_type, r.semantic_subtype) == ("metrica", "rate")


def test_metrica_generic_fallback():
    """Number sin signal de nombre → metrica.generic low confidence."""
    r = classify_column("medicion_x", "number")
    assert r.semantic_type == "metrica"
    assert r.semantic_subtype == "generic"
    assert r.confidence == "low"


# ---- DIMENSION ----

@pytest.mark.parametrize("name,sub", [
    ("genero", "demographic"),
    ("sexo", "demographic"),
    ("grupo_etario", "demographic"),
    ("nivel_educativo", "educational"),
    ("jornada", "educational"),
    ("sector", "administrative"),
    ("tipo_contrato", "administrative"),
    ("modalidad", "educational"),  # nota: modalidad cae en educational primero
])
def test_dimension_subtypes(name, sub):
    r = classify_column(name, "text")
    assert r.semantic_type == "dimension"
    assert r.semantic_subtype == sub


def test_dimension_other_fallback():
    """text sin patrón conocido → dimension.other low."""
    r = classify_column("variable_x", "text")
    assert r.semantic_type == "dimension"
    assert r.semantic_subtype == "other"
    assert r.confidence == "low"


# ---- EXCLUDE ----

def test_exclude_id():
    r = classify_column("id_solicitud", "number")
    assert r.semantic_type == "exclude"
    assert r.semantic_subtype == "id"


def test_exclude_url_prefix():
    r = classify_column("url_documento", "text")
    assert r.semantic_type == "exclude"
    assert r.semantic_subtype == "url"


def test_exclude_url_suffix():
    r = classify_column("documento_url", "text")
    assert r.semantic_type == "exclude"
    assert r.semantic_subtype == "url"


def test_exclude_text_long():
    r = classify_column("observaciones", "text")
    assert r.semantic_type == "exclude"
    assert r.semantic_subtype == "text_long"


# ---- Edge cases ----

def test_empty_name():
    r = classify_column("", "text")
    assert r.semantic_type == "exclude"


def test_description_overrides_text_dtype_to_fecha():
    """Si name es ambiguo pero description menciona fecha y dtype text → fecha medium."""
    r = classify_column("campo_x", "text", "Fecha de inicio del proceso")
    assert r.semantic_type == "fecha"
    assert r.confidence == "medium"


def test_id_no_falsa_geo():
    """`id_municipio` matchea exclude.id, NO geo.code."""
    r = classify_column("id_municipio", "number")
    assert r.semantic_type == "exclude"
