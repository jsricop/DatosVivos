"""GET /api/v1/datasets/{id} — metadata estructurada de un dataset.

Consume directamente la Metadata API de Socrata vía
`mcp_server.socrata.metadata_client.MetadataClient`.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from api.models.schemas import DatasetColumn, DatasetMetadata
from mcp_server.socrata.metadata_client import MetadataClient

router = APIRouter()
log = logging.getLogger(__name__)

_DATASET_PAGE = "https://www.datos.gov.co/d/{id}"
_DATASET_API = "https://www.datos.gov.co/resource/{id}.json"

_metadata_client = MetadataClient()


@router.get("/datasets/{dataset_id}", response_model=DatasetMetadata)
async def dataset_metadata(dataset_id: str) -> DatasetMetadata:
    try:
        meta: dict[str, Any] = await _metadata_client.get(dataset_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("Metadata API falló para %s: %s", dataset_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not meta or not meta.get("id"):
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id!r} no encontrado")

    columns: list[DatasetColumn] = []
    for col in meta.get("columns") or []:
        if not isinstance(col, dict):
            continue
        field_name = (
            col.get("field_name") or col.get("fieldName") or col.get("name") or ""
        )
        if not field_name:
            continue
        columns.append(
            DatasetColumn(
                field_name=str(field_name),
                name=str(col.get("name") or field_name),
                data_type=str(col.get("data_type") or col.get("dataTypeName") or ""),
                description=col.get("description"),
            )
        )

    return DatasetMetadata(
        id=str(meta["id"]),
        name=str(meta.get("name") or dataset_id),
        entity=meta.get("attribution"),
        description=str(meta.get("description") or ""),
        columns=columns,
        row_count=meta.get("rowsUpdatedAt"),  # placeholder; row_count exacto vive en views API distinta
        last_updated=meta.get("rowsUpdatedAt"),
        url=_DATASET_PAGE.format(id=dataset_id),
        api_url=_DATASET_API.format(id=dataset_id),
    )
