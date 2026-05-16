"""Punto de entrada del MCP Server. Registra las tools y arranca transporte SSE/stdio."""

import logging

from mcp.server.fastmcp import FastMCP

from .settings import settings
from .tools import register_all

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

mcp = FastMCP("datosvivos")
register_all(mcp)


def main() -> None:
    transport = settings.mcp_transport.lower()
    log.info("MCP Server arrancando: transport=%s port=%s", transport, settings.mcp_port)
    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "sse":
        mcp.run(transport="sse")
    else:
        raise ValueError(f"MCP_TRANSPORT inválido: {transport!r}. Use 'sse' o 'stdio'.")


if __name__ == "__main__":
    main()
