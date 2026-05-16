"""Tool MCP: search_datasets — busca datasets por keyword vía Discovery API.

Aplica el flujo de búsqueda con fallback en 3 tiers (ADR-007):
1. expand_query: si la query menciona acrónimos/nombres de entidades, expande
   al canónico antes de pegarle a Socrata (ya integrado en DiscoveryClient.search).
2. topic keywords iterativo: si Tier 1 no aportó y Socrata devuelve [], se
   intentan grupos de 2 entidades temáticamente relacionadas hasta encontrar
   resultados o agotar opciones. Aplicado aquí vía `expand_with_topics_iterative`.

Tier 3 (LLM reformulación) vive en `Analyzer.analyze()` cuando aplica.
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..socrata.discovery_client import DiscoveryClient
from ..socrata.topic_keywords import expand_with_topics_iterative
from ._errors import call_socrata


def _shape(result: dict[str, Any]) -> dict[str, Any]:
    """Aplana el objeto Discovery a la forma documentada en MAIN.md §8.1."""
    resource = result.get("resource", {}) or {}
    classification = result.get("classification", {}) or {}
    columns = resource.get("columns_name") or []
    return {
        "id": resource.get("id"),
        "name": resource.get("name"),
        "description": (resource.get("description") or "").strip(),
        "entity": resource.get("attribution"),
        "updated_at": resource.get("updatedAt"),
        "columns_count": len(columns),
        "rows_count": resource.get("page_views", {}).get("page_views_total"),
        "category": classification.get("domain_category"),
        "permalink": result.get("permalink"),
    }


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def search_datasets(query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Busca datasets en datos.gov.co por palabras clave.

        Args:
            query: Términos de búsqueda en español o inglés.
            limit: Máximo de resultados (default 10, recomendado <= 25).

        Returns:
            Lista de datasets con id, name, description, entity, updated_at,
            columns_count, rows_count, category y permalink.
        """
        client = DiscoveryClient()
        # Tier 1+2: precise acronym expansion (en DiscoveryClient.search)
        # + iterative topic keyword fallback si Socrata retorna [].
        results = await call_socrata(
            expand_with_topics_iterative(client=client, query=query, limit=limit),
            context=f"search_datasets(query={query!r})",
        )
        return [_shape(r) for r in results]
