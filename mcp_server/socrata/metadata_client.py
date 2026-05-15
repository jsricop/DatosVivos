"""Wrapper de la Metadata API — esquema y metadatos por dataset_id."""
from typing import Any

import httpx

from ..settings import settings


class MetadataClient:
    """Cliente para la Metadata API de Socrata.

    Endpoint: https://{domain}/api/views/{dataset_id}.json
    Retorna esquema completo: columnas, tipos, descripción, entidad, tags, rowsCount.
    """

    def __init__(
        self,
        domain: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.domain = domain or settings.socrata_domain
        self.timeout = timeout

    async def get(self, dataset_id: str) -> dict[str, Any]:
        """Obtiene los metadatos completos de un dataset.

        Args:
            dataset_id: 4x4 ID del dataset en datos.gov.co.

        Returns:
            Diccionario con metadatos del dataset (incluye `columns`, `rowsCount`, `attribution`, etc.).
        """
        url = f"https://{self.domain}/api/views/{dataset_id}.json"
        headers = {"User-Agent": "DatosVivos/0.1 (+https://github.com/jsricop/DatosVivos)"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
