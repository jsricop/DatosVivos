#!/usr/bin/env python3
"""Auditoría de calidad del catálogo de datasets (D.1).

Read-only. No modifica datos. Genera un reporte markdown en
`data/curation/quality_audit_YYYY-MM-DD.md` con:

- Totales y completitud por columna
- Distribución de jurisdicción y confidence (post Fase 1 prereq)
- Datasets sin entity, sin category, sin row_count, sin update reciente
- Tags duplicados por normalización (`educacion` vs `educación`)
- Top entity_raw para detectar variantes a fusionar
- Datasets duplicados estrictos (mismo nombre + entidad)
- Heurística "admin-only": datasets cuyo nombre matchea patterns de
  esquema de publicación / ITA / índice clasificada — no aportan datos

Uso:
    DATABASE_URL=... python scripts/audit_catalog_quality.py

    o dentro del container API:
    docker compose exec -T api python scripts/audit_catalog_quality.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _query(cur, sql: str, params: tuple | list = ()) -> list[dict]:
    cur.execute(sql, params)
    return cur.fetchall()


def _scalar(cur, sql: str, params: tuple | list = ()) -> int | None:
    cur.execute(sql, params)
    row = cur.fetchone()
    return row.get("n") if row else None


# ----------------------------------------------------------------------
# Reporte
# ----------------------------------------------------------------------


_ADMIN_PATTERNS = [
    "esquema de publicación",
    "esquema de publicacion",
    "índice de información clasificada",
    "indice de informacion clasificada",
    "registro de activos de información",
    "activos de información",
    "activos de informacion",
    "informe de gestión",
    "tabla de retención documental",
    "instrumentos archivísticos",
]


def run_audit(conn) -> str:
    parts: list[str] = []
    stamp_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    parts.append(f"# Auditoría calidad catálogo — {stamp_iso}")
    parts.append("")
    parts.append("> Read-only. Solo lectura del estado actual.")
    parts.append("")

    with conn.cursor() as cur:
        total = _scalar(cur, "SELECT COUNT(*) AS n FROM datasets")
        parts.append(f"## Total datasets: **{total:,}**")
        parts.append("")

        # ------------------------------------------------------------------
        # 1. Completitud por columna
        # ------------------------------------------------------------------
        parts.append("## 1. Completitud por columna")
        parts.append("")
        parts.append("| Columna | Vacíos / nulls | % | Comentario |")
        parts.append("|---|---:|---:|---|")
        checks = [
            ("entity_raw", "entity_raw IS NULL OR entity_raw = ''",
             "imposible filtrar por ENTIDAD si falta"),
            ("category", "category IS NULL OR category = ''",
             "chip TEMA queda fuera"),
            ("description", "description IS NULL OR description = ''",
             "afecta refinador texto libre"),
            ("row_count", "row_count IS NULL OR row_count = 0",
             "dataset sin filas: candidato D.5 quality_flag='no_rows'"),
            ("view_count", "view_count IS NULL OR view_count = 0",
             "el score A.2 lo asume al menos 1; impacto bajo"),
            ("rows_updated_at", "rows_updated_at IS NULL",
             "score A.2 freshness=0 → desplazamiento al fondo"),
            ("socrata_url", "socrata_url IS NULL OR socrata_url = ''",
             "imposible linkear; UI cae al fallback genérico"),
            ("jurisdiccion_nivel", "jurisdiccion_nivel IS NULL",
             "chip TERRITORIO no puede filtrar"),
        ]
        for col, where, comment in checks:
            n = _scalar(cur, f"SELECT COUNT(*) AS n FROM datasets WHERE {where}") or 0
            pct = (100 * n / total) if total else 0
            parts.append(f"| `{col}` | {n:,} | {pct:.1f}% | {comment} |")
        parts.append("")

        # ------------------------------------------------------------------
        # 2. Categorías: duplicadas por casing/tilde
        # ------------------------------------------------------------------
        parts.append("## 2. Categorías raw vs normalizadas")
        parts.append("")
        raw_n = _scalar(cur,
            "SELECT COUNT(DISTINCT category) AS n FROM datasets WHERE category IS NOT NULL"
        ) or 0
        norm_n = _scalar(cur,
            "SELECT COUNT(DISTINCT lower(unaccent(category))) AS n "
            "FROM datasets WHERE category IS NOT NULL"
        ) if _ext_unaccent_exists(conn) else None
        parts.append(f"- distinct(category) raw = **{raw_n}**")
        if norm_n is not None:
            parts.append(f"- distinct(lower+unaccent) = **{norm_n}**")
            parts.append(f"- duplicados por normalización: **{raw_n - norm_n}**")
        else:
            parts.append("- (no se evaluó normalización: extensión `unaccent` no instalada)")
        parts.append("")
        top_cats = _query(cur,
            "SELECT category, COUNT(*) AS n FROM datasets WHERE category IS NOT NULL "
            "GROUP BY category ORDER BY n DESC LIMIT 20"
        )
        parts.append("Top 20 categorías:")
        parts.append("")
        parts.append("| category | datasets |")
        parts.append("|---|---:|")
        for r in top_cats:
            parts.append(f"| {r['category']} | {r['n']:,} |")
        parts.append("")

        # ------------------------------------------------------------------
        # 3. Entidades (entity_raw)
        # ------------------------------------------------------------------
        parts.append("## 3. Entidades — top 30")
        parts.append("")
        parts.append("Para detectar variantes a fusionar en D.2 (`expand_entities.py`).")
        parts.append("")
        ents = _query(cur,
            "SELECT entity_raw, COUNT(*) AS n FROM datasets "
            "WHERE entity_raw IS NOT NULL AND entity_raw != '' "
            "GROUP BY entity_raw ORDER BY n DESC LIMIT 30"
        )
        parts.append("| entity_raw | datasets |")
        parts.append("|---|---:|")
        for r in ents:
            parts.append(f"| {(r['entity_raw'] or '')[:90]} | {r['n']:,} |")
        parts.append("")
        distinct_ents = _scalar(cur,
            "SELECT COUNT(DISTINCT entity_raw) AS n FROM datasets "
            "WHERE entity_raw IS NOT NULL AND entity_raw != ''"
        ) or 0
        parts.append(f"Total entidades distintas (raw): **{distinct_ents:,}**")
        parts.append("(tabla `entities` actual tiene ~11 entries; D.2 las expande)")
        parts.append("")

        # ------------------------------------------------------------------
        # 4. Datasets stale
        # ------------------------------------------------------------------
        parts.append("## 4. Datasets stale (sin actualización reciente)")
        parts.append("")
        stale_buckets = [
            ("Stale >3 años", "NOW() - INTERVAL '3 years'"),
            ("Stale >1 año", "NOW() - INTERVAL '1 year'"),
            ("Stale >6 meses", "NOW() - INTERVAL '6 months'"),
        ]
        parts.append("| Umbral | count |")
        parts.append("|---|---:|")
        for label, cutoff in stale_buckets:
            n = _scalar(cur,
                f"SELECT COUNT(*) AS n FROM datasets "
                f"WHERE rows_updated_at < {cutoff}"
            ) or 0
            parts.append(f"| {label} | {n:,} |")
        parts.append("")

        # ------------------------------------------------------------------
        # 5. Datasets administrativos
        # ------------------------------------------------------------------
        parts.append("## 5. Datasets administrativos (heurística por nombre)")
        parts.append("")
        parts.append(
            "Datasets cuyo `name` matchea patrones administrativos "
            "(esquema de publicación, ITA, registro de activos, etc.). "
            "Candidatos a D.5 `quality_flag='admin_only'` para sacarlos del "
            "subset por default."
        )
        parts.append("")
        admin_total = 0
        parts.append("| Patrón | datasets |")
        parts.append("|---|---:|")
        for p in _ADMIN_PATTERNS:
            n = _scalar(cur,
                "SELECT COUNT(*) AS n FROM datasets WHERE name ILIKE %s",
                (f"%{p}%",),
            ) or 0
            admin_total += n
            parts.append(f"| {p} | {n:,} |")
        parts.append(f"| **total bruto** (con overlap) | **{admin_total:,}** |")
        parts.append("")
        # Sin overlap
        union_where = " OR ".join(["name ILIKE %s"] * len(_ADMIN_PATTERNS))
        params = tuple(f"%{p}%" for p in _ADMIN_PATTERNS)
        union_n = _scalar(cur,
            f"SELECT COUNT(*) AS n FROM datasets WHERE {union_where}", params
        ) or 0
        pct = (100 * union_n / total) if total else 0
        parts.append(f"- únicos (sin doble-conteo): **{union_n:,}** ({pct:.1f}% del catálogo)")
        parts.append("")

        # ------------------------------------------------------------------
        # 6. Duplicados estrictos (mismo name + entity_raw)
        # ------------------------------------------------------------------
        parts.append("## 6. Duplicados estrictos (mismo `name` + `entity_raw`)")
        parts.append("")
        dups = _query(cur, """
            SELECT name, entity_raw, COUNT(*) AS n
            FROM datasets
            WHERE name IS NOT NULL AND entity_raw IS NOT NULL
            GROUP BY name, entity_raw
            HAVING COUNT(*) > 1
            ORDER BY n DESC
            LIMIT 15
        """)
        if dups:
            parts.append(f"Encontrados: **{len(dups)}** grupos con duplicados (top-15):")
            parts.append("")
            parts.append("| name | entity_raw | n |")
            parts.append("|---|---|---:|")
            for r in dups:
                parts.append(f"| {(r['name'] or '')[:60]} | {(r['entity_raw'] or '')[:50]} | {r['n']} |")
        else:
            parts.append("Sin duplicados estrictos detectados ✅")
        parts.append("")

        # ------------------------------------------------------------------
        # 7. Jurisdicción (post Fase 1 prereq)
        # ------------------------------------------------------------------
        parts.append("## 7. Jurisdicción geográfica (post Fase 1)")
        parts.append("")
        jur = _query(cur,
            "SELECT jurisdiccion_nivel, COUNT(*) AS n FROM datasets "
            "GROUP BY jurisdiccion_nivel ORDER BY n DESC"
        )
        parts.append("| nivel | datasets |")
        parts.append("|---|---:|")
        for r in jur:
            label = r["jurisdiccion_nivel"] or "(none)"
            parts.append(f"| {label} | {r['n']:,} |")
        parts.append("")
        conf = _query(cur,
            "SELECT jurisdiccion_confidence, COUNT(*) AS n FROM datasets "
            "GROUP BY jurisdiccion_confidence ORDER BY n DESC"
        )
        parts.append("| confidence | datasets |")
        parts.append("|---|---:|")
        for r in conf:
            label = r["jurisdiccion_confidence"] or "(none)"
            parts.append(f"| {label} | {r['n']:,} |")
        parts.append("")

        # ------------------------------------------------------------------
        # 8. Tags
        # ------------------------------------------------------------------
        parts.append("## 8. Tags (dataset_tags)")
        parts.append("")
        tag_total = _scalar(cur, "SELECT COUNT(*) AS n FROM dataset_tags") or 0
        tag_distinct = _scalar(cur, "SELECT COUNT(DISTINCT tag) AS n FROM dataset_tags") or 0
        parts.append(f"- total entries: **{tag_total:,}**")
        parts.append(f"- distinct tags (raw): **{tag_distinct:,}**")
        if _ext_unaccent_exists(conn):
            tag_normalized = _scalar(cur,
                "SELECT COUNT(DISTINCT lower(unaccent(tag))) AS n FROM dataset_tags"
            ) or 0
            parts.append(f"- distinct normalizados: **{tag_normalized:,}**")
            parts.append(f"- duplicados por normalización: **{tag_distinct - tag_normalized:,}**")
            parts.append("")
            parts.append("Ejemplos de variantes detectadas:")
            parts.append("")
            variants = _query(cur,
                "SELECT lower(unaccent(tag)) AS norm, array_agg(DISTINCT tag) AS variants, "
                "COUNT(DISTINCT tag) AS n_variants "
                "FROM dataset_tags GROUP BY norm HAVING COUNT(DISTINCT tag) > 1 "
                "ORDER BY n_variants DESC LIMIT 10"
            )
            parts.append("| normalizado | variantes |")
            parts.append("|---|---|")
            for r in variants:
                parts.append(f"| {r['norm']} | {', '.join(r['variants'])} |")
        else:
            parts.append("- (variantes con tildes no evaluadas — `unaccent` no instalada)")
        parts.append("")

        # ------------------------------------------------------------------
        # 9. Sugerencias para próximos pasos
        # ------------------------------------------------------------------
        parts.append("## 9. Resumen de hallazgos clave")
        parts.append("")
        parts.append("Pendiente análisis humano. Ver tablas arriba para decidir:")
        parts.append("")
        parts.append("- D.2: ¿qué entidades fusionar / agregar a tabla `entities`?")
        parts.append("- D.3: ¿qué tags normalizar/eliminar?")
        parts.append("- D.5: ¿`quality_flag` para los administrativos detectados?")
        parts.append("- D.6: ¿cuál es el top-N realista a curar manualmente?")

    return "\n".join(parts) + "\n"


def _ext_unaccent_exists(conn) -> bool:
    """Detecta si la extensión `unaccent` está instalada."""
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_extension WHERE extname='unaccent'")
        return cur.fetchone() is not None


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL no definida", file=sys.stderr)
        return 2

    out_dir = Path("data/curation")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = out_dir / f"quality_audit_{stamp}.md"

    with psycopg.connect(url, row_factory=dict_row) as conn:
        report = run_audit(conn)

    out_path.write_text(report)
    print(f"OK: reporte en {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
