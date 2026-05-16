"""Wrapper de la Discovery API — búsqueda en el catálogo global de Socrata."""

from typing import Any

import httpx

from ..settings import settings


class DiscoveryClient:
    """Cliente para la Discovery API de Socrata.

    Endpoint: https://api.us.socrata.com/api/catalog/v1
    Permite buscar datasets por keyword en todo el catálogo de un dominio.
    """

    def __init__(
        self,
        base_url: str | None = None,
        domain: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url or settings.discovery_api_url
        self.domain = domain or settings.socrata_domain
        self.timeout = timeout

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Busca datasets por palabras clave en el catálogo del dominio configurado.

        Args:
            query: Término de búsqueda (español o inglés).
            limit: Máximo de resultados.

        Returns:
            Lista de objetos `result` con `resource`, `classification`, `metadata`.
        """
        params: dict[str, Any] = {
            "domains": self.domain,
            "q": query,
            "limit": limit,
            "only": "dataset",
        }
        headers = {"User-Agent": "DatosVivos/0.1 (+https://github.com/jsricop/DatosVivos)"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.base_url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
