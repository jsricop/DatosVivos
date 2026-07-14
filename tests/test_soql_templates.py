"""Unit tests for ai_engine.soql_templates.build_soql."""

from __future__ import annotations

from ai_engine.soql_templates import build_soql


def col(name, stype, subtype=None, data_type=None):
    return {
        "col_name": name,
        "semantic_type": stype,
        "semantic_subtype": subtype,
        "socrata_data_type": data_type,
    }


def test_cuantos_no_requiere_columnas():
    r = build_soql("Cuántos", [])
    assert r.error is None
    assert r.soql == "SELECT count(*) AS n"
    assert r.columns_used == []


def test_comparar_requiere_dimension():
    r = build_soql("Comparar", [])
    assert r.error is not None
    assert "dimension" in r.error


def test_comparar_con_dimension():
    r = build_soql("Comparar", [col("departamento", "dimension"), col("municipio", "dimension")])
    assert r.error is None
    assert "departamento" in r.soql  # toma la primera (más confianza)
    assert "GROUP BY departamento" in r.soql
    assert "ORDER BY n DESC" in r.soql
    assert "LIMIT 10" in r.soql
    assert r.columns_used == ["departamento"]


def test_ranking_default_count_sin_metrica():
    r = build_soql("Ranking", [col("entidad", "dimension")])
    assert r.error is None
    assert "count(*)" in r.soql.lower()
    assert "sum(" not in r.soql.lower()


def test_ranking_usa_sum_con_metrica():
    r = build_soql("Ranking", [col("entidad", "dimension"), col("monto", "metrica")])
    assert r.error is None
    assert "sum(monto)" in r.soql
    assert r.columns_used == ["entidad", "monto"]


def test_ranking_force_count_si_use_metric_false():
    r = build_soql(
        "Ranking",
        [col("entidad", "dimension"), col("monto", "metrica")],
        use_metric=False,
    )
    assert "sum(" not in r.soql.lower()
    assert "count(*)" in r.soql.lower()


def test_tendencia_requiere_fecha():
    r = build_soql("Tendencia", [col("x", "dimension")])
    assert r.error is not None
    assert "fecha" in r.error.lower()


def test_tendencia_date_real_usa_date_trunc_ym():
    r = build_soql(
        "Tendencia",
        [col("fecha_evento", "fecha", subtype="date", data_type="calendar_date")],
    )
    assert r.error is None
    assert "date_trunc_ym(fecha_evento)" in r.soql


def test_tendencia_pide_los_ultimos_periodos():
    """DESC LIMIT 60 = los ÚLTIMOS 60 periodos. Con ASC un dataset 2010-2025
    respondía '¿está subiendo?' con datos de 2010-2014 (2026-07-13). El
    endpoint invierte a ascendente antes de responder."""
    r = build_soql(
        "Tendencia",
        [col("fecha_evento", "fecha", subtype="date", data_type="calendar_date")],
    )
    assert "ORDER BY periodo DESC" in r.soql


def test_tendencia_year_como_numero_no_usa_date_trunc():
    """`año` (semantic=fecha, data_type=number) NO debe envolverse en
    date_trunc_ym — SODA falla con type-mismatch. Group by raw."""
    r = build_soql(
        "Tendencia",
        [col("anio", "fecha", subtype="year", data_type="number")],
    )
    assert r.error is None
    assert "date_trunc_ym" not in r.soql
    assert "GROUP BY periodo" in r.soql


def test_tendencia_fecha_como_texto_no_usa_date_trunc():
    r = build_soql(
        "Tendencia",
        [col("fecha_str", "fecha", subtype="date", data_type="text")],
    )
    assert r.error is None
    assert "date_trunc_ym" not in r.soql


def test_mapa_requiere_geo():
    r = build_soql("Mapa", [col("x", "dimension")])
    assert r.error is not None
    assert "geo" in r.error.lower()


def test_mapa_con_geo():
    r = build_soql("Mapa", [col("codigo_departamento", "geo")])
    assert r.error is None
    assert "codigo_departamento" in r.soql
    assert "LIMIT 32" in r.soql


def test_identificador_invalido_se_salta():
    r = build_soql(
        "Comparar",
        [col("columna con espacio", "dimension"), col("buena_col", "dimension")],
    )
    assert r.error is None
    assert "buena_col" in r.soql
    assert "columna con espacio" not in r.soql


def test_identificador_todo_invalido_falla():
    r = build_soql(
        "Comparar",
        [col("bad ident", "dimension"), col("1starts_with_digit", "dimension")],
    )
    assert r.error is not None


def test_tipo_desconocido():
    r = build_soql("XYZ", [])  # type: ignore[arg-type]
    assert r.error is not None
    assert "desconocido" in r.error.lower()
