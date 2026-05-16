"""Tests de integración del MCP Server vía transporte SSE.

Arrancan el servidor en un subproceso, conectan un cliente SSE externo (el oficial
del SDK MCP), y ejercitan las 3 tools end-to-end. Esto cierra la brecha de los tests
in-process (`mcp.call_tool`) que no probaban el transporte real.

Para correr solo estos: `pytest -m integration tests/test_mcp_server_sse.py -v`.
Para saltarlos: `pytest -m "not integration"`.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator

import pytest
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 38000  # puerto poco usado para evitar conflictos con otro server local
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/sse"


def _wait_for_port(host: str, port: int, timeout: float = 15.0) -> bool:
    """Espera hasta `timeout` segundos a que el puerto acepte conexiones TCP."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False


@pytest.fixture(scope="module")
def mcp_server() -> Iterator[str]:
    """Arranca `mcp_server.server` en un subproceso con transporte SSE y lo tumba al final."""
    env = {
        **os.environ,
        "MCP_TRANSPORT": "sse",
        "MCP_HOST": SERVER_HOST,
        "MCP_PORT": str(SERVER_PORT),
        "LOG_LEVEL": "WARNING",
        # Asegurar que .env del proyecto no sobreescriba MCP_PORT
        "PYTHONUNBUFFERED": "1",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "mcp_server.server"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        if not _wait_for_port(SERVER_HOST, SERVER_PORT, timeout=15.0):
            proc.terminate()
            out, err = proc.communicate(timeout=3)
            pytest.fail(
                "Server no respondió en 15s.\n"
                f"stdout:\n{out.decode(errors='replace')}\n"
                f"stderr:\n{err.decode(errors='replace')}"
            )
        yield SERVER_URL
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def _extract_blocks(call_result) -> list:
    """Devuelve todos los TextContent del CallToolResult parseados como JSON.

    FastMCP serializa una lista[dict] como N bloques TextContent (uno por item).
    Para tools que retornan un solo dict, devuelve una lista de 1 elemento.
    """
    if call_result.isError:
        pytest.fail(f"Tool devolvió error: {call_result.content}")
    return [json.loads(block.text) for block in call_result.content if getattr(block, "text", None)]


@pytest.mark.live
@pytest.mark.integration
async def test_sse_initialize_and_list_tools(mcp_server: str):
    """Cliente SSE externo se conecta, inicializa sesión y descubre las 3 tools."""
    async with sse_client(mcp_server) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            assert init.serverInfo.name == "datosvivos"

            tools_resp = await session.list_tools()
            names = {t.name for t in tools_resp.tools}
            # cross_datasets agregada en Sprint 3 (PR feature/ai-sprint3)
            assert names == {
                "search_datasets",
                "get_metadata",
                "query_data",
                "cross_datasets",
            }, names


@pytest.mark.live
@pytest.mark.integration
async def test_sse_call_search_datasets(mcp_server: str):
    async with sse_client(mcp_server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("search_datasets", {"query": "divipola", "limit": 3})
            items = _extract_blocks(result)
            assert len(items) > 0
            ids = [r["id"] for r in items]
            assert "gdxc-w37w" in ids


@pytest.mark.live
@pytest.mark.integration
async def test_sse_call_get_metadata(mcp_server: str):
    async with sse_client(mcp_server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_metadata", {"dataset_id": "gdxc-w37w"})
            blocks = _extract_blocks(result)
            assert len(blocks) == 1
            meta = blocks[0]
            assert meta["id"] == "gdxc-w37w"
            assert "DIVIPOLA" in (meta.get("name") or "").upper()
            assert len(meta.get("columns") or []) >= 5


@pytest.mark.live
@pytest.mark.integration
async def test_sse_call_query_data_soql(mcp_server: str):
    async with sse_client(mcp_server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            soql = "SELECT cod_dpto, count(*) AS n GROUP BY cod_dpto ORDER BY n DESC LIMIT 3"
            result = await session.call_tool(
                "query_data",
                {"dataset_id": "gdxc-w37w", "soql_query": soql},
            )
            rows = _extract_blocks(result)
            assert len(rows) == 3
            # Antioquia (05) debe seguir siendo el top con 125 municipios
            assert rows[0]["cod_dpto"] == "05"
            assert int(rows[0]["n"]) == 125


# ============================================================
# Coverage gap fills: cross_datasets + search con Tier 2 sobre SSE
# ============================================================


@pytest.mark.live
@pytest.mark.integration
async def test_sse_call_cross_datasets_via_protocol(mcp_server: str):
    """`cross_datasets` debe ser callable via el protocolo MCP SSE real,
    no solo in-process. Cubre gap: hasta ahora cross_datasets se probaba con
    mcp.call_tool directo; este test usa sse_client externo."""
    async with sse_client(mcp_server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "cross_datasets",
                {
                    "dataset_ids": ["gdxc-w37w", "t7kp-7a7c"],
                    "join_keys": "cod_dpto",
                },
            )
            rows = _extract_blocks(result)
            assert rows, "cross_datasets vía SSE devolvió vacío"
            assert "cod_dpto" in rows[0], f"Esperaba columna cod_dpto en primer row: {rows[0]}"


@pytest.mark.live
@pytest.mark.integration
async def test_sse_search_thematic_query_via_topic_fallback(mcp_server: str):
    """Query temática que NO menciona entidad por nombre debe encontrar
    resultados vía Tier 2 (topic keywords iterativo).

    Cubre gap: el flujo Tier 2 estaba testeado in-process (`expand_with_topics_iterative`)
    pero NO via el protocolo MCP SSE. Esta es la verificación end-to-end
    del recall mejorado.
    """
    async with sse_client(mcp_server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # "Información sobre vacunación" no menciona MinSalud/INS por nombre.
            # Tier 1 (acrónimos) no expande. Tier 2 debe encontrar entidades
            # de salud por keyword matching.
            result = await session.call_tool(
                "search_datasets",
                {"query": "información sobre vacunación", "limit": 5},
            )
            items = _extract_blocks(result)
            assert items, "Esperaba resultados vía Tier 2 para query temática"
            assert any("id" in r and "name" in r for r in items)
