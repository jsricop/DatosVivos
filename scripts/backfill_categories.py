#!/usr/bin/env python3
"""Backfill de `category` para datasets sin categoría — clasificación semántica.

Problema (2026-07-11): 2.504 datasets útiles (11%) tienen `category` NULL/'' —
invisibles para el filtro TEMA de chips aunque sean la respuesta correcta
(caso real: "Matrícula Total en Colegios Oficiales. Bogotá D.C." f3r4-br7h).

Método (mismo patrón que la inferencia DIVIPOLA: determinista, con confianza):
1. Vocabulario = categorías reales con ≥ --min-class ejemplos útiles,
   excluyendo 'geospatial' (formato, no tema) y unificando variantes de
   mayúsculas ("Función pública"/"Función Pública" → la grafía dominante).
2. Centroide por categoría = promedio de embeddings e5 (mismo modelo del
   índice, prefijo "passage:") de hasta --cap ejemplos etiquetados.
3. Validación holdout (10%): precisión de la asignación al umbral elegido —
   se imprime ANTES de aplicar; si no convence, no se aplica.
4. Asignación: coseno top-1 ≥ --min-score y margen sobre top-2 ≥ --min-margin.
   Lo que no supera el umbral se queda NULL (preferimos hueco a etiqueta falsa).

Por defecto DRY-RUN (no escribe). --apply para escribir. Reporte siempre en
eval/reports/backfill_categories_<fecha>.md.

Durabilidad: requiere el guard COALESCE en el upsert del ETL (mismo commit)
para que la corrida nocturna no pise lo inferido con NULL de la fuente.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_engine.vector_index import DEFAULT_MODEL  # noqa: E402


def _connect():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL no configurada")
    return psycopg.connect(url, row_factory=dict_row)


def _doc(r: dict) -> str:
    parts = [r["name"] or ""]
    if r.get("entity_raw"):
        parts.append(str(r["entity_raw"]))
    if r.get("description"):
        parts.append(str(r["description"])[:300])
    return "passage: " + " | ".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="escribir (default: dry-run)")
    ap.add_argument("--min-class", type=int, default=150)
    ap.add_argument("--cap", type=int, default=400, help="ejemplos máx por categoría")
    ap.add_argument("--min-score", type=float, default=0.82)
    ap.add_argument("--min-margin", type=float, default=0.005)
    ap.add_argument("--out", default="eval/reports")
    args = ap.parse_args()

    from sentence_transformers import SentenceTransformer

    with _connect() as conn, conn.cursor() as cur:
        # Vocabulario canónico: grafía dominante por lower(category).
        cur.execute("""
            SELECT category, count(*) AS n FROM datasets
            WHERE (quality_flag IS NULL OR quality_flag='ok')
              AND category IS NOT NULL AND category != '' AND category != 'geospatial'
            GROUP BY category
        """)
        by_lower: dict[str, Counter] = defaultdict(Counter)
        for r in cur.fetchall():
            by_lower[r["category"].strip().lower()][r["category"].strip()] += r["n"]
        canon: dict[str, str] = {}   # lower → grafía dominante
        for low, spellings in by_lower.items():
            if sum(spellings.values()) >= args.min_class:
                canon[low] = spellings.most_common(1)[0][0]
        print(f"vocabulario: {len(canon)} categorías (≥{args.min_class} ejemplos)")

        # Etiquetados (cap por categoría, los más vistos primero).
        cur.execute("""
            SELECT dataset_id, name, entity_raw, description, category
            FROM datasets
            WHERE (quality_flag IS NULL OR quality_flag='ok')
              AND category IS NOT NULL AND category != '' AND category != 'geospatial'
            ORDER BY view_count DESC NULLS LAST
        """)
        labeled: dict[str, list[dict]] = defaultdict(list)
        for r in cur.fetchall():
            low = r["category"].strip().lower()
            if low in canon and len(labeled[low]) < args.cap:
                labeled[low].append(r)

        # Objetivos.
        cur.execute("""
            SELECT dataset_id, name, entity_raw, description
            FROM datasets
            WHERE (quality_flag IS NULL OR quality_flag='ok')
              AND (category IS NULL OR category = '')
        """)
        targets = cur.fetchall()
        print(f"objetivos sin categoría: {len(targets)}")

    model = SentenceTransformer(DEFAULT_MODEL)

    def embed(texts: list[str]) -> np.ndarray:
        return np.asarray(model.encode(
            texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False
        ))

    # Holdout 10% por clase, centroides con el 90%.
    rng = np.random.default_rng(20260711)
    centroids: dict[str, np.ndarray] = {}
    holdout: list[tuple[str, dict]] = []
    for low, rows in labeled.items():
        idx = rng.permutation(len(rows))
        n_hold = max(1, len(rows) // 10)
        hold, train = [rows[i] for i in idx[:n_hold]], [rows[i] for i in idx[n_hold:]]
        holdout.extend((low, r) for r in hold)
        vecs = embed([_doc(r) for r in train])
        c = vecs.mean(axis=0)
        centroids[low] = c / np.linalg.norm(c)

    cats = sorted(centroids)
    C = np.stack([centroids[c] for c in cats])

    def classify(rows: list[dict]) -> list[tuple[str | None, float, float]]:
        """→ [(categoria_lower|None, score_top1, margen)]"""
        if not rows:
            return []
        sims = embed([_doc(r) for r in rows]) @ C.T
        out = []
        for s in sims:
            order = np.argsort(s)[::-1]
            top1, top2 = float(s[order[0]]), float(s[order[1]])
            ok = top1 >= args.min_score and (top1 - top2) >= args.min_margin
            out.append((cats[order[0]] if ok else None, top1, top1 - top2))
        return out

    # Validación holdout.
    preds = classify([r for _, r in holdout])
    asignados = [(true, p) for (true, _), (p, _, _) in zip(holdout, preds) if p]
    aciertos = sum(1 for t, p in asignados if t == p)
    cobertura = len(asignados) / max(1, len(holdout))
    precision = aciertos / max(1, len(asignados))
    print(f"holdout: n={len(holdout)} cobertura={cobertura:.1%} precisión={precision:.1%}")

    # Clasificación de los objetivos.
    res = classify(targets)
    asigna = [
        (t["dataset_id"], canon[cat], score, margen)
        for t, (cat, score, margen) in zip(targets, res) if cat
    ]
    dist = Counter(c for _, c, _, _ in asigna)
    print(f"asignables: {len(asigna)}/{len(targets)} ({len(asigna)/max(1,len(targets)):.1%})")
    for c, n in dist.most_common(12):
        print(f"  {n:5d}  {c}")

    # Reporte.
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    out = Path(args.out) / f"backfill_categories_{ts}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Backfill de categorías — {ts} ({'APPLY' if args.apply else 'DRY-RUN'})",
        f"- modelo: {DEFAULT_MODEL} · min_score={args.min_score} · min_margin={args.min_margin}",
        f"- vocabulario: {len(cats)} categorías · objetivos: {len(targets)}",
        f"- holdout: cobertura {cobertura:.1%} · **precisión {precision:.1%}** (n={len(holdout)})",
        f"- asignados: {len(asigna)} ({len(asigna)/max(1,len(targets)):.1%}); resto queda NULL",
        "",
        "| categoría | asignados |",
        "|---|---|",
        *[f"| {c} | {n} |" for c, n in dist.most_common()],
        "",
        "Muestra (20):",
        *[f"- `{d}` → {c} (score {s:.3f}, margen {m:.3f})" for d, c, s, m in asigna[:20]],
    ]
    out.write_text("\n".join(lines))
    print(f"reporte: {out}")

    if not args.apply:
        print("DRY-RUN: no se escribió nada. Repite con --apply.")
        return 0

    with _connect() as conn, conn.cursor() as cur:
        cur.executemany(
            "UPDATE datasets SET category = %s WHERE dataset_id = %s "
            "AND (category IS NULL OR category = '')",
            [(c, d) for d, c, _, _ in asigna],
        )
        conn.commit()
        print(f"APPLY: {len(asigna)} categorías escritas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
