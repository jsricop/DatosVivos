"""Tests de las 3 tools del MCP Server contra datos.gov.co real.

Estos tests pegan a Socrata público — requieren internet.
Para saltarlos: `pytest -m "not live"`.

Dataset de referencia: `gdxc-w37w` (DIVIPOLA-Códigos municipios) — 1.122 filas estables.
"""

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from mcp_server.server import mcp

DIVIPOLA_DATASET_ID = "gdxc-w37w"


async def _call(name: str, args: dict):
    """Wrapper que aplana el retorno de mcp.call_tool()."""
    result = await mcp.call_tool(name, args)
    payload = result[1] if isinstance(result, tuple) else result
    if hasattr(payload, "get") and "result" in payload:
        return payload["result"]
    return payload


@pytest.mark.live
async def test_search_datasets_returns_results():
    results = await _call("search_datasets", {"query": "divipola", "limit": 3})
    assert isinstance(results, list)
    assert len(results) > 0
    assert all("id" in r and "name" in r for r in results)
    # Esperamos que DIVIPOLA municipios aparezca en los primeros resultados
    ids = [r.get("id") for r in results]
    assert DIVIPOLA_DATASET_ID in ids


@pytest.mark.live
async def test_search_datasets_respects_limit():
    results = await _call("search_datasets", {"query": "educacion", "limit": 2})
    assert len(results) <= 2


@pytest.mark.live
async def test_get_metadata_returns_schema():
    meta = await _call("get_metadata", {"dataset_id": DIVIPOLA_DATASET_ID})
    assert meta["id"] == DIVIPOLA_DATASET_ID
    assert "DIVIPOLA" in (meta.get("name") or "").upper()
    columns = meta.get("columns") or []
    assert len(columns) >= 5
    # Verifica forma de columna
    col = columns[0]
    assert "name" in col and "type" in col


@pytest.mark.live
async def test_query_data_basic_limit():
    rows = await _call(
        "query_data",
        {"dataset_id": DIVIPOLA_DATASET_ID, "limit": 5},
    )
    assert isinstance(rows, list)
    assert len(rows) == 5
    assert "cod_dpto" in rows[0]
    assert "nom_mpio" in rows[0]


@pytest.mark.live
async def test_query_data_soql_aggregation():
    soql = "SELECT cod_dpto, count(*) AS n " "GROUP BY cod_dpto ORDER BY n DESC LIMIT 5"
    rows = await _call(
        "query_data",
        {"dataset_id": DIVIPOLA_DATASET_ID, "soql_query": soql},
    )
    assert len(rows) == 5
    # Antioquia (05) debe ser el departamento con más municipios (125)
    top = rows[0]
    assert top["cod_dpto"] == "05"
    assert int(top["n"]) == 125


@pytest.mark.live
async def test_query_data_caps_at_max_limit():
    # Pedir más del límite máximo no rompe; el cliente lo capa a MAX_LIMIT
    rows = await _call(
        "query_data",
        {"dataset_id": DIVIPOLA_DATASET_ID, "limit": 50000},
    )
    assert len(rows) <= 5000


# === Error paths — verifican que el LLM consumidor reciba mensajes útiles ===


@pytest.mark.live
async def test_get_metadata_invalid_id_raises_useful_error():
    """Un dataset_id que no existe debe producir ToolError con HTTP 404 + mensaje real."""
    with pytest.raises(ToolError) as exc_info:
        await _call("get_metadata", {"dataset_id": "xxxx-xxxx"})
    msg = str(exc_info.value)
    assert "404" in msg, f"Esperaba '404' en el mensaje, vi: {msg!r}"
    assert (
        "xxxx-xxxx" in msg
    ), "El mensaje debe incluir el dataset_id para que el LLM sepa qué falló"


@pytest.mark.live
async def test_query_data_malformed_soql_raises_useful_error():
    """SoQL inválido debe llegar al LLM con el mensaje de Socrata, no opaco."""
    with pytest.raises(ToolError) as exc_info:
        await _call(
            "query_data",
            {"dataset_id": DIVIPOLA_DATASET_ID, "soql_query": "SELECT WHERE FROM"},
        )
    msg = str(exc_info.value)
    assert "400" in msg
    # El mensaje útil de Socrata debe estar presente — no un genérico "Bad Request"
    assert (
        "SoQL" in msg or "parse" in msg or "Expected" in msg
    ), f"Mensaje no incluye detalle del SoQL: {msg!r}"


@pytest.mark.live
async def test_search_datasets_no_matches_returns_empty_list():
    """Búsqueda sin matches NO es un error — es una lista vacía."""
    results = await _call("search_datasets", {"query": "xxxqfdhg9874ttt_no_match", "limit": 5})
    assert results == []


# Guard `test_cross_datasets_is_not_registered` eliminado en Sprint 3:
# cross_datasets YA está registrada (ver tests/test_sprint3_acceptance.py::
# test_cross_datasets_is_registered_in_mcp_server).
