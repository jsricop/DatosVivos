"""Tool MCP: get_metadata — obtiene esquema completo de un dataset vía Metadata API."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..socrata.metadata_client import MetadataClient
from ._errors import call_socrata


def _shape_column(col: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": col.get("name"),
        "field_name": col.get("fieldName"),
        "type": col.get("dataTypeName"),
        "description": (col.get("description") or "").strip(),
    }


def _shape(meta: dict[str, Any]) -> dict[str, Any]:
    """Aplana la respuesta de Metadata API a la forma documentada en MAIN.md §8.2."""
    columns = [_shape_column(c) for c in (meta.get("columns") or [])]
    tags = meta.get("tags") or []
    return {
        "id": meta.get("id"),
        "name": meta.get("name"),
        "description": (meta.get("description") or "").strip(),
        "entity": meta.get("attribution"),
        "category": meta.get("category"),
        "tags": tags,
        "columns": columns,
        "rows_count": meta.get("rowsUpdatedAt") and meta.get("viewCount"),
        "created_at": meta.get("createdAt"),
        "updated_at": meta.get("rowsUpdatedAt"),
    }


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_metadata(dataset_id: str) -> dict[str, Any]:
        """Obtiene el esquema completo de un dataset de datos.gov.co.

        Args:
            dataset_id: 4x4 ID del dataset (ej: 'gdxc-w37w').

        Returns:
            Diccionario con id, name, description, entity, category, tags,
            columns (lista con name, field_name, type, description),
            rows_count, created_at, updated_at.
        """
        client = MetadataClient()
        meta = await call_socrata(
            client.get(dataset_id),
            context=f"get_metadata({dataset_id!r})",
        )
        return _shape(meta)
