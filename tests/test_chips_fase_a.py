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
# 2. Reintento sin refinador
# ----------------------------------------------------------------------


def _conn_secuencia(*respuestas):
    """Cada elemento = (total, rows) para una llamada a _run (2 cursores)."""
    cursors = []
    it = iter(respuestas)

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def cursor(self):
            cur = MagicMock()
            # El primer cursor de cada _run hace COUNT; el segundo, el top-10.
            if not cursors or cursors[-1][1] is not None:
                total, _ = next(it)
                cur.fetchone.return_value = {"c": total}
                cursors.append([cur, None])
            else:
                # segundo cursor del par
                idx = len([c for c in cursors if c[1] is None]) - 1
                _, rows = respuestas[len(cursors) - 1]
                cur.fetchall.return_value = rows
                cursors[-1][1] = cur
            cm = MagicMock()
            cm.__enter__ = MagicMock(return_value=cur)
            cm.__exit__ = MagicMock(return_value=False)
            return cm

    return FakeConn()


def test_query_chips_reintenta_sin_refinador():
    """Subset vacío CON refinador → reintento sin él → resultados + aviso."""
    client = _client()
    fila = {
        "dataset_id": "ry5e-gwqx", "name": "Instituciones Educativas Sogamoso",
        "entity_raw": "Alcaldía de Sogamoso", "category": "Educación",
        "row_count": 108, "view_count": 500, "last_updated": "2026-01-01",
        "url": None, "api_url": None, "jurisdiccion_nivel": "municipal",
        "jurisdiccion_geo_codes": None, "score": 0.9,
    }

    # secuencia: _run 1 → (0, []); _run 2 (sin refinador) → (43, [fila])
    respuestas = iter([(0, []), (43, [fila])])

    def fake_connect():
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        state = {"pair": None}

        def cursor():
            cur = MagicMock()
            if state["pair"] is None:
                state["pair"] = next(respuestas)
                cur.fetchone.return_value = {"c": state["pair"][0]}
            else:
                cur.fetchall.return_value = state["pair"][1]
                state["pair"] = None
            cm = MagicMock()
            cm.__enter__ = MagicMock(return_value=cur)
            cm.__exit__ = MagicMock(return_value=False)
            return cm

        conn.cursor = cursor
        return conn

    with patch("api.routes.chips._connect", side_effect=fake_connect):
        body = client.post(
            "/api/v1/query/chips",
            json={"tema": "Educación", "territorio": "15", "refinador": "colegios"},
        ).json()

    assert body["total_in_subset"] == 43
    assert body["candidates"][0]["dataset_id"] == "ry5e-gwqx"
    assert "colegios" in (body["message"] or "")  # aviso del refinador ignorado
    assert "no coincidió" in (body["message"] or "")


def test_query_chips_vacio_sin_refinador_no_reintenta():
    """Sin refinador y subset 0 → mensaje de vacío normal, un solo _run."""
    client = _client()
    llamadas = {"n": 0}

    def fake_connect():
        llamadas["n"] += 1
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        state = {"first": True}

        def cursor():
            cur = MagicMock()
            if state["first"]:
                cur.fetchone.return_value = {"c": 0}
                state["first"] = False
            else:
                cur.fetchall.return_value = []
            cm = MagicMock()
            cm.__enter__ = MagicMock(return_value=cur)
            cm.__exit__ = MagicMock(return_value=False)
            return cm

        conn.cursor = cursor
        return conn

    with patch("api.routes.chips._connect", side_effect=fake_connect):
        body = client.post(
            "/api/v1/query/chips",
            json={"tema": "Educación", "territorio": "99"},
        ).json()

    assert body["total_in_subset"] == 0
    assert llamadas["n"] == 1  # sin reintento
    assert "Ningún dataset coincide" in body["message"]


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
