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

import json
import logging
import re
import urllib.parse
import urllib.request
from typing import Any

import duckdb

from ai_engine.column_classifier import classify_column
from ai_engine.csv_cache import get_or_download

log = logging.getLogger(__name__)

# Encodings que intentamos para portales colombianos (utf-8 default,
# luego latin-1 que cubre Bogotá CSVs; utf-16 cubre algunos Valle).
_ENCODING_FALLBACKS = ("utf-8", "latin-1", "utf-16")

# Portales CKAN cuyo `data_url` apunta a la página del recurso (no al
# CSV directo). Para esos hay que resolver via /api/3/action/resource_show.
_CKAN_RESOLVER_HOSTS = ("datos.cali.gov.co",)

# Extensiones no-tabulares — DuckDB no las puede leer como CSV.
_NON_CSV_EXTENSIONS = (".pdf", ".xlsx", ".xls", ".zip", ".rar", ".doc", ".docx")


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


def resolve_data_url(data_url: str) -> str:
    """Si `data_url` apunta a una página CKAN (sin `/download/X.csv`),
    consulta `/api/3/action/resource_show` para obtener la URL real del
    archivo. Si ya es URL directa, la devuelve sin cambios. Si el formato
    no es CSV (PDF/XLS/etc), lanza ValueError.
    """
    if not data_url:
        return data_url
    lower = data_url.lower()
    if any(lower.endswith(ext) for ext in _NON_CSV_EXTENSIONS):
        raise ValueError(f"data_url no es CSV (extensión no soportada): {data_url}")

    parsed = urllib.parse.urlparse(data_url)
    host = parsed.netloc.lower()

    # Si el path ya contiene `/download/` y termina en .csv, asume URL
    # directa al archivo — ningún portal CKAN colombiano la cambia.
    if "/download/" in parsed.path and lower.endswith(".csv"):
        return data_url

    # CKAN page-style URL: /dataset/<x>/resource/<uuid> sin /download/.
    if host in _CKAN_RESOLVER_HOSTS or (
        "/resource/" in parsed.path and "/download/" not in parsed.path
    ):
        m = re.search(r"/resource/([a-f0-9-]{32,})", parsed.path)
        if not m:
            return data_url  # último intento: probar tal cual
        res_id = m.group(1)
        api_url = f"https://{host}/api/3/action/resource_show?id={res_id}"
        try:
            with urllib.request.urlopen(api_url, timeout=15) as resp:
                payload = json.load(resp)
        except Exception as exc:
            raise ValueError(
                f"CKAN resource_show falló para {host} id={res_id}: {exc}"
            ) from exc
        result = payload.get("result") or {}
        fmt = (result.get("format") or "").upper()
        url = result.get("url")
        if not url:
            raise ValueError(f"CKAN no devolvió `url` para id={res_id}")
        if fmt and fmt != "CSV":
            raise ValueError(
                f"Recurso CKAN id={res_id} no es CSV (format={fmt!r})"
            )
        return str(url)

    return data_url


def _csv_read_expr(url: str, encoding: str) -> str:
    """SQL `read_csv(...)` con encoding explícito y auto-detección."""
    safe = url.replace("'", "")
    if encoding == "utf-8":
        # read_csv_auto = utf-8 por defecto, más inferencia rápida.
        return f"read_csv_auto('{safe}')"
    return (
        f"read_csv('{safe}', "
        f"encoding='{encoding}', "
        f"AUTO_DETECT=TRUE, "
        f"HEADER=TRUE)"
    )


def _try_with_fallback(url: str, build_sql) -> tuple[Any, str]:
    """Ejecuta `build_sql(read_expr)` probando encodings en cascada.

    Devuelve `(resultado, encoding_usado)`. Lanza la última excepción si
    todos los encodings fallan.
    """
    last_exc: Exception | None = None
    for enc in _ENCODING_FALLBACKS:
        try:
            read_expr = _csv_read_expr(url, enc)
            con = _connection()
            try:
                result = build_sql(con, read_expr)
            finally:
                con.close()
            return result, enc
        except Exception as exc:
            msg = str(exc).lower()
            # Solo retry si es un problema de encoding; otros errores
            # (URL no accesible, columna inválida) no mejoran cambiando enc.
            if "encod" in msg or "unicode" in msg or "byte sequence" in msg:
                last_exc = exc
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("Sin resultado y sin excepción — estado inválido")


