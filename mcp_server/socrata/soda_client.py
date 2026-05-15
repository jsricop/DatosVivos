"""Wrapper de la SODA API — consultas SoQL sobre datasets de datos.gov.co."""

from typing import Any

import httpx

from ..settings import settings


class SodaClient:
    """Cliente para la SODA API de Socrata.

    Endpoint: https://{domain}/resource/{dataset_id}.json
    Soporta SoQL (`$select`, `$where`, `$group`, `$order`, `$limit`, `$offset`).
    """

    def __init__(
        self,
        domain: str | None = None,
        app_token: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.domain = domain or settings.socrata_domain
        self.app_token = app_token or settings.socrata_app_token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "DatosVivos/0.1 (+https://github.com/jsricop/DatosVivos)",
        }
        if self.app_token:
            headers["X-App-Token"] = self.app_token
        return headers

    async def query(
        self,
        dataset_id: str,
        soql_query: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Ejecuta una consulta SoQL contra un dataset.

        Si `soql_query` se entrega, se pasa como `$query` (SoQL completo).
        En caso contrario se usan `$limit` y `$offset` para paginación simple.

        Args:
            dataset_id: 4x4 ID del dataset en datos.gov.co.
            soql_query: Consulta SoQL completa (opcional).
            limit: Tope máximo de filas si no se pasa SoQL completo.
            offset: Desplazamiento para paginación.

        Returns:
            Lista de registros como diccionarios.
        """
        url = f"https://{self.domain}/resource/{dataset_id}.json"
        if soql_query:
            params: dict[str, Any] = {"$query": soql_query}
        else:
            params = {"$limit": limit, "$offset": offset}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params, headers=self._headers())
            response.raise_for_status()
            return response.json()
