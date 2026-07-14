"""Unit tests para ai_engine.soql_verifier (ADR-022 Fase 2, capas 1 y 3)."""

from __future__ import annotations

from ai_engine.query_constraints import extract_constraints
from ai_engine.soql_verifier import verify_static


def _cols(*specs):
    """specs: (col_name, semantic_type)."""
    return [{"col_name": n, "semantic_type": t, "semantic_subtype": None,
             "socrata_data_type": None} for n, t in specs]


VALID = {"cod_dpto", "municipio", "anio", "valor", "n"}
CURATED = _cols(
    ("cod_dpto", "geo"),
    ("municipio", "geo"),
    ("anio", "fecha"),
    ("valor", "metrica"),
)


def _verify(soql, question, **kw):
    return verify_static(
        soql,
        valid_cols=VALID,
        curated_columns=CURATED,
        constraints=extract_constraints(question, **kw),
    )


# ---------- Capa 1: sintaxis ----------

def test_rejects_non_select():
    r = _verify("DELETE FROM x", "cuántos")
    assert not r.ok and r.layer_failed == "syntax"


def test_rejects_from_clause():
    r = _verify("SELECT count(*) AS n FROM tabla", "cuántos colegios")
    assert not r.ok and r.layer_failed == "syntax"
    assert "FROM" in r.error_message


def test_rejects_unknown_column():
    r = _verify("SELECT inventada, count(*) AS n GROUP BY inventada", "por municipio")
    assert not r.ok and r.layer_failed == "syntax"


def test_rejects_groupby_incoherente():
    # municipio en SELECT sin agregación pero no está en GROUP BY
    r = _verify("SELECT municipio, count(*) AS n GROUP BY cod_dpto",
                "homicidios por municipio")
    assert not r.ok and r.layer_failed == "syntax"


# ---------- Capa 3: restricciones semánticas ----------

def test_count_question_without_aggregate_fails():
    r = _verify("SELECT municipio", "¿cuántos colegios hay?")
    assert not r.ok and r.layer_failed == "semantic"


def test_ranking_without_orderby_limit_fails():
    r = _verify("SELECT municipio, count(*) AS n GROUP BY municipio",
                "top 5 municipios con más casos")
    assert not r.ok and r.layer_failed == "semantic"


def test_temporal_requires_fecha_column():
    # Agrupa por geo en vez de por la columna fecha → no responde "por año".
    r = _verify("SELECT municipio, count(*) AS n GROUP BY municipio",
                "tendencia de homicidios por año")
    assert not r.ok and r.layer_failed == "semantic"


def test_geo_filter_required_but_missing():
    r = _verify("SELECT count(*) AS n", "¿cuántos colegios en Boyacá?",
                has_geo_filter=True)
    assert not r.ok and r.layer_failed == "semantic"


# ---------- Casos válidos ----------

def test_valid_count():
    r = _verify("SELECT count(*) AS n", "¿cuántos colegios hay?")
    assert r.ok, r.error_message


def test_valid_ranking():
    r = _verify(
        "SELECT municipio, count(*) AS n GROUP BY municipio ORDER BY n DESC LIMIT 5",
        "top 5 municipios con más casos",
    )
    assert r.ok, r.error_message


def test_valid_temporal():
    r = _verify(
        "SELECT anio, count(*) AS n GROUP BY anio ORDER BY anio LIMIT 60",
        "tendencia de homicidios por año",
    )
    assert r.ok, r.error_message


def test_valid_geo_filter():
    r = _verify("SELECT count(*) AS n WHERE cod_dpto = '15'",
                "¿cuántos colegios en Boyacá?", has_geo_filter=True)
    assert r.ok, r.error_message
