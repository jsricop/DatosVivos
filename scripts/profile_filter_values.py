#!/usr/bin/env python3
"""Perfil de columnas FILTRABLES de la bodega Parquet (ADR-024, Fase 1).

Para cada dataset descargado en la bodega, precalcula con DuckDB:
  - kind='valor': valores de columnas de texto de BAJA cardinalidad
    (2..30 distintos) — candidatas a chip de filtro ("sector: OFICIAL").
  - kind='anio' : años presentes en columnas fecha — chip de año.

El resultado vive en `dataset_filter_values` (migración 028) y es el
CATÁLOGO de lo filtrable: los endpoints solo aplican filtros cuyos
(col, value) existen aquí. Determinista, sin LLM, sin red — todo sale
del Parquet local.

Modos:
  --bootstrap    perfila TODA la bodega (primera vez; ~10k parquets).
  (default)      incremental: solo snapshots descargados/refrescados
                 después de su último perfil (lo corre el ETL diario).
  --dataset-id   uno solo (debug).
  --limit N      cap de datasets (smoke).

Reanudable: el perfil se escribe por dataset (delete+insert+commit);
relanzar continúa donde iba.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import time
from pathlib import Path

import duckdb
import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

log = logging.getLogger("profile_filter_values")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MAX_CARDINALITY = 30       # más distintos que esto no es un chip, es una lista
MAX_FILTER_COLS = 8        # columnas 'valor' por dataset (las de menor cardinalidad)
MAX_YEARS = 60
MAX_VALUE_LEN = 80

# Mismo criterio que los templates: columnas-identificador no son filtros.
_ID_LIKE_RE = re.compile(
    r"(^|_)(id|ids|codigo|cod|nro|numero|num|consecutivo|registro|radicado)(_|\s|$)"
    r"|identificaci|expediente|correo|email|telefono|tel_fono|direcci|nombre_|_nombre",
    re.IGNORECASE,
)

# Valores-basura: mismos placeholders que sin_basura de los templates.
_JUNK_VALUES = {
    "", "NR", "N/A", "NA", "N.A", "N.A.", "NULL", "SIN DATO",
    "SIN INFORMACION", "SIN INFORMACIÓN", "NO APLICA", "NO REPORTA",
}

_DATE_TYPES = ("DATE", "TIMESTAMP")


def _connect():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL no configurada")
    return psycopg.connect(url, row_factory=dict_row)


def _parquet_expr(path: str) -> str:
    return "read_parquet('" + str(path).replace("'", "''") + "')"


def _ident(col: str) -> str:
    return '"' + col.replace('"', '""') + '"'


def profile_one(path: str) -> list[tuple[str, str, str, int]]:
    """Perfila un Parquet. → [(col_name, kind, value, n), ...]. Puro DuckDB."""
    con = duckdb.connect(":memory:")
    try:
        src = _parquet_expr(path)
        schema = con.execute(f"DESCRIBE SELECT * FROM {src} LIMIT 0").fetchall()
        text_cols = [
            str(c) for c, t, *_ in schema
            if str(t).upper().startswith("VARCHAR") and not _ID_LIKE_RE.search(str(c))
        ]
        date_cols = [
            str(c) for c, t, *_ in schema
            if any(str(t).upper().startswith(d) for d in _DATE_TYPES)
        ]

        out: list[tuple[str, str, str, int]] = []

        # 1) Cardinalidad de TODAS las candidatas en un solo scan.
        filter_cols: list[tuple[str, int]] = []
        if text_cols:
            exprs = ", ".join(
                f"approx_count_distinct({_ident(c)})" for c in text_cols
            )
            cards = con.execute(f"SELECT {exprs} FROM {src}").fetchone()
            filter_cols = sorted(
                [
                    (c, int(card or 0))
                    for c, card in zip(text_cols, cards)
                    if 2 <= int(card or 0) <= MAX_CARDINALITY
                ],
                key=lambda t: t[1],
            )[:MAX_FILTER_COLS]

        # 2) Valores reales de cada columna filtrable.
        for col, _card in filter_cols:
            q = _ident(col)
            rows = con.execute(
                f"SELECT {q} AS v, count(*) AS n FROM {src} "
                f"WHERE {q} IS NOT NULL GROUP BY {q} "
                f"ORDER BY n DESC LIMIT {MAX_CARDINALITY + 5}"
            ).fetchall()
            vals = [
                (col, "valor", str(v), int(n)) for v, n in rows
                if str(v).strip() and len(str(v)) <= MAX_VALUE_LEN
                and str(v).strip().upper() not in _JUNK_VALUES
            ]
            # Una columna con un solo valor útil no filtra nada.
            if len(vals) >= 2:
                out.extend(vals[:MAX_CARDINALITY])

        # 3) Años de columnas fecha nativas.
        for col in date_cols:
            q = _ident(col)
            # GROUP BY posicional: el alias 'y' puede chocar con una columna
            # real llamada 'y' (Binder Error, bootstrap 2026-07-13).
            rows = con.execute(
                f"SELECT EXTRACT(YEAR FROM {q})::INT AS anio_v, count(*) AS n "
                f"FROM {src} WHERE {q} IS NOT NULL "
                f"GROUP BY 1 ORDER BY 1 DESC LIMIT {MAX_YEARS}"
            ).fetchall()
            vals = [
                (col, "anio", str(int(y)), int(n)) for y, n in rows
                if y is not None and 1900 <= int(y) <= 2100
            ]
            if len(vals) >= 2:
                out.extend(vals)

        return out
    finally:
        con.close()


def _pending_sql(mode_bootstrap: bool) -> str:
    """Snapshots a perfilar. Incremental = sin perfil o refrescados después
    del último perfil."""
    base = """
        SELECT s.dataset_id, s.parquet_path
        FROM dataset_snapshots s
        LEFT JOIN (
            SELECT dataset_id, MAX(profiled_at) AS profiled_at
            FROM dataset_filter_values GROUP BY dataset_id
        ) p USING (dataset_id)
        WHERE s.status = 'downloaded' AND s.parquet_path IS NOT NULL
    """
    if not mode_bootstrap:
        base += " AND (p.profiled_at IS NULL OR s.downloaded_at > p.profiled_at)"
    return base + " ORDER BY s.bytes ASC NULLS LAST"


def run(conn, *, bootstrap: bool = False, limit: int | None = None,
        dataset_id: str | None = None, max_minutes: int | None = None) -> int:
    t0 = time.monotonic()
    with conn.cursor() as cur:
        if dataset_id:
            cur.execute(
                "SELECT dataset_id, parquet_path FROM dataset_snapshots "
                "WHERE dataset_id = %s AND status = 'downloaded'", [dataset_id],
            )
        else:
            cur.execute(_pending_sql(bootstrap))
        pending = cur.fetchall()
    if limit:
        pending = pending[:limit]
    log.info("perfil: %d datasets pendientes", len(pending))

    ok = fail = 0
    for snap in pending:
        if max_minutes and time.monotonic() - t0 > max_minutes * 60:
            log.info("tope de tiempo — quedan %d (siguen mañana)",
                     len(pending) - ok - fail)
            break
        ds = snap["dataset_id"]
        try:
            values = profile_one(snap["parquet_path"])
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM dataset_filter_values WHERE dataset_id = %s", [ds]
                )
                if values:
                    cur.executemany(
                        "INSERT INTO dataset_filter_values "
                        "(dataset_id, col_name, kind, value, n) "
                        "VALUES (%s, %s, %s, %s, %s) "
                        "ON CONFLICT (dataset_id, col_name, value) DO UPDATE "
                        "SET n = EXCLUDED.n, profiled_at = now()",
                        [(ds, c, k, v, n) for c, k, v, n in values],
                    )
                else:
                    # Marca de "perfilado sin filtrables" para no re-visitar:
                    # una fila centinela que los endpoints ignoran.
                    cur.execute(
                        "INSERT INTO dataset_filter_values "
                        "(dataset_id, col_name, kind, value, n) "
                        "VALUES (%s, '_sin_filtrables', 'meta', '1', 0) "
                        "ON CONFLICT DO NOTHING",
                        [ds],
                    )
            conn.commit()
            ok += 1
        except Exception as exc:  # noqa: BLE001 — un parquet roto no para el barrido
            conn.rollback()
            fail += 1
            log.warning("perfil %s falló: %s", ds, str(exc)[:160])
        if (ok + fail) % 500 == 0:
            log.info("progreso perfil: %d ok · %d fail", ok, fail)
    log.info("perfil fin: %d ok · %d fail en %.1f min",
             ok, fail, (time.monotonic() - t0) / 60)
    return 0


def run_daily(max_minutes: int = 20) -> None:
    """Gancho del ETL (tras el farmeo): incremental y acotado. Nunca lanza."""
    try:
        with _connect() as conn:
            run(conn, bootstrap=False, max_minutes=max_minutes)
    except Exception:  # noqa: BLE001
        log.exception("perfil diario falló (el ETL continúa)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bootstrap", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dataset-id", default=None)
    ap.add_argument("--max-minutes", type=int, default=None)
    args = ap.parse_args()
    with _connect() as conn:
        return run(conn, bootstrap=args.bootstrap, limit=args.limit,
                   dataset_id=args.dataset_id, max_minutes=args.max_minutes)


if __name__ == "__main__":
    raise SystemExit(main())
