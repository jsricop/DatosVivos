"""Tools MCP expuestas: search_datasets, get_metadata, query_data, cross_datasets."""
from mcp.server.fastmcp import FastMCP

from . import get_metadata, query_data, search_datasets


def register_all(mcp: FastMCP) -> None:
    """Registra las 3 tools del Sprint 1 en la instancia FastMCP dada."""
    search_datasets.register(mcp)
    get_metadata.register(mcp)
    query_data.register(mcp)
    # cross_datasets se implementa en Sprint 3 (Jun 2-15).
