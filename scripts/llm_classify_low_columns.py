#!/usr/bin/env python3
"""LLM batch classifier para columnas low confidence (D.6 iter 5).

Procesa las columnas con `confidence='low'` y description útil. Usa Ollama
3B con prompt few-shot + JSON output forzado. UPSERT en
`dataset_columns_curated` solo si el LLM devuelve confidence >= medium
(para no degradar las low que ya tenemos).

Diseño:
- Concurrency=1: el Ollama de prod está compartido con tráfico real.
- Batch de N columnas por prompt: amortiza overhead Ollama.
- Sleep 0.5s entre prompts: ceder ciclos.
- `--limit N` y `--only-missing` para sub-runs.
- Telemetría: contadores de OK/fail/JSON-parse-fail.

Uso:
    docker compose exec -T api python scripts/llm_classify_low_columns.py [--limit N] [--batch N]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_engine.llm_backend import get_backend  # noqa: E402


SLEEP_BETWEEN_PROMPTS = 0.5    # ceder al Ollama compartido
DEFAULT_BATCH = 8              # columnas por prompt
MAX_TOKENS = 800               # JSON output más grande que prompt input
MODEL_NAME = os.getenv("OLLAMA_MODEL_FAST", "qwen2.5-coder:3b")


_PROMPT_TEMPLATE = """Eres un clasificador de columnas de datos abiertos colombianos.

Para cada columna te doy: name, data_type, description.

Clasifica con uno de estos `semantic_type`:
- geo: columna geográfica (códigos DIVIPOLA, nombres de dpto/mpio/ciudad, coordenadas, dirección, barrio, comuna).
- fecha: año, fecha, periodo, vigencia, día, mes.
- metrica: número que se SUMA/cuenta/mide (total, cantidad, monto, valor, área, caudal, velocidad).
- dimension: categoría/clasificador (género, sector, nivel, tipo, modalidad, estado, status booleano).
- exclude: identificadores (id, nombre persona, NIT, código interno), URLs, textos largos sin valor analítico.

Y un `semantic_subtype`:
- geo: code | name | coord
- fecha: year | date | period
- metrica: count | currency | rate | generic
- dimension: demographic | educational | administrative | status | other
- exclude: id | url | text_long | other

Y `confidence`: high | medium | low (sé conservador: high solo si description es inequívoca).

Devuelve SOLO un JSON array, sin texto adicional. Una entry por columna en el orden recibido.

EJEMPLO entrada:
[
  {{"name": "caudal", "data_type": "number", "description": "Caudal otorgado en litros por segundo"}},
  {{"name": "tipo_via", "data_type": "text", "description": "Tipo de vía: Avenida, Calle, Carrera"}}
]

EJEMPLO salida:
[
  {{"semantic_type": "metrica", "semantic_subtype": "generic", "confidence": "high"}},
  {{"semantic_type": "dimension", "semantic_subtype": "administrative", "confidence": "high"}}
]

Ahora clasifica estas columnas:
{batch_json}
"""


def fetch_low_with_desc(conn, limit: int | None) -> list[dict]:
    sql = """
        SELECT dataset_id, col_name, socrata_data_type, socrata_description
        FROM dataset_columns_curated
        WHERE confidence = 'low'
          AND socrata_description IS NOT NULL
          AND LENGTH(socrata_description) >= 15
        ORDER BY dataset_id, col_name
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql)
        return cur.fetchall()


_VALID_TYPES = {"geo", "fecha", "metrica", "dimension", "exclude"}
_VALID_CONF = {"high", "medium", "low"}


def parse_llm_response(raw: str, expected_count: int) -> list[dict] | None:
    """Extrae JSON array del raw del LLM. Tolera prefijo/sufijo de texto."""
    # Buscar primer `[` hasta el último `]` matching
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        return None
    try:
        parsed = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list) or len(parsed) != expected_count:
        return None
    # Validar shape mínimo
    out = []
    for entry in parsed:
        if not isinstance(entry, dict):
            return None
        t = entry.get("semantic_type", "").lower()
        c = entry.get("confidence", "").lower()
        if t not in _VALID_TYPES or c not in _VALID_CONF:
            return None
        out.append({
            "semantic_type": t,
            "semantic_subtype": entry.get("semantic_subtype", "other"),
            "confidence": c,
        })
    return out


