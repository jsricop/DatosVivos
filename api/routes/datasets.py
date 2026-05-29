"""Endpoints de datasets individuales.

- `GET /api/v1/datasets/{id}` — metadata cruda desde la Metadata API de Socrata.
- `GET /api/v1/datasets/{id}/columns` — columnas tipadas desde
  `dataset_columns_curated` (curación interna para el motor SoQL de Fase B).
"""

from __future__ import annotations

import logging
import os
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException
from psycopg.rows import dict_row

from api.models.schemas import (
    CuratedColumn,
    DatasetColumn,
    DatasetCuratedColumns,
    DatasetMetadata,
)
from mcp_server.socrata.metadata_client import MetadataClient

router = APIRouter()
log = logging.getLogger(__name__)

_DATASET_PAGE = "https://www.datos.gov.co/d/{id}"
_DATASET_API = "https://www.datos.gov.co/resource/{id}.json"

_metadata_client = MetadataClient()

# Orden de preferencia al armar `by_type`. Más confianza primero.
_CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}


def _connect() -> psycopg.Connection:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="DATABASE_URL no configurada")
    return psycopg.connect(url, row_factory=dict_row)


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


@router.get(
    "/datasets/{dataset_id}/columns", response_model=DatasetCuratedColumns
)
async def dataset_curated_columns(dataset_id: str) -> DatasetCuratedColumns:
    """Devuelve las columnas curadas del dataset (`semantic_type` listo para
    el constructor SoQL de Fase B). 404 si el dataset no tiene curación."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT col_name, socrata_data_type, socrata_description,
                       semantic_type, semantic_subtype, confidence
                FROM dataset_columns_curated
                WHERE dataset_id = %s
                ORDER BY
                    CASE confidence
                        WHEN 'high' THEN 0
                        WHEN 'medium' THEN 1
                        WHEN 'low' THEN 2
                        ELSE 3
                    END,
                    col_name
                """,
                (dataset_id,),
            )
            rows = cur.fetchall()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset {dataset_id!r} no tiene columnas curadas",
        )
    columns = [CuratedColumn(**row) for row in rows]
    by_type: dict[str, list[str]] = {}
    for col in columns:
        by_type.setdefault(col.semantic_type, []).append(col.col_name)
    return DatasetCuratedColumns(
        dataset_id=dataset_id, columns=columns, by_type=by_type
    )
