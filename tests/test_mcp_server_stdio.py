"""Tests de integración del MCP Server vía transporte stdio.

stdio es el otro transporte soportado por nuestro server. Es el modo típico
cuando un host MCP local (ej. Claude Desktop, Ollama con un wrapper) lanza
el server como proceso hijo y se comunica por stdin/stdout.

Para correr solo estos: `pytest -m integration tests/test_mcp_server_stdio.py -v`.
"""

from __future__ import annotations

import json
import os
import sys

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def _build_params() -> StdioServerParameters:
    """Construye los parámetros para lanzar `mcp_server.server` en modo stdio."""
    env = {
        **os.environ,
        "MCP_TRANSPORT": "stdio",
        "LOG_LEVEL": "WARNING",
        "PYTHONUNBUFFERED": "1",
    }
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        env=env,
    )


@pytest.mark.live
@pytest.mark.integration
async def test_stdio_initialize_and_list_tools():
    """Cliente stdio externo: inicializa sesión, descubre las 3 tools."""
    async with stdio_client(_build_params()) as (read, write):
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
async def test_stdio_call_tool_end_to_end():
    """Cliente stdio externo: llama query_data con SoQL y valida datos reales."""
    async with stdio_client(_build_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            soql = "SELECT cod_dpto, count(*) AS n GROUP BY cod_dpto ORDER BY n DESC LIMIT 1"
            result = await session.call_tool(
                "query_data",
                {"dataset_id": "gdxc-w37w", "soql_query": soql},
            )
            assert not result.isError
            rows = [json.loads(b.text) for b in result.content if getattr(b, "text", None)]
            assert len(rows) == 1
            assert rows[0]["cod_dpto"] == "05"
            assert int(rows[0]["n"]) == 125
