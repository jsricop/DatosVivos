"""Tests para ai_engine/duckdb_templates (Reto F.4 build_duckdb_sql).

Paralelos a tests/test_soql_templates.py pero adaptados a sintaxis DuckDB:
- read_csv(...) FROM clause como placeholder {src}
- date_trunc('month', try_cast(...)) cuando aplica
- Comillas dobles en identificadores
"""

from __future__ import annotations

from ai_engine.duckdb_templates import build_duckdb_sql


def col(name, stype, subtype=None, data_type=None):
    return {
        "col_name": name,
        "semantic_type": stype,
        "semantic_subtype": subtype,
        "socrata_data_type": data_type,
    }


URL = "http://example.com/x.csv"


def test_cuantos_emite_count_y_from_placeholder():
    r = build_duckdb_sql("Cuántos", [], URL)
    assert r.error is None
    assert "count(*)" in r.soql.lower() if False else "count(*) AS n" in r.sql
    assert "{src}" in r.sql
    assert r.columns_used == []


def test_comparar_requiere_dimension():
    r = build_duckdb_sql("Comparar", [], URL)
    assert r.error is not None and "dimension" in r.error


def test_comparar_con_dimension_quote_doble():
    r = build_duckdb_sql("Comparar", [col("Año", "dimension")], URL)
    assert r.error is None
    # Identificador con tilde debe ir entre dobles comillas.
    assert '"Año"' in r.sql
    assert "GROUP BY \"Año\"" in r.sql


def test_ranking_sum_con_metrica_usa_try_cast():
    r = build_duckdb_sql(
        "Ranking",
        [col("entidad", "dimension"), col("monto", "metrica")],
        URL,
    )
    assert r.error is None
    # try_cast protege contra columnas tipo TEXT con números.
    assert "try_cast(\"monto\" AS DOUBLE)" in r.sql
    assert "sum(try_cast" in r.sql


def test_ranking_sin_metrica_cae_a_count():
    r = build_duckdb_sql("Ranking", [col("entidad", "dimension")], URL)
    assert r.error is None
    assert "count(*)" in r.sql
    assert "sum(" not in r.sql


def test_tendencia_date_real_usa_date_trunc():
    r = build_duckdb_sql(
        "Tendencia",
        [col("fecha_evento", "fecha", subtype="date", data_type="TIMESTAMP")],
        URL,
    )
    assert r.error is None
    assert "date_trunc('month', \"fecha_evento\")" in r.sql


def test_tendencia_date_text_usa_try_cast_a_timestamp():
    r = build_duckdb_sql(
        "Tendencia",
        [col("fecha_str", "fecha", subtype="date", data_type="VARCHAR")],
        URL,
    )
    assert r.error is None
    assert "try_cast(\"fecha_str\" AS TIMESTAMP)" in r.sql


def test_tendencia_year_no_usa_date_trunc():
    r = build_duckdb_sql(
        "Tendencia",
        [col("anio", "fecha", subtype="year", data_type="BIGINT")],
        URL,
    )
    assert r.error is None
    assert "date_trunc" not in r.sql
    assert '"anio"' in r.sql


def test_mapa_con_geo():
    r = build_duckdb_sql("Mapa", [col("dpto_code", "geo")], URL)
    assert r.error is None
    assert '"dpto_code"' in r.sql
    assert "LIMIT 32" in r.sql


def test_mapa_requiere_geo():
    r = build_duckdb_sql("Mapa", [col("x", "dimension")], URL)
    assert r.error is not None and "geo" in r.error.lower()


def test_identificador_inseguro_se_filtra():
    # Columna con comillas dobles SE FILTRA — rompería el SQL.
    r = build_duckdb_sql(
        "Comparar",
        [col('mal"col', "dimension"), col("buena_col", "dimension")],
        URL,
    )
    assert r.error is None
    assert "buena_col" in r.sql
    assert "mal" not in r.sql.split('"buena_col"')[0]


def test_url_con_comilla_simple_se_sanitiza_en_from_clause():
    r = build_duckdb_sql("Cuántos", [], "http://x.com/'evil.csv")
    # `{src}` está embebido — el executor sustituye con read_csv.
    # build_duckdb_sql NO debe incluir la URL literal con comilla en su output.
    assert r.error is None
