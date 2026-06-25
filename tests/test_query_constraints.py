"""Unit tests para ai_engine.query_constraints (ADR-022 Fase 2)."""

from __future__ import annotations

from ai_engine.query_constraints import detect_tipo, extract_constraints


def test_detect_tipo_cuantos():
    assert detect_tipo("¿Cuántos colegios públicos hay en Boyacá?") == "Cuántos"


def test_detect_tipo_tendencia_gana_a_count():
    # "cuántos por año" → la temporalidad manda.
    assert detect_tipo("¿Cuántos homicidios por año en Antioquia?") == "Tendencia"


def test_detect_tipo_ranking():
    assert detect_tipo("Top 5 municipios con más contratos") == "Ranking"


def test_detect_tipo_mapa():
    assert detect_tipo("Homicidios por departamento") == "Mapa"


def test_detect_tipo_none():
    assert detect_tipo("háblame de educación") is None


def test_constraints_count():
    c = extract_constraints("¿Cuántos colegios hay?")
    assert c.requires_count is True
    assert c.requires_groupby is False
    assert c.is_empty() is False


def test_constraints_temporal_expects_fecha():
    c = extract_constraints("Tendencia de homicidios por año")
    assert c.requires_temporal is True
    assert "fecha" in c.expected_semantic_types


def test_constraints_ranking_expects_orderby_limit():
    c = extract_constraints("Top 10 entidades con mayor número de contratos")
    assert c.requires_orderby_limit is True
    assert c.requires_groupby is True


def test_constraints_mapa_expects_geo():
    c = extract_constraints("Homicidios por municipio")
    assert "geo" in c.expected_semantic_types


def test_constraints_geo_filter_from_resolver():
    c = extract_constraints("¿Cuántos colegios en Boyacá?", has_geo_filter=True)
    assert c.requires_geo_filter is True


def test_constraints_empty_for_vague():
    c = extract_constraints("información sobre salud")
    assert c.is_empty() is True
