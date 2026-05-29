"""Executor DuckDB sobre CSVs remotos (Reto F.4).

Habilita la consulta determinista sobre datasets federados (`source_type='federated'`,
`federated_status='ok'`) cuyo `data_url` apunta a un CSV externo (MEDATA y
otros portales que exponen el archivo directo).

Diseño:
- DuckDB en proceso, conexión efímera por consulta (sin estado entre llamadas).
- `httpfs` se instala/carga al inicializar — necesario para `read_csv_auto`
  sobre URLs `http(s)://`.
- `describe_csv(url)` corre `DESCRIBE SELECT * FROM read_csv_auto(url) LIMIT 0`
  para sacar el schema (col_name, data_type) sin descargar filas. Luego corre
  `classify_column` (compartido con el path nativo) para deducir
  `semantic_type` por columna.
- `execute_csv(url, sql)` ejecuta la query y devuelve filas como dicts.
  Las plantillas SQL deben emitir la URL directamente embebida (no parámetro)
  porque `read_csv_auto` requiere literal string en algunas versiones.
  Los identificadores de columna SE VALIDAN antes de embeberse para evitar
  inyección (ver `_safe_ident_dbq`).

Limitaciones (out of scope hoy):
- Sin caché entre llamadas: cada query descarga el CSV. OK para MVP, costoso
  para datasets grandes y queries frecuentes (Reto F.5 hot path).
- Solo URLs `http(s)`. URLs CKAN (page-HTML) requieren resolución previa
  (F.4 fase 2: CKAN resolver).
- Sin protección de tamaño: un CSV de 1 GB lo descargará en memoria. Habría
  que cap por `data_url` size o `LIMIT` rows fetched.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import duckdb

from ai_engine.column_classifier import classify_column

log = logging.getLogger(__name__)


# Identificador SQL DuckDB seguro para embeber (cuando se rodea con dobles
# comillas). Permitimos letras, dígitos, guion bajo, espacio, tilde de
# acento — el resto se rechaza. NO permitimos comillas dobles literales
# (cerrarían el identificador y abrirían inyección).
_SAFE_IDENT_RE = re.compile(r'^[A-Za-zÁÉÍÓÚÑáéíóúñ0-9_ \-\.]+$')


def _safe_ident_dbq(name: str) -> str | None:
    """Devuelve `"name"` listo para SQL DuckDB si el nombre es seguro; None si no."""
    if not name or not _SAFE_IDENT_RE.match(name):
        return None
    return f'"{name}"'


def _connection() -> duckdb.DuckDBPyConnection:
    """Conexión efímera con httpfs cargado."""
    con = duckdb.connect(":memory:")
    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")
    return con


def describe_csv(url: str) -> list[dict[str, Any]]:
    """Schema del CSV + clasificación semántica por columna.

    Returns:
        Lista de dicts con la misma forma que `dataset_columns_curated`:
        `{col_name, socrata_data_type, socrata_description, semantic_type,
        semantic_subtype, confidence}`. Sirve directamente al motor de
        plantillas (`build_soql` lo bucketiza por semantic_type).
    """
    if not url:
        raise ValueError("URL vacía")
    con = _connection()
    try:
        # DESCRIBE en una consulta con LIMIT 0 evita descargar filas.
        rows = con.execute(
            f"DESCRIBE SELECT * FROM read_csv_auto('{url}') LIMIT 0"
        ).fetchall()
    finally:
        con.close()
    out: list[dict[str, Any]] = []
    for row in rows:
        col_name = str(row[0])
        data_type = str(row[1]) if len(row) > 1 else ""
        cls = classify_column(col_name=col_name, data_type=data_type)
        out.append(
            {
                "col_name": col_name,
                "socrata_data_type": data_type,
                "socrata_description": None,
                "semantic_type": cls.semantic_type,
                "semantic_subtype": cls.semantic_subtype,
                "confidence": cls.confidence,
            }
        )
    return out


def execute_csv(url: str, sql: str) -> list[dict[str, Any]]:
    """Ejecuta SQL contra `read_csv_auto(url)` y devuelve filas como dicts.

    Los strings vienen como `str`, números como `int`/`float`. Filas de
    fecha vuelven como `datetime`/`date` — el cliente JSON las renderea
    con `default=str` (FastAPI lo hace automáticamente vía pydantic).
    """
    if not url:
        raise ValueError("URL vacía")
    con = _connection()
    try:
        res = con.execute(sql)
        cols = [d[0] for d in res.description]
        return [dict(zip(cols, row)) for row in res.fetchall()]
    finally:
        con.close()