def update_classification(conn, batch: list[dict], classifications: list[dict]) -> int:
    """UPSERT solo las clasificaciones LLM que mejoran (confidence >= medium)."""
    n_updated = 0
    with conn.cursor() as cur:
        for col, classif in zip(batch, classifications):
            # Solo actualizar si el LLM se anima a medium o high
            if classif["confidence"] == "low":
                continue
            cur.execute(
                """
                UPDATE dataset_columns_curated
                SET semantic_type = %s,
                    semantic_subtype = %s,
                    confidence = %s,
                    reason = %s,
                    curated_at = NOW()
                WHERE dataset_id = %s AND col_name = %s
                  AND confidence = 'low'
                """,
                (
                    classif["semantic_type"],
                    classif["semantic_subtype"],
                    classif["confidence"],
                    f"llm_classify: {classif['confidence']}",
                    col["dataset_id"],
                    col["col_name"],
                ),
            )
            n_updated += cur.rowcount
    return n_updated


async def classify_batch(backend, batch: list[dict]) -> list[dict] | None:
    payload = [
        {
            "name": c["col_name"],
            "data_type": c["socrata_data_type"] or "?",
            "description": (c["socrata_description"] or "")[:200],
        }
        for c in batch
    ]
    prompt = _PROMPT_TEMPLATE.format(batch_json=json.dumps(payload, ensure_ascii=False))
    try:
        raw = await backend.generate(prompt, max_tokens=MAX_TOKENS, model=MODEL_NAME, temperature=0.1)
    except Exception as exc:  # noqa: BLE001
        print(f"  LLM error: {exc}", file=sys.stderr)
        return None
    return parse_llm_response(raw, expected_count=len(batch))


async def main_async(args) -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL no definida", file=sys.stderr)
        return 2

    backend = get_backend()  # OllamaBackend si LLM_BACKEND=ollama

    with psycopg.connect(url) as conn:
        cols = fetch_low_with_desc(conn, args.limit)
    print(f"Procesando {len(cols):,} columnas low con description útil…", file=sys.stderr)
    print(f"Modelo: {MODEL_NAME}, batch={args.batch}, sleep={SLEEP_BETWEEN_PROMPTS}s", file=sys.stderr)

    n_total = len(cols)
    n_batches = (n_total + args.batch - 1) // args.batch
    n_processed = 0
    n_parse_fail = 0
    n_llm_fail = 0
    n_updated_total = 0
    new_conf: Counter = Counter()
    started = time.perf_counter()

    with psycopg.connect(url) as write_conn:
        for batch_idx in range(n_batches):
            batch = cols[batch_idx * args.batch : (batch_idx + 1) * args.batch]
            classifications = await classify_batch(backend, batch)
            if classifications is None:
                n_llm_fail += len(batch)
            else:
                # Si el parser falló (None) ya está manejado. Sino, son válidos.
                n_updated = update_classification(write_conn, batch, classifications)
                write_conn.commit()
                n_updated_total += n_updated
                for c in classifications:
                    new_conf[c["confidence"]] += 1
            n_processed += len(batch)

            if (batch_idx + 1) % 20 == 0:
                elapsed = time.perf_counter() - started
                rate = n_processed / elapsed if elapsed else 0
                eta_s = (n_total - n_processed) / rate if rate else 0
                print(
                    f"  batch {batch_idx+1}/{n_batches} ({n_processed:,}/{n_total:,}) "
                    f"updates={n_updated_total:,} llm_fail={n_llm_fail} "
                    f"rate={rate:.1f}/s eta={eta_s/60:.0f}min",
                    file=sys.stderr,
                )
            await asyncio.sleep(SLEEP_BETWEEN_PROMPTS)

    print(f"\n=== Resumen ===")
    print(f"Columnas procesadas:   {n_processed:,}")
    print(f"LLM fail (network/parse): {n_llm_fail}")
    print(f"DB updates (low → ≥medium): {n_updated_total:,}")
    print(f"Distribución LLM confidence devuelta:")
    for c, n in new_conf.most_common():
        print(f"  {c}: {n:,}")

    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH)
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
