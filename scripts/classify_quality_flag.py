#!/usr/bin/env python3
"""Marca `quality_flag` en `datasets` según reglas heurísticas (D.5).

Marcado actual:
- `admin_only`: nombres que matchean patrones de obligaciones Ley 1712
  (esquema de publicación, índice de información clasificada, registro de
  activos de información, ITA).
- `no_rows`: row_count = 0 o NULL.

NO marca `stale` automáticamente — el score A.2 ya lo maneja vía decay de
freshness. Si decidimos ocultarlos por default, agregar acá.

Idempotente: re-corrigible. UPDATE explícito por flag, no NULL → flag
(es decir, los `ok` quedan NULL para minimizar ruido en la tabla).

Uso:
    DATABASE_URL=... python scripts/classify_quality_flag.py
    # o dentro del container:
    docker compose exec -T api python scripts/classify_quality_flag.py
"""

from __future__ import annotations

import os
import sys

import psycopg


# Patrones administrativos. Cualquier match en `name` (ILIKE) marca el dataset.
# Sincronizado con `audit_catalog_quality._ADMIN_PATTERNS`.
_ADMIN_PATTERNS = [
    "esquema de publicación",
    "esquema de publicacion",
    "índice de información clasificada",
    "indice de informacion clasificada",
    "registro de activos de información",
    "registro de activos de informacion",
    "activos de información",
    "activos de informacion",
    "informe de gestión",
    "informe de gestion",
    "tabla de retención documental",
    "tabla de retencion documental",
    "instrumentos archivísticos",
    "instrumentos archivisticos",
]


def mark_admin_only(conn) -> int:
    """UPDATE datasets SET quality_flag='admin_only' donde nombre match.

    Returns el número de filas afectadas.
    """
    # ILIKE OR chain — funciona en Postgres sin extensión.
    or_clause = " OR ".join(["name ILIKE %s"] * len(_ADMIN_PATTERNS))
    params = tuple(f"%{p}%" for p in _ADMIN_PATTERNS)
    sql = f"""
        UPDATE datasets
        SET quality_flag = 'admin_only',
            quality_flag_at = NOW()
        WHERE (quality_flag IS NULL OR quality_flag != 'admin_only')
          AND ({or_clause})
    """
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def mark_no_rows(conn) -> int:
    """Marca datasets con row_count=0/NULL como no_rows, salvo los ya admin_only."""
    sql = """
        UPDATE datasets
        SET quality_flag = 'no_rows',
            quality_flag_at = NOW()
        WHERE quality_flag IS NULL
          AND (row_count IS NULL OR row_count = 0)
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.rowcount


def show_distribution(conn) -> None:
    sql = """
        SELECT COALESCE(quality_flag, 'ok') AS flag, COUNT(*) AS n
        FROM datasets
        GROUP BY flag
        ORDER BY n DESC
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    total = sum(r[1] for r in rows)
    print("Distribución post-clasificación:")
    for flag, n in rows:
        pct = (100 * n / total) if total else 0
        print(f"  {flag:<15} {n:>6,}  ({pct:.1f}%)")
    print(f"  {'TOTAL':<15} {total:>6,}")


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL no definida", file=sys.stderr)
        return 2

    with psycopg.connect(url) as conn:
        n_admin = mark_admin_only(conn)
        print(f"Marcados admin_only: {n_admin:,}")
        n_no_rows = mark_no_rows(conn)
        print(f"Marcados no_rows:    {n_no_rows:,}")
        conn.commit()
        show_distribution(conn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
