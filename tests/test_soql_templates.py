"""Unit tests for ai_engine.soql_templates.build_soql."""

from __future__ import annotations

from ai_engine.soql_templates import build_soql


def test_cuantos_no_requiere_columnas():
    r = build_soql("Cuántos", {})
    assert r.error is None
    assert r.soql == "SELECT count(*) AS n"
    assert r.columns_used == []


def test_comparar_requiere_dimension():
    r = build_soql("Comparar", {})
    assert r.error is not None
    assert "dimension" in r.error


def test_comparar_con_dimension():
    r = build_soql("Comparar", {"dimension": ["departamento", "municipio"]})
    assert r.error is None
    assert "departamento" in r.soql  # toma la primera (más confianza)
    assert "GROUP BY departamento" in r.soql
    assert "ORDER BY n DESC" in r.soql
    assert "LIMIT 10" in r.soql
    assert r.columns_used == ["departamento"]


def test_ranking_default_count_sin_metrica():
    r = build_soql("Ranking", {"dimension": ["entidad"]})
    assert r.error is None
    assert "count(*)" in r.soql.lower()
    assert "sum(" not in r.soql.lower()
    assert r.columns_used == ["entidad"]


def test_ranking_usa_sum_con_metrica():
    r = build_soql(
        "Ranking",
        {"dimension": ["entidad"], "metrica": ["monto_total"]},
    )
    assert r.error is None
    assert "sum(monto_total)" in r.soql
    assert "AS total" in r.soql
    assert r.columns_used == ["entidad", "monto_total"]


def test_ranking_force_count_si_use_metric_false():
    r = build_soql(
        "Ranking",
        {"dimension": ["entidad"], "metrica": ["monto"]},
        use_metric=False,
    )
    assert "sum(" not in r.soql.lower()
    assert "count(*)" in r.soql.lower()


def test_tendencia_requiere_fecha():
    r = build_soql("Tendencia", {"dimension": ["x"]})
    assert r.error is not None
    assert "fecha" in r.error.lower()


def test_tendencia_usa_date_trunc_ym():
    r = build_soql("Tendencia", {"fecha": ["fecha_evento"]})
    assert r.error is None
    assert "date_trunc_ym(fecha_evento)" in r.soql
    assert "GROUP BY periodo" in r.soql
    assert "ORDER BY periodo" in r.soql
    assert r.columns_used == ["fecha_evento"]


def test_mapa_requiere_geo():
    r = build_soql("Mapa", {"dimension": ["x"]})
    assert r.error is not None
    assert "geo" in r.error.lower()


def test_mapa_con_geo():
    r = build_soql("Mapa", {"geo": ["codigo_departamento"]})
    assert r.error is None
    assert "codigo_departamento" in r.soql
    assert "GROUP BY codigo_departamento" in r.soql
    assert "LIMIT 32" in r.soql


def test_identificador_invalido_rechazado():
    # nombre con espacio o caracteres raros no debe filtrarse a la SoQL
    r = build_soql("Comparar", {"dimension": ["columna con espacio", "buena_col"]})
    assert r.error is None
    assert "buena_col" in r.soql
    assert "columna con espacio" not in r.soql


def test_identificador_todo_invalido_falla():
    r = build_soql("Comparar", {"dimension": ["bad ident", "1starts_with_digit"]})
    assert r.error is not None


def test_tipo_desconocido():
    r = build_soql("XYZ", {})  # type: ignore[arg-type]
    assert r.error is not None
    assert "desconocido" in r.error.lower()