def _local_or_url(resolved: str) -> str:
    """Intenta cache disk-backed; si falla la descarga, cae a la URL
    original para que DuckDB la abra via httpfs."""
    try:
        return get_or_download(resolved)
    except Exception as exc:  # noqa: BLE001
        log.info("csv_cache miss para %s: %s — uso URL directa", resolved, exc)
        return resolved


def describe_csv(url: str) -> list[dict[str, Any]]:
    """Schema del CSV + clasificación semántica por columna.

    Acepta URLs CKAN (resuelve via resource_show si hace falta) y CSVs
    no-utf-8 (intenta latin-1 y utf-16 si utf-8 falla). Devuelve la lista
    con el mismo shape que `dataset_columns_curated`. Pre-cachea el CSV
    a disco para que queries siguientes sobre el mismo dataset eviten la
    descarga.
    """
    if not url:
        raise ValueError("URL vacía")
    resolved = resolve_data_url(url)
    local_or_url = _local_or_url(resolved)

    def _run(con, read_expr):
        return con.execute(
            f"DESCRIBE SELECT * FROM {read_expr} LIMIT 0"
        ).fetchall()

    rows, _enc = _try_with_fallback(local_or_url, _run)
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


# ----------------------------------------------------------------------
# Bodega local (farmeo): gemelos de describe/execute sobre Parquet.
# Sin fallback de encoding (Parquet es binario autodescriptivo) y sin red:
# la consulta corre en milisegundos contra /app/data/lake/{id}.parquet.
# ----------------------------------------------------------------------


def _parquet_expr(path: str) -> str:
    return "read_parquet('" + str(path).replace("'", "''") + "')"


def describe_parquet(path: str) -> list[dict[str, Any]]:
    """Schema del Parquet local + clasificación semántica por columna.

    Mismo shape que `describe_csv` / `dataset_columns_curated`.
    """
    if not path:
        raise ValueError("ruta vacía")
    con = _connection()
    try:
        rows = con.execute(
            f"DESCRIBE SELECT * FROM {_parquet_expr(path)} LIMIT 0"
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


def execute_parquet(path: str, sql: str) -> list[dict[str, Any]]:
    """Ejecuta SQL (placeholder `{src}`) contra el Parquet local de la bodega."""
    if not path:
        raise ValueError("ruta vacía")
    con = _connection()
    try:
        res = con.execute(sql.replace("{src}", _parquet_expr(path)))
        cols = [d[0] for d in res.description]
        return [dict(zip(cols, row)) for row in res.fetchall()]
    finally:
        con.close()


def execute_csv(url: str, sql: str) -> list[dict[str, Any]]:
    """Ejecuta SQL contra el CSV en `url` y devuelve filas como dicts.

    `sql` debe usar el placeholder `{src}` para el FROM clause, p.ej.
    `"SELECT count(*) FROM {src}"`. El executor sustituye `{src}` por el
    `read_csv(...)` con el encoding apropiado.

    Para compatibilidad con call sites anteriores: si `sql` no tiene
    `{src}` pero menciona `read_csv_auto('<url>')`, se reusa tal cual y
    no se intenta fallback de encoding.
    """
    if not url:
        raise ValueError("URL vacía")
    resolved = resolve_data_url(url)
    local_or_url = _local_or_url(resolved)

    if "{src}" in sql:
        def _run(con, read_expr):
            res = con.execute(sql.replace("{src}", read_expr))
            cols = [d[0] for d in res.description]
            return [dict(zip(cols, row)) for row in res.fetchall()]
        rows, _enc = _try_with_fallback(local_or_url, _run)
        return rows

    # Modo legacy: SQL ya tiene el FROM embebido. Sin fallback.
    con = _connection()
    try:
        res = con.execute(sql)
        cols = [d[0] for d in res.description]
        return [dict(zip(cols, row)) for row in res.fetchall()]
    finally:
        con.close()
