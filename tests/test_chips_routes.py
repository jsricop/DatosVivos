"""Tests integración para api/routes/chips.py.

Cubre:
- GET /api/v1/chips devuelve las 4 listas (con DB mockeada)
- POST /api/v1/query/chips arma el WHERE correctamente para cada combinación
- Manejo de subset grande (sin tipo → suggested_chips + message)
- territorio "nacional" no filtra
- macroregiones expanden a lista de códigos
- refinador hace ILIKE en name+description

Como api/routes/chips.py usa psycopg.connect (no async), mockeamos a nivel
de _connect() para evitar levantar Postgres en tests unitarios.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("psycopg")

from fastapi.testclient import TestClient  # noqa: E402


def _mock_conn_with_responses(*responses):
    """Construye un mock connection que devuelve `responses` en orden por
    cada execute. Cada response es un list[dict] o un dict (para fetchone)."""
    cursors = []
    iterator = iter(responses)

    def _make_cursor(*args, **kwargs):
        cur = MagicMock()
        r = next(iterator)
        if isinstance(r, dict):
            cur.fetchone.return_value = r
            cur.fetchall.return_value = [r]
        elif isinstance(r, list):
            cur.fetchall.return_value = r
            cur.fetchone.return_value = r[0] if r else None
        else:
            cur.fetchone.return_value = r
            cur.fetchall.return_value = [r] if r is not None else []
        cursors.append(cur)
        return cur

    conn = MagicMock()
    conn.cursor.return_value.__enter__.side_effect = _make_cursor
    conn.cursor.return_value.__exit__.return_value = False
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False
    return conn, cursors


def _get_app():
    from api.main import app

    return app


# ---------- GET /chips ----------


def test_get_chips_devuelve_4_listas():
    """GET /chips arma TEMA + TIPO + TERRITORIO + ENTIDAD."""
    temas = [{"category": "Salud y Protección Social", "c": 746},
             {"category": "Educación", "c": 1015}]
    entidades = [{"entity_id": 1, "entity_name": "Ministerio de Salud", "c": 120},
                 {"entity_id": 2, "entity_name": "DANE", "c": 80}]
    conn, _ = _mock_conn_with_responses(temas, entidades)
    with patch("api.routes.chips._connect", return_value=conn):
        client = TestClient(_get_app())
        res = client.get("/api/v1/chips")
        assert res.status_code == 200
        data = res.json()
        assert {"tema", "tipo", "territorio", "entidad"} <= set(data.keys())
        # TIPO siempre 5 hardcoded
        assert len(data["tipo"]) == 5
        tipo_labels = {o["label"] for o in data["tipo"]}
        assert {"Cuántos", "Comparar", "Ranking", "Tendencia", "Mapa"} == tipo_labels
        # TEMA vino de la query mockeada
        assert data["tema"][0]["label"] == "Salud y Protección Social"
        # TERRITORIO incluye Nacional + macro + dptos (≥33)
        assert len(data["territorio"]) >= 33
        # ENTIDAD vino mockeada
        assert data["entidad"][0]["label"] == "Ministerio de Salud"


# ---------- POST /query/chips ----------


def test_query_chips_requiere_al_menos_un_chip():
    """POST con todos null devuelve 400."""
    client = TestClient(_get_app())
    res = client.post("/api/v1/query/chips", json={})
    assert res.status_code == 400


def test_query_chips_subset_grande_sin_tipo_no_elige():
    """Si solo marcaron tema y hay >10 candidatos, no se elige dataset y se
    sugiere refinar."""
    count_row = {"c": 50}  # >10
    candidates = [
        {"dataset_id": f"abcd-{i:04d}", "name": f"Dataset {i}",
         "entity_raw": "MinSalud", "category": "Salud y Protección Social",
         "row_count": 100, "view_count": 1000, "last_updated": None,
         "url": None, "api_url": None,
         "jurisdiccion_nivel": "nacional", "jurisdiccion_geo_codes": []}
        for i in range(10)
    ]
    conn, _ = _mock_conn_with_responses(count_row, candidates)
    with patch("api.routes.chips._connect", return_value=conn):
        client = TestClient(_get_app())
        res = client.post(
            "/api/v1/query/chips",
            json={"tema": "Salud y Protección Social"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total_in_subset"] == 50
        assert data["chosen_dataset_id"] is None
        assert data["suggested_chips"] is not None
        assert "marcá" in (data["message"] or "").lower()


def test_query_chips_con_tipo_marca_chosen():
    """Si el usuario marca TIPO, ejecutamos sobre top-1 aunque subset sea grande."""
    count_row = {"c": 100}
    candidates = [
        {"dataset_id": "top1-id1", "name": "Top 1",
         "entity_raw": "MinSalud", "category": "Salud y Protección Social",
         "row_count": 1000, "view_count": 50000, "last_updated": None,
         "url": None, "api_url": None,
         "jurisdiccion_nivel": "nacional", "jurisdiccion_geo_codes": []}
    ]
    conn, _ = _mock_conn_with_responses(count_row, candidates)
    with patch("api.routes.chips._connect", return_value=conn):
        client = TestClient(_get_app())
        res = client.post(
            "/api/v1/query/chips",
            json={"tema": "Salud y Protección Social", "tipo": "Cuántos"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["chosen_dataset_id"] == "top1-id1"


def test_query_chips_subset_vacio():
    """0 datasets matchean → mensaje útil."""
    count_row = {"c": 0}
    conn, _ = _mock_conn_with_responses(count_row, [])
    with patch("api.routes.chips._connect", return_value=conn):
        client = TestClient(_get_app())
        res = client.post(
            "/api/v1/query/chips",
            json={"tema": "Salud", "territorio": "94", "entidad": "999"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total_in_subset"] == 0
        assert data["chosen_dataset_id"] is None
        assert "ningún dataset" in (data["message"] or "").lower()


def test_query_chips_force_dataset_id_se_respeta():
    """force_dataset_id override la elección automática."""
    count_row = {"c": 5}
    candidates = [
        {"dataset_id": "auto-pick", "name": "Auto",
         "entity_raw": "X", "category": "Y",
         "row_count": 100, "view_count": 1000, "last_updated": None,
         "url": None, "api_url": None,
         "jurisdiccion_nivel": "nacional", "jurisdiccion_geo_codes": []}
    ]
    conn, _ = _mock_conn_with_responses(count_row, candidates)
    with patch("api.routes.chips._connect", return_value=conn):
        client = TestClient(_get_app())
        res = client.post(
            "/api/v1/query/chips",
            json={"tema": "Educación", "force_dataset_id": "user-chose"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["chosen_dataset_id"] == "user-chose"


# ---------- territorios ----------


def test_territory_nacional_no_filtra():
    """`territorio = "nacional"` NO debe agregar filtro geo al WHERE."""
    from api.routes.chips import _territory_codes
    assert _territory_codes("nacional") is None


def test_territory_macroregion_caribe_expande():
    """`macro:caribe` debe expandir a 8 códigos de dpto del Caribe."""
    from api.routes.chips import _territory_codes
    codes = _territory_codes("macro:caribe")
    assert codes is not None
    # Atlántico, Bolívar, Cesar, Córdoba, La Guajira, Magdalena, Sucre, San Andrés
    assert set(codes) == {"08", "13", "20", "23", "44", "47", "70", "88"}


def test_territory_codigo_directo():
    """Un código simple (ej. '11' = Bogotá) se pasa tal cual."""
    from api.routes.chips import _territory_codes
    assert _territory_codes("11") == ["11"]
    assert _territory_codes("05001") == ["05001"]


# ---------- A.1: GET /chips/refine + POST con subtags ----------


def test_refine_sin_chips_devuelve_vacio():
    """Sin parámetros, no podemos calcular un subset → 0 + lista vacía."""
    client = TestClient(_get_app())
    res = client.get("/api/v1/chips/refine")
    assert res.status_code == 200
    data = res.json()
    assert data["subset_total"] == 0
    assert data["subtags"] == []


def test_refine_subset_grande_devuelve_vacio():
    """Si subset >500, tags son ruido del catálogo. Retornar vacío."""
    conn, _ = _mock_conn_with_responses({"c": 800})
    with patch("api.routes.chips._connect", return_value=conn):
        client = TestClient(_get_app())
        res = client.get("/api/v1/chips/refine?tema=Educación")
        assert res.status_code == 200
        data = res.json()
        assert data["subset_total"] == 800
        assert data["subtags"] == []


def test_refine_devuelve_tags_top():
    """Subset razonable → lista de tags ordenada DESC por count."""
    count_row = {"c": 56}
    tags_rows = [
        {"tag": "educación superior", "c": 10},
        {"tag": "universidad del cauca", "c": 8},
        {"tag": "matrícula", "c": 5},
    ]
    conn, _ = _mock_conn_with_responses(count_row, tags_rows)
    with patch("api.routes.chips._connect", return_value=conn):
        client = TestClient(_get_app())
        res = client.get("/api/v1/chips/refine?tema=Educación&territorio=macro:pacifico")
        assert res.status_code == 200
        data = res.json()
        assert data["subset_total"] == 56
        assert len(data["subtags"]) == 3
        assert data["subtags"][0]["value"] == "educación superior"
        assert data["subtags"][0]["count"] == 10


def test_query_chips_con_subtags_intersection():
    """POST /query/chips con subtags=['a','b'] aplica intersection."""
    count_row = {"c": 3}
    candidates = [
        {"dataset_id": "abc-1", "name": "Filtered",
         "entity_raw": "X", "category": "Y",
         "row_count": 100, "view_count": 500, "last_updated": None,
         "url": None, "api_url": None,
         "jurisdiccion_nivel": "departamental", "jurisdiccion_geo_codes": ["19"]}
    ]
    conn, cursors = _mock_conn_with_responses(count_row, candidates)
    with patch("api.routes.chips._connect", return_value=conn):
        client = TestClient(_get_app())
        res = client.post(
            "/api/v1/query/chips",
            json={"tema": "Educación", "subtags": ["matrícula", "cobertura"]},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total_in_subset"] == 3
        # Verificar que el SQL incluye 2 EXISTS clauses para los 2 subtags
        executed_sql = " ".join(
            str(call.args[0]) for call in cursors[0].execute.call_args_list
        )
        assert executed_sql.count("EXISTS (SELECT 1 FROM dataset_tags") == 2


def test_query_chips_solo_subtag_es_chip_valido():
    """Con SOLO subtag (sin tema/territorio/etc.) NO debe rechazar como 'sin chips'."""
    count_row = {"c": 1}
    candidates = [
        {"dataset_id": "abc-1", "name": "X",
         "entity_raw": "E", "category": "C",
         "row_count": 1, "view_count": 1, "last_updated": None,
         "url": None, "api_url": None,
         "jurisdiccion_nivel": None, "jurisdiccion_geo_codes": None}
    ]
    conn, _ = _mock_conn_with_responses(count_row, candidates)
    with patch("api.routes.chips._connect", return_value=conn):
        client = TestClient(_get_app())
        res = client.post(
            "/api/v1/query/chips",
            json={"subtags": ["matrícula"]},
        )
        assert res.status_code == 200


def test_build_chips_where_subtags_genera_exists():
    """El helper genera EXISTS clauses por cada subtag."""
    from api.routes.chips import _build_chips_where
    sql, params = _build_chips_where(
        tema="Educación",
        entidad=None,
        territorio=None,
        subtags=["matrícula", "cobertura"],
    )
    assert sql.count("EXISTS") == 2
    assert "dataset_tags" in sql
    assert "matrícula" in params
    assert "cobertura" in params


def test_build_chips_where_sin_filtros_devuelve_true():
    from api.routes.chips import _build_chips_where
    sql, params = _build_chips_where(None, None, None)
    assert sql == "TRUE"
    assert params == []


# ---------- A.2: score compuesto del ELEGIDO ----------


def test_query_chips_devuelve_score_por_candidate():
    """Cada candidato lleva su score numérico (>=0 y <=1)."""
    count_row = {"c": 5}
    candidates = [
        {"dataset_id": "abc-1", "name": "Top",
         "entity_raw": "X", "category": "Y",
         "row_count": 100, "view_count": 50000, "last_updated": None,
         "url": None, "api_url": None,
         "jurisdiccion_nivel": "nacional", "jurisdiccion_geo_codes": [],
         "score": 0.87},
        {"dataset_id": "abc-2", "name": "Bottom",
         "entity_raw": "X", "category": "Y",
         "row_count": 100, "view_count": 100, "last_updated": None,
         "url": None, "api_url": None,
         "jurisdiccion_nivel": "nacional", "jurisdiccion_geo_codes": [],
         "score": 0.21},
    ]
    conn, _ = _mock_conn_with_responses(count_row, candidates)
    with patch("api.routes.chips._connect", return_value=conn):
        client = TestClient(_get_app())
        res = client.post("/api/v1/query/chips", json={"tema": "Educación"})
        assert res.status_code == 200
        data = res.json()
        assert data["candidates"][0]["score"] == 0.87
        assert data["candidates"][1]["score"] == 0.21


def test_query_chips_score_null_si_no_calculable():
    """Si SQL devuelve NULL en score (subset sin view_count), exponer None."""
    count_row = {"c": 1}
    candidates = [
        {"dataset_id": "abc-1", "name": "X",
         "entity_raw": "Y", "category": "Z",
         "row_count": 0, "view_count": None, "last_updated": None,
         "url": None, "api_url": None,
         "jurisdiccion_nivel": None, "jurisdiccion_geo_codes": None,
         "score": None},
    ]
    conn, _ = _mock_conn_with_responses(count_row, candidates)
    with patch("api.routes.chips._connect", return_value=conn):
        client = TestClient(_get_app())
        res = client.post("/api/v1/query/chips", json={"tema": "X"})
        assert res.json()["candidates"][0]["score"] is None


def test_score_constants_sum_to_one():
    """Los pesos del score deben sumar 1.0 para que score ∈ [0, 1]."""
    from api.routes.chips import _SCORE_W_VIEW, _SCORE_W_FRESHNESS
    assert abs(_SCORE_W_VIEW + _SCORE_W_FRESHNESS - 1.0) < 1e-9
