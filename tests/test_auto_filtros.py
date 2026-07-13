"""Fase 3+4 de filtros (ADR-024): auto-filtro desde la pregunta y recorte
territorial determinista.

La garantía en ambos: el LLM/el código solo ELIGEN entre valores que
existen en el dato — nunca escriben SQL ni inventan valores.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import duckdb
import pytest

from api.routes.chips import _filtro_territorial, _filtros_desde_pregunta

PERFIL = [
    {"col_name": "SECTOR", "kind": "valor", "value": "OFICIAL", "n": 1721},
    {"col_name": "SECTOR", "kind": "valor", "value": "NO OFICIAL", "n": 463},
    {"col_name": "FECHA CORTE", "kind": "anio", "value": "2024", "n": 900},
]


@pytest.mark.asyncio
async def test_auto_filtro_acepta_solo_valores_del_perfil():
    backend = AsyncMock()
    backend.generate.return_value = (
        '{"filtros": [{"col": "SECTOR", "value": "OFICIAL"},'
        ' {"col": "SECTOR", "value": "PRIVADO"},'
        ' {"col": "OTRA", "value": "X"}]}'
    )
    with patch("api.routes.chips.get_backend", return_value=backend):
        out = await _filtros_desde_pregunta("¿Cuántos colegios públicos?", PERFIL)
    assert out == [{"col": "SECTOR", "kind": "valor", "value": "OFICIAL"}]


@pytest.mark.asyncio
async def test_auto_filtro_json_invalido_devuelve_vacio():
    backend = AsyncMock()
    backend.generate.return_value = "no soy json"
    with patch("api.routes.chips.get_backend", return_value=backend):
        assert await _filtros_desde_pregunta("pregunta", PERFIL) == []


@pytest.mark.asyncio
async def test_auto_filtro_sin_perfil_no_llama_al_llm():
    backend = AsyncMock()
    with patch("api.routes.chips.get_backend", return_value=backend):
        assert await _filtros_desde_pregunta("pregunta", []) == []
    backend.generate.assert_not_called()


@pytest.fixture()
def parquet_nacional(tmp_path):
    path = str(tmp_path / "nac.parquet")
    con = duckdb.connect(":memory:")
    con.execute(f"""
        COPY (
          SELECT CASE i % 3 WHEN 0 THEN 'Boyacá'
                            WHEN 1 THEN 'ANTIOQUIA'
                            ELSE 'CUNDINAMARCA' END AS departamento,
                 i AS n
          FROM range(1, 31) t(i)
        ) TO '{path}' (FORMAT PARQUET)
    """)
    con.close()
    return path


LAKE_COLS = [
    {"col_name": "departamento", "semantic_type": "geo",
     "socrata_data_type": "VARCHAR"},
    {"col_name": "n", "semantic_type": "metrica",
     "socrata_data_type": "BIGINT"},
]


def test_filtro_territorial_encuentra_el_valor_tal_cual(parquet_nacional):
    # Código 15 = Boyacá; en el dato está como 'Boyacá' (con tilde y
    # minúsculas) → el filtro usa el valor ALMACENADO, no el canónico.
    f = _filtro_territorial(parquet_nacional, LAKE_COLS, "15")
    assert f == {"col": "departamento", "kind": "valor", "value": "Boyacá"}


def test_filtro_territorial_sin_match_devuelve_none(parquet_nacional):
    # 88 = San Andrés — no está en el dato.
    assert _filtro_territorial(parquet_nacional, LAKE_COLS, "88") is None


def test_filtro_territorial_solo_para_departamentos(parquet_nacional):
    assert _filtro_territorial(parquet_nacional, LAKE_COLS, "nacional") is None
    assert _filtro_territorial(parquet_nacional, LAKE_COLS, None) is None
    assert _filtro_territorial(parquet_nacional, LAKE_COLS, "15759") is None
