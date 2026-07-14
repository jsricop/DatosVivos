"""Tests para GET /api/v1/stats/panorama (ADR-023).

Cubre:
- shape de la respuesta (totales, semáforo, acceso, sector, departamento)
- suma del semáforo == total
- códigos de departamento siempre dentro de _DEPT_NAMES (los desconocidos se descartan)
- caché TTL: dentro del TTL no recomputa; vencido el TTL sí

Como stats.py usa psycopg.connect síncrono, mockeamos a nivel de _connect()
(mismo enfoque que test_chips_routes.py) para no levantar Postgres.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("psycopg")

from fastapi.testclient import TestClient  # noqa: E402


# Secuencia real de _compute_panorama sobre UN cursor:
#   execute(totales)     → fetchone
#   execute(sector)      → fetchall
#   execute(dpto)        → fetchall
#   execute(sin_geo)     → fetchone
#   execute(portal)      → fetchall
#   execute(last_etl)    → fetchone
#   execute(crecimiento) → fetchall
_TOTALS = {
    "total": 100,
    "n_entidades": 40,
    "verde": 20,
    "amarillo": 30,
    "rojo": 45,
    "desconocido": 5,
    "directo": 60,
    "requiere_herramienta": 25,
    "solo_metadatos": 15,
    "administrativos": 12,
}
_SECTORES = [
    {"sector": "Salud", "n_datasets": 30, "n_entidades": 12},
    {"sector": "Educación", "n_datasets": 25, "n_entidades": 9},
]
_DPTOS = [
    {"codigo": "11", "n_datasets": 40},
    {"codigo": "05", "n_datasets": 22},
    {"codigo": "ZZ", "n_datasets": 3},  # código basura → debe descartarse
]
_SIN_GEO = {"n": 35}
_PORTALES = [
    {"portal": "datos.gov.co", "n_datasets": 80},
    {"portal": "datosabiertos.bogota.gov.co", "n_datasets": 20},
]
_LAST_ETL = {"t": datetime(2026, 7, 12, 5, 15, 9, tzinfo=timezone.utc)}
_INTERACCION = {"descargas_totales": 10761102, "vistas_mes": 3256601,
                "con_comentarios": 68}
_CRECIMIENTO = [
    {"anio": 2015, "n": 10},
    {"anio": 2020, "n": 30},
    {"anio": 2026, "n": 60},
]


def _mock_conn():
    cur = MagicMock()
    cur.fetchone.side_effect = [_TOTALS, _SIN_GEO, _LAST_ETL, _INTERACCION]
    cur.fetchall.side_effect = [_SECTORES, _DPTOS, _PORTALES, _CRECIMIENTO]
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    conn.cursor.return_value.__exit__.return_value = False
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False
    return conn, cur


def _client():
    from api.main import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_cache():
    """Cada test parte sin caché para no heredar estado entre tests."""
    from api.routes import stats

    stats._panorama_cache = None
    yield
    stats._panorama_cache = None


def test_panorama_shape_y_semantica():
    conn, _ = _mock_conn()
    with patch("api.routes.stats._connect", return_value=conn):
        resp = _client().get("/api/v1/stats/panorama")

    assert resp.status_code == 200
    body = resp.json()

    assert body["total"] == 100
    assert body["n_entidades"] == 40

    # Composición: temáticos + administrativos == total.
    assert body["composicion"] == {"tematicos": 88, "administrativos": 12}
    assert sum(body["composicion"].values()) == body["total"]

    # Semáforo completo y consistente: suma == total.
    assert set(body["semaforo"]) == {"verde", "amarillo", "rojo", "desconocido"}
    assert sum(body["semaforo"].values()) == body["total"]

    assert set(body["acceso"]) == {"directo", "requiere_herramienta", "solo_metadatos"}
    assert sum(body["acceso"].values()) == body["total"]

    assert body["por_sector"][0] == {
        "sector": "Salud",
        "n_datasets": 30,
        "n_entidades": 12,
    }
    assert body["por_portal"][0] == {"portal": "datos.gov.co", "n_datasets": 80}
    assert sum(p["n_datasets"] for p in body["por_portal"]) == body["total"]
    assert body["nacional_sin_geo"] == 35
    assert body["generated_at"]  # ISO no vacío

    # last_etl_at = cierre real del ETL (lo que muestra la home), no el caché.
    assert body["last_etl_at"].startswith("2026-07-12T05:15:09")

    # Línea de tiempo: acumulado creciente que termina en la suma total.
    assert body["crecimiento"] == [
        {"anio": 2015, "acumulado": 10},
        {"anio": 2020, "acumulado": 40},
        {"anio": 2026, "acumulado": 100},
    ]


def test_panorama_departamentos_solo_codigos_canonicos():
    from api.routes.divipola import _DEPT_NAMES

    conn, _ = _mock_conn()
    with patch("api.routes.stats._connect", return_value=conn):
        body = _client().get("/api/v1/stats/panorama").json()

    codigos = [d["codigo"] for d in body["por_departamento"]]
    assert "ZZ" not in codigos  # basura descartada
    assert codigos == ["11", "05"]
    for d in body["por_departamento"]:
        assert d["codigo"] in _DEPT_NAMES
        assert d["nombre"] == _DEPT_NAMES[d["codigo"]]


def test_panorama_cache_ttl(monkeypatch):
    from api.routes import stats

    conn, _ = _mock_conn()
    client = _client()

    fake_now = [1000.0]
    monkeypatch.setattr(stats.time, "monotonic", lambda: fake_now[0])

    with patch("api.routes.stats._connect", return_value=conn) as mocked:
        assert client.get("/api/v1/stats/panorama").status_code == 200
        assert mocked.call_count == 1

        # Dentro del TTL: sirve del caché, no reconecta.
        fake_now[0] += stats._PANORAMA_TTL - 1
        assert client.get("/api/v1/stats/panorama").status_code == 200
        assert mocked.call_count == 1

        # TTL vencido: recomputa (nueva conexión con datos frescos).
        conn2, _ = _mock_conn()
        mocked.return_value = conn2
        fake_now[0] += 2
        assert client.get("/api/v1/stats/panorama").status_code == 200
        assert mocked.call_count == 2
