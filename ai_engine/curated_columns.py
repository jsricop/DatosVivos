"""Carga de columnas curadas por dataset para el path generativo (ADR-022, Fase 1).

El camino generativo (`Analyzer`) históricamente armaba el esquema solo desde la
Metadata API de Socrata, sin los `semantic_type` curados que viven en
`dataset_columns_curated`. El verificador semántico de 3 capas (ADR-022 §1.3)
necesita esos tipos para comprobar que el SoQL generado cumple la intención
("por X" → GROUP BY sobre una columna `dimension/geo`, etc.).

Este módulo unifica la lectura:
  1. Lee `dataset_columns_curated` de Postgres (fuente de verdad, igual que chips).
  2. Si el dataset no está curado, clasifica al vuelo desde las columnas de la
     Metadata API con `column_classifier.classify_column` (menor confianza).

El shape de salida es el mismo `list[dict]` que consume `soql_templates.build_soql`
(claves `col_name`, `semantic_type`, `semantic_subtype`, `socrata_data_type`), más
`confidence` y `source` para trazabilidad / decisiones del refusal.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from ai_engine.column_classifier import classify_column

log = logging.getLogger("datosvivos.curated_columns")

# Lazy single connection — mismas lecturas chicas que api/routes/chips.py::_connect,
# pero resiliente: si no hay DB, devolvemos [] y se cae al fallback de metadata.
_conn = None
_conn_disabled = False


def _get_conn():
    global _conn, _conn_disabled
    if _conn_disabled:
        return None
    if _conn is not None and not _conn.closed:
        return _conn
    url = os.environ.get("DATABASE_URL")
    if not url:
        _conn_disabled = True
        return None
    try:
        import psycopg
        from psycopg.rows import dict_row

        _conn = psycopg.connect(url, row_factory=dict_row)
        return _conn
    except Exception as exc:  # noqa: BLE001
        log.warning("curated_columns: sin Postgres (%s) — solo fallback metadata", exc)
        _conn_disabled = True
        return None


def _from_db(dataset_id: str) -> list[dict[str, Any]]:
    conn = _get_conn()
    if conn is None:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT col_name, semantic_type, semantic_subtype,
                       socrata_data_type, confidence
                FROM dataset_columns_curated
                WHERE dataset_id = %s
                ORDER BY
                    CASE confidence WHEN 'high' THEN 0 WHEN 'medium' THEN 1
                                    WHEN 'low' THEN 2 ELSE 3 END,
                    col_name
                """,
                (dataset_id,),
            )
            rows = cur.fetchall()
    except Exception as exc:  # noqa: BLE001
        # Una transacción puede quedar abortada; resetear para no envenenar la conexión.
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            pass
        log.warning("curated_columns: query falló para %s (%s)", dataset_id, exc)
        return []
    for r in rows:
        r["source"] = "curated"
    return list(rows)


def _metadata_field(col: dict[str, Any]) -> tuple[str, str | None, str | None]:
    """Extrae (col_name, data_type, description) de una columna de la Metadata API."""
    col_name = (
        col.get("fieldName")
        or col.get("field_name")
        or col.get("name")
        or ""
    )
    data_type = col.get("dataTypeName") or col.get("dataType") or col.get("renderTypeName")
    description = col.get("description") or col.get("name")
    return col_name, data_type, description


def _from_metadata(metadata_columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Clasifica al vuelo cuando no hay curación (menor confianza)."""
    out: list[dict[str, Any]] = []
    for col in metadata_columns or []:
        col_name, data_type, description = _metadata_field(col)
        if not col_name:
            continue
        cl = classify_column(col_name, data_type, description)
        out.append(
            {
                "col_name": col_name,
                "semantic_type": cl.semantic_type,
                "semantic_subtype": cl.semantic_subtype,
                "socrata_data_type": data_type,
                "confidence": cl.confidence,
                "source": "inferred",
            }
        )
    # Mismo orden que la DB: confidence DESC (high primero).
    _rank = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda c: (_rank.get(c.get("confidence") or "", 3), c["col_name"]))
    return out


def load_curated_columns(
    dataset_id: str,
    metadata_columns: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Devuelve columnas con tipo semántico para `dataset_id`.

    Prefiere `dataset_columns_curated`; si está vacío y se pasan
    `metadata_columns` (de la Metadata API), clasifica al vuelo.

    El resultado es `list[dict]` compatible con `soql_templates.build_soql`
    (`col_name`, `semantic_type`, `semantic_subtype`, `socrata_data_type`) +
    `confidence` y `source` ('curated' | 'inferred').
    """
    curated = _from_db(dataset_id)
    if curated:
        return curated
    return _from_metadata(metadata_columns or [])
