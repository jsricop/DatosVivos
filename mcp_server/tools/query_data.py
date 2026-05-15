"""Tool MCP: query_data — ejecuta consultas SoQL sobre un dataset vía SODA API."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..socrata.soda_client import SodaClient

MAX_LIMIT = 5000


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def query_data(
        dataset_id: str,
        soql_query: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Ejecuta consultas SoQL sobre un dataset de datos.gov.co.

        SoQL soporta `$select`, `$where`, `$group`, `$order`, `$limit`, `$offset`.
        Ejemplo: `SELECT cod_dpto, count(*) AS n GROUP BY cod_dpto ORDER BY n DESC LIMIT 10`

        Args:
            dataset_id: 4x4 ID del dataset (ej: 'gdxc-w37w').
            soql_query: Consulta SoQL completa (opcional). Si se omite, retorna
                las primeras `limit` filas.
            limit: Tope de filas (default 1000, máximo 5000 para evitar respuestas masivas).
            offset: Desplazamiento para paginación cuando no se entrega `soql_query`.

        Returns:
            Lista de registros como diccionarios.
        """
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT
        client = SodaClient()
        return await client.query(
            dataset_id=dataset_id,
            soql_query=soql_query,
            limit=limit,
            offset=offset,
        )
