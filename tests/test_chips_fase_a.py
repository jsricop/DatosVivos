"""Tests de la Fase A del arreglo del buscador NL (2026-07-10).

Cubre los tres arreglos deterministas del lado de chips:
1. Heurística léxica de TIPO en from-nl ("cuántos" siempre gana al LLM;
   las demás señales solo rellenan).
2. Reintento sin refinador cuando el subset queda vacío (el refinador
   inventado por el mapper era un callejón sin salida).
3. Umbral del índice vectorial re-calibrado y configurable por env.

Mismo enfoque de mocks que test_chips_routes.py (sin Postgres real).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("psycopg")

from fastapi.testclient import TestClient  # noqa: E402


def _client():
    from api.main import app

    return TestClient(app)


# ----------------------------------------------------------------------
# 1. Heurística léxica de TIPO
# ----------------------------------------------------------------------


def test_infer_tipo_lexico_casos():
    from api.routes.chips import _infer_tipo_lexico

    assert _infer_tipo_lexico("¿Cuántos colegios hay en Boyacá?") == "Cuántos"
    assert _infer_tipo_lexico("cuantas camas UCI tiene Cali") == "Cuántos"
    assert _infer_tipo_lexico("comparar matrícula entre Bogotá y Cali") == "Comparar"
    assert _infer_tipo_lexico("top 10 municipios con más contratos") == "Ranking"
    assert _infer_tipo_lexico("evolución de homicidios 2018-2024") == "Tendencia"
    assert _infer_tipo_lexico("mapa de vacunación por departamento") == "Mapa"
    assert _infer_tipo_lexico("contratos firmados por la ANI en 2024") is None


async def _fake_list_chips():
    """from-nl carga las listas de chips desde la BD — se mockea vacío."""
    m = MagicMock()
    m.tema, m.territorio, m.entidad = [], [], []
    return m


def _post_from_nl(client, q, mapper):
    with patch("api.routes.chips.list_chips", side_effect=_fake_list_chips), \
         patch("api.routes.chips.map_nl_to_chips", side_effect=mapper):
        res = client.post("/api/v1/chips/from-nl", json={"q": q})
    assert res.status_code == 200, res.text
    return res.json()


def test_from_nl_cuantos_sobreescribe_al_llm():
    """El LLM devolvió tipo=null (caso real medido): la heurística lo rellena.
    Y si el LLM dice 'Ranking' para una pregunta '¿cuántos…?', se corrige."""
    client = _client()

    async def fake_map(q, available):
        return {"tema": "Educación", "tipo": None, "territorio": "15",
                "entidad": None, "refinador": "colegios"}

    body = _post_from_nl(client, "¿Cuántos colegios públicos hay en Boyacá?", fake_map)
    assert body["tipo"] == "Cuántos"

    async def fake_map2(q, available):
        return {"tema": "Educación", "tipo": "Ranking", "territorio": None,
                "entidad": None, "refinador": None}

    body = _post_from_nl(client, "¿cuántas sedes educativas hay?", fake_map2)
    assert body["tipo"] == "Cuántos"  # la señal léxica fuerte gana


def test_from_nl_relleno_no_pisa_al_llm():
    """Señales débiles (p.ej. 'mapa') solo rellenan: si el LLM ya dio un tipo
    y NO hay señal fuerte, se respeta el del LLM."""
    client = _client()

    async def fake_map(q, available):
        return {"tema": None, "tipo": "Tendencia", "territorio": None,
                "entidad": None, "refinador": None}

    # "mapa" (señal débil) NO pisa el "Tendencia" que ya propuso el LLM.
    body = _post_from_nl(client, "dame el mapa de la deserción", fake_map)
    assert body["tipo"] == "Tendencia"


# ----------------------------------------------------------------------
# 2. Refinador como BOOST de ranking (no filtra el subset)
# ----------------------------------------------------------------------


def _fake_connect_capturando(capturas, total=43, rows=None):
    """Mock de _connect que captura los SQL/params ejecutados."""
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    state = {"first": True}

    def cursor():
        cur = MagicMock()

        def execute(sql, params=None):
            capturas.append((sql, params))

        cur.execute = execute
        if state["first"]:
            cur.fetchone.return_value = {"c": total}
            state["first"] = False
        else:
            cur.fetchall.return_value = rows or []
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cur)
        cm.__exit__ = MagicMock(return_value=False)
        return cm

    conn.cursor = cursor
    return conn


def test_query_chips_refinador_no_filtra_y_boostea():
    """El refinador NO entra al WHERE (no vacía subsets) y SÍ entra al score
    como boost ILIKE — el caso 'estudiantes' que contaba un dataset arbitrario."""
    client = _client()
    fila = {
        "dataset_id": "mat-0001", "name": "Estudiantes matriculados Bogotá",
        "entity_raw": "SED", "category": "Educación",
        "row_count": 5000, "view_count": 900, "last_updated": "2026-01-01",
        "url": None, "api_url": None, "jurisdiccion_nivel": "distrito_capital",
        "jurisdiccion_geo_codes": None, "score": 1.2,
    }
    capturas: list = []

    with patch(
        "api.routes.chips._connect",
        side_effect=lambda: _fake_connect_capturando(capturas, total=9, rows=[fila]),
    ):
        body = client.post(
            "/api/v1/query/chips",
            json={"tema": "Educación", "territorio": "11", "refinador": "estudiantes"},
        ).json()

    assert body["total_in_subset"] == 9
    assert body["candidates"][0]["dataset_id"] == "mat-0001"
    # sin aviso de refinador ignorado: ya no se descarta, ordena
    assert "no coincidió" not in (body["message"] or "")

    count_sql, count_params = capturas[0]
    score_sql, score_params = capturas[1]
    # WHERE del conteo: el refinador NO filtra
    assert "refinador" not in count_sql.lower()
    assert "estudiantes" not in str(count_params)
    # score: boost CASE con el refinador como ILIKE
    assert "CASE WHEN" in score_sql and "ILIKE" in score_sql
    assert "%estudiantes%" in score_params


# ----------------------------------------------------------------------
# 3. Umbral del índice vectorial
# ----------------------------------------------------------------------


def test_min_score_default_y_env(monkeypatch):
    import importlib

    import ai_engine.vector_index as vi

    assert vi.DEFAULT_MIN_SCORE == pytest.approx(0.815)

    monkeypatch.setenv("VECTOR_MIN_SCORE", "0.5")
    importlib.reload(vi)
    assert vi.DEFAULT_MIN_SCORE == pytest.approx(0.5)

    monkeypatch.delenv("VECTOR_MIN_SCORE")
    importlib.reload(vi)
    assert vi.DEFAULT_MIN_SCORE == pytest.approx(0.815)
