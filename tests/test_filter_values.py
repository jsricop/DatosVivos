"""Filtros de valor sobre la bodega (ADR-024, Fase 1).

Cubre: condiciones SQL seguras, integración en las plantillas DuckDB,
el profiler (perfil de un Parquet sintético) y la validación contra el
perfil en el endpoint.
"""

from __future__ import annotations

import duckdb
import pytest

from ai_engine.duckdb_templates import build_duckdb_sql, filter_conditions


def col(name, stype, subtype=None, dtype="text"):
    return {
        "col_name": name,
        "semantic_type": stype,
        "semantic_subtype": subtype,
        "socrata_data_type": dtype,
    }


# ----------------------------------------------------------------------
# filter_conditions — SQL seguro
# ----------------------------------------------------------------------


def test_filter_conditions_valor_y_anio():
    conds = filter_conditions([
        {"col": "sector", "kind": "valor", "value": "OFICIAL"},
        {"col": "fecha_corte", "kind": "anio", "value": "2024"},
    ])
    assert conds == [
        "\"sector\" = 'OFICIAL'",
        "EXTRACT(YEAR FROM \"fecha_corte\") = 2024",
    ]


def test_filter_conditions_escapa_comillas_y_descarta_inseguro():
    conds = filter_conditions([
        {"col": "zona", "kind": "valor", "value": "D'ORO"},
        {"col": 'mal"col', "kind": "valor", "value": "X"},   # ident inseguro
        {"col": "anio", "kind": "anio", "value": "2024; DROP"},  # no dígito
    ])
    assert conds == ["\"zona\" = 'D''ORO'"]


# ----------------------------------------------------------------------
# Plantillas con filtros
# ----------------------------------------------------------------------


def test_cuantos_con_filtro():
    r = build_duckdb_sql(
        "Cuántos", [], "x.parquet",
        filters=[{"col": "sector", "kind": "valor", "value": "OFICIAL"}],
    )
    assert r.error is None
    assert "WHERE \"sector\" = 'OFICIAL'" in r.sql
    assert "sector" in r.columns_used


def test_cuantos_sin_filtro_no_cambia():
    r = build_duckdb_sql("Cuántos", [], "x.parquet")
    assert r.sql == "SELECT count(*) AS n FROM {src}"


def test_comparar_filtro_se_suma_al_sin_basura():
    r = build_duckdb_sql(
        "Comparar", [col("municipio", "dimension")], "x.parquet",
        filters=[{"col": "sector", "kind": "valor", "value": "OFICIAL"}],
    )
    assert r.error is None
    assert "IS NOT NULL" in r.sql          # sin_basura sigue
    assert "AND \"sector\" = 'OFICIAL'" in r.sql


def test_tendencia_con_filtro_de_anio():
    r = build_duckdb_sql(
        "Tendencia",
        [col("fecha", "fecha", subtype="date", dtype="DATE")],
        "x.parquet",
        filters=[{"col": "sector", "kind": "valor", "value": "OFICIAL"}],
    )
    assert r.error is None
    assert "WHERE \"sector\" = 'OFICIAL'" in r.sql
    assert "ORDER BY periodo DESC" in r.sql


# ----------------------------------------------------------------------
# Profiler sobre Parquet sintético
# ----------------------------------------------------------------------


@pytest.fixture()
def parquet_sintetico(tmp_path):
    path = str(tmp_path / "d.parquet")
    con = duckdb.connect(":memory:")
    con.execute(f"""
        COPY (
          SELECT 'IE ' || i AS nombre_est,
                 CASE WHEN i % 3 = 0 THEN 'NO OFICIAL' ELSE 'OFICIAL' END AS sector,
                 CASE WHEN i % 4 = 0 THEN 'NR' ELSE 'URBANA' END AS zona,
                 (DATE '2023-01-01' + INTERVAL (i * 7 % 700) DAY) AS fecha_corte,
                 i AS codigo
          FROM range(1, 101) t(i)
        ) TO '{path}' (FORMAT PARQUET)
    """)
    con.close()
    return path


def test_profile_one_extrae_valores_y_anios(parquet_sintetico):
    from scripts.profile_filter_values import profile_one

    vals = profile_one(parquet_sintetico)
    por_col = {}
    for c, kind, v, n in vals:
        por_col.setdefault((c, kind), []).append(v)
    assert set(por_col[("sector", "valor")]) == {"OFICIAL", "NO OFICIAL"}
    # 'NR' es basura y 'zona' queda con UN solo valor útil → no filtra nada
    assert ("zona", "valor") not in por_col
    assert set(por_col[("fecha_corte", "anio")]) >= {"2023", "2024"}
    # identificadores y nombres únicos fuera
    assert all(c not in ("codigo", "nombre_est") for c, _, _, _ in vals)


# ----------------------------------------------------------------------
# Validación contra el perfil (endpoint)
# ----------------------------------------------------------------------


class _Cur:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, sql, params=None):
        pass

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Conn:
    def __init__(self, rows):
        self._rows = rows

    def cursor(self):
        return _Cur(self._rows)


def test_validate_filters_descarta_lo_que_no_existe():
    from api.models.schemas import FilterSpec
    from api.routes.chips import _validate_filters

    perfil = [
        {"col_name": "sector", "kind": "valor", "value": "OFICIAL"},
        {"col_name": "fecha_corte", "kind": "anio", "value": "2024"},
    ]
    validos, note = _validate_filters(_Conn(perfil), "x", [
        FilterSpec(col="sector", value="OFICIAL"),
        FilterSpec(col="sector", value="PRIVADO"),      # no existe
        FilterSpec(col="fecha_corte", value="2024"),
    ])
    assert validos == [
        {"col": "sector", "kind": "valor", "value": "OFICIAL"},
        {"col": "fecha_corte", "kind": "anio", "value": "2024"},
    ]
    assert note is not None and "sector=PRIVADO" in note


def test_validate_filters_sin_filtros():
    from api.routes.chips import _validate_filters

    assert _validate_filters(_Conn([]), "x", None) == ([], None)
