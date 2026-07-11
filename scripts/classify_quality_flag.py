#!/usr/bin/env python3
"""Marca `quality_flag` en `datasets` según reglas heurísticas (D.5).

Marcado actual:
- `admin_only`: nombres que matchean patrones de obligaciones Ley 1712
  (esquema de publicación, índice de información clasificada, registro de
  activos de información, ITA).
- `no_rows`: row_count = 0 o NULL. DESACTIVADO por defecto (--include-no-rows):
  en este catálogo los sin-conteo son federados no-tabulares (solo_metadatos /
  requiere_herramienta), no vacíos genuinos; marcarlos escondería federados útiles.

NO marca `stale` automáticamente — el score A.2 ya lo maneja vía decay de
freshness. Si decidimos ocultarlos por default, agregar acá.

Idempotente: re-corrigible. UPDATE explícito por flag, no NULL → flag
(es decir, los `ok` quedan NULL para minimizar ruido en la tabla).
`mark_admin_only` se reusa desde el ETL (etl_refresh_catalog) en cada refresh.

Uso:
    DATABASE_URL=... python scripts/classify_quality_flag.py                 # solo admin_only
    DATABASE_URL=... python scripts/classify_quality_flag.py --include-no-rows
    # o dentro del container:
    docker compose exec -T api python scripts/classify_quality_flag.py
"""

from __future__ import annotations

import argparse
import os
import sys

import psycopg


# Patrones administrativos, en minúscula y SIN tildes: el match normaliza el
# nombre con translate(lower(name), ...) para que "ÍNDICE", "Indice" e
# "INFORMACIÓN"/"informacion" (cualquier combinación de mayúsculas y tildes)
# caigan igual. Antes se enumeraban variantes acentuadas a mano y los nombres
# MIXTOS ("INDICE DE INFORMACIÓN...") se escapaban (caso real FODESEP,
# 2026-07-11). Sincronizado con `audit_catalog_quality._ADMIN_PATTERNS`.
_ADMIN_PATTERNS = [
    "esquema de publicacion",
    "indice de informacion clasificada",
    # Variante sin "de": "Índice Información Clasificada y Reservada" (q59t-e9gs).
    "indice informacion clasificada",
    "registro de activos de informacion",
    "activos de informacion",
    "informe de gestion",
    "tabla de retencion documental",
    "instrumentos archivisticos",
]

# Normalización en SQL puro (sin extensión unaccent): minúsculas + tildes fuera.
_NORM = "translate(lower(name), 'áéíóúüñ', 'aeiouun')"


def mark_admin_only(conn) -> int:
    """UPDATE datasets SET quality_flag='admin_only' donde nombre match.

    Returns el número de filas afectadas.
    """
    or_clause = " OR ".join([f"{_NORM} LIKE %s"] * len(_ADMIN_PATTERNS))
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
    p = argparse.ArgumentParser(description="Clasifica quality_flag en datasets (D.5).")
    p.add_argument(
        "--include-no-rows",
        action="store_true",
        help=(
            "Además de admin_only, marca no_rows (row_count 0/NULL). DESACTIVADO por "
            "defecto: en este catálogo los sin-conteo son federados no-tabulares, no "
            "vacíos genuinos; marcarlos escondería federados útiles. Ver plan/ADR."
        ),
    )
    args = p.parse_args()

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL no definida", file=sys.stderr)
        return 2

    with psycopg.connect(url) as conn:
        n_admin = mark_admin_only(conn)
        print(f"Marcados admin_only: {n_admin:,}")
        if args.include_no_rows:
            n_no_rows = mark_no_rows(conn)
            print(f"Marcados no_rows:    {n_no_rows:,}")
        else:
            print("no_rows: omitido (usar --include-no-rows para activarlo)")
        conn.commit()
        show_distribution(conn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
