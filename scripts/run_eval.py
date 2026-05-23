#!/usr/bin/env python3
"""Audit harness — corre el golden set contra /api/v1/query y mide outcomes.

Diseñado para Fase 0 del audit top-down (ver plan en docs/adr/017 cuando exista).
Sin medición no podemos validar si los cambios de Fase 1-3 mejoran o empeoran.

Uso típico:
    python scripts/run_eval.py                              # local default
    EVAL_BASE_URL=https://datosvivos.co python scripts/run_eval.py
    python scripts/run_eval.py --golden eval/golden_queries.yaml --out eval/reports/

Salida:
    eval/reports/YYYY-MM-DDTHH-MM-SS.json     — datos crudos por query
    eval/reports/YYYY-MM-DDTHH-MM-SS.md       — resumen humano

Métricas:
    accuracy_at_1        % de queries curadas donde top-1 == expected_dataset_id
    intent_accuracy      % donde intent emitido == expected_intent
    dashboard_correctness % donde la decisión emitir/omitir dashboard fue correcta
    hallucination_rate   % de queries con narrative_correction (señal censura)
    p50/p95 latency_s    del campo elapsed_s

Las queries con needs_curation=true se ejecutan pero NO cuentan en accuracy_at_1
(solo loggean el dataset elegido para construir baseline).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml


DEFAULT_BASE_URL = os.environ.get("EVAL_BASE_URL", "http://localhost:8001")
DEFAULT_GOLDEN = Path("eval/golden_queries.yaml")
DEFAULT_OUT = Path("eval/reports")
DEFAULT_TIMEOUT = 90.0  # seconds por query
DEFAULT_CONCURRENCY = 1  # secuencial por defecto — el LLM Ollama no escala


def _parse_sse(raw: str) -> list[tuple[str, dict[str, Any]]]:
    """Parsea un stream SSE en lista [(event_name, data_dict), ...]."""
    events: list[tuple[str, dict[str, Any]]] = []
    current_event: str | None = None
    data_lines: list[str] = []
    for line in raw.splitlines():
        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:"):].strip())
        elif line == "":
            if current_event and data_lines:
                payload_raw = "\n".join(data_lines)
                try:
                    payload = json.loads(payload_raw)
                except json.JSONDecodeError:
                    payload = {"_raw": payload_raw}
                events.append((current_event, payload))
            current_event = None
            data_lines = []
    return events


async def _run_one(client: httpx.AsyncClient, base_url: str, entry: dict[str, Any]) -> dict[str, Any]:
    q = entry["q"]
    started = time.perf_counter()
    result: dict[str, Any] = {
        "id": entry["id"],
        "q": q,
        "expected_dataset_id": entry.get("expected_dataset_id"),
        "expected_intent": entry.get("expected_intent"),
        "expected_territory": entry.get("expected_territory"),
        "needs_curation": entry.get("needs_curation", False),
        "not_acceptable_datasets": entry.get("not_acceptable_datasets") or [],
        "actual_dataset_top1": None,
        "actual_intent": None,
        "actual_geo_resolved": None,
        "dashboard_emitted": False,
        "had_narrative_correction": False,
        "events_seen": [],
        "elapsed_s": None,
        "error": None,
    }
    try:
        async with client.stream(
            "POST",
            f"{base_url}/api/v1/query",
            json={"q": q},
            timeout=DEFAULT_TIMEOUT,
        ) as response:
            response.raise_for_status()
            buf = ""
            async for chunk in response.aiter_text():
                buf += chunk
            events = _parse_sse(buf)
            for name, data in events:
                result["events_seen"].append(name)
                if name == "intent":
                    result["actual_intent"] = data.get("intent")
                elif name == "dataset_hits":
                    hits = data.get("datasets") or []
                    if hits and isinstance(hits[0], dict):
                        result["actual_dataset_top1"] = hits[0].get("id")
                elif name == "citations" and not result["actual_dataset_top1"]:
                    cits = data.get("citations") or []
                    if cits and isinstance(cits[0], dict):
                        result["actual_dataset_top1"] = cits[0].get("id")
                elif name == "narrative_correction":
                    result["had_narrative_correction"] = True
                elif name == "dashboard_spec":
                    result["dashboard_emitted"] = True
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["elapsed_s"] = round(time.perf_counter() - started, 2)
    return result


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return round(values[0], 2)
    return round(statistics.quantiles(values, n=100, method="inclusive")[int(p) - 1], 2)


def _evaluate(results: list[dict[str, Any]]) -> dict[str, Any]:
    curated = [r for r in results if not r["needs_curation"] and r["expected_dataset_id"]]
    intent_curated = [r for r in results if r.get("expected_intent")]
    latencies = [r["elapsed_s"] for r in results if r["elapsed_s"] is not None]

    # accuracy@1
    acc_pass = sum(1 for r in curated if r["actual_dataset_top1"] == r["expected_dataset_id"])
    # not_acceptable (sanidad)
    forbidden_hits = sum(
        1
        for r in results
        if r["actual_dataset_top1"] and r["actual_dataset_top1"] in r["not_acceptable_datasets"]
    )
    # intent
    intent_pass = sum(1 for r in intent_curated if r["actual_intent"] == r["expected_intent"])
    # halluc
    halluc = sum(1 for r in results if r["had_narrative_correction"])
    # errores
    errors = sum(1 for r in results if r["error"])

    return {
        "total_queries": len(results),
        "curated_queries": len(curated),
        "errored": errors,
        "accuracy_at_1": {
            "pass": acc_pass,
            "total": len(curated),
            "rate": round(acc_pass / len(curated), 4) if curated else None,
        },
        "intent_accuracy": {
            "pass": intent_pass,
            "total": len(intent_curated),
            "rate": round(intent_pass / len(intent_curated), 4) if intent_curated else None,
        },
        "forbidden_dataset_hits": forbidden_hits,
        "hallucination_rate": round(halluc / len(results), 4) if results else None,
        "p50_latency_s": _percentile(latencies, 50),
        "p95_latency_s": _percentile(latencies, 95),
    }


def _render_markdown(report: dict[str, Any], results: list[dict[str, Any]]) -> str:
    m = report["metrics"]
    lines = [
        f"# Eval report — {report['timestamp']}",
        "",
        f"- **Base URL**: `{report['base_url']}`",
        f"- **Golden set**: `{report['golden_path']}`",
        f"- **Queries**: {m['total_queries']} (curadas: {m['curated_queries']}, errored: {m['errored']})",
        "",
        "## Métricas",
        "",
        f"- `accuracy@1`: **{m['accuracy_at_1']['pass']}/{m['accuracy_at_1']['total']}** "
        f"({m['accuracy_at_1']['rate'] if m['accuracy_at_1']['rate'] is not None else 'n/a'})",
        f"- `intent_accuracy`: **{m['intent_accuracy']['pass']}/{m['intent_accuracy']['total']}** "
        f"({m['intent_accuracy']['rate'] if m['intent_accuracy']['rate'] is not None else 'n/a'})",
        f"- `forbidden_dataset_hits`: **{m['forbidden_dataset_hits']}** (debe ser 0)",
        f"- `hallucination_rate`: {m['hallucination_rate']}",
        f"- `p50/p95 latency_s`: {m['p50_latency_s']} / {m['p95_latency_s']}",
        "",
        "## Per-query",
        "",
        "| id | q | expected | actual | intent ok | halluc | latency_s | error |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        q_short = (r["q"][:50] + "…") if len(r["q"]) > 50 else r["q"]
        exp = r["expected_dataset_id"] or ("?" if r["needs_curation"] else "—")
        act = r["actual_dataset_top1"] or "—"
        intent_ok = "✓" if r.get("expected_intent") and r["actual_intent"] == r["expected_intent"] else (
            "✗" if r.get("expected_intent") else "—"
        )
        halluc = "✗" if r["had_narrative_correction"] else "—"
        err = (r["error"] or "")[:40]
        lines.append(
            f"| {r['id']} | {q_short} | {exp} | {act} | {intent_ok} | {halluc} | {r['elapsed_s']} | {err} |"
        )
    return "\n".join(lines) + "\n"


async def _main(args: argparse.Namespace) -> int:
    golden_path = Path(args.golden)
    if not golden_path.exists():
        print(f"ERROR: golden set no encontrado en {golden_path}", file=sys.stderr)
        return 2
    raw = yaml.safe_load(golden_path.read_text())
    entries = raw.get("queries") or []
    if not entries:
        print("ERROR: golden set vacío", file=sys.stderr)
        return 2
    if args.limit:
        entries = entries[: args.limit]

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Corriendo {len(entries)} queries contra {args.base_url} …", file=sys.stderr)
    started_ts = datetime.now(timezone.utc)

    async with httpx.AsyncClient() as client:
        sem = asyncio.Semaphore(args.concurrency)

        async def _bounded(entry: dict[str, Any]) -> dict[str, Any]:
            async with sem:
                res = await _run_one(client, args.base_url, entry)
                marker = (
                    "OK"
                    if not res["error"]
                    and (res["needs_curation"] or res["actual_dataset_top1"] == res["expected_dataset_id"])
                    else ("MISS" if not res["error"] else "ERR")
                )
                print(
                    f"  [{marker}] {res['id']} {res['elapsed_s']}s "
                    f"→ {res['actual_dataset_top1']}",
                    file=sys.stderr,
                )
                return res

        results = await asyncio.gather(*[_bounded(e) for e in entries])

    report = {
        "timestamp": started_ts.isoformat(timespec="seconds"),
        "base_url": args.base_url,
        "golden_path": str(golden_path),
        "metrics": _evaluate(results),
        "per_query": results,
    }

    stamp = started_ts.strftime("%Y-%m-%dT%H-%M-%S")
    json_path = out_dir / f"{stamp}.json"
    md_path = out_dir / f"{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    md_path.write_text(_render_markdown(report, results))

    print(f"\nReporte: {json_path}", file=sys.stderr)
    print(f"Resumen: {md_path}", file=sys.stderr)
    m = report["metrics"]
    rate = m["accuracy_at_1"]["rate"]
    print(
        f"\n  accuracy@1={rate}  intent_accuracy={m['intent_accuracy']['rate']}  "
        f"forbidden={m['forbidden_dataset_hits']}  p95={m['p95_latency_s']}s",
        file=sys.stderr,
    )
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--golden", default=str(DEFAULT_GOLDEN))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--limit", type=int, default=None, help="Solo correr las primeras N queries (debug)")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(asyncio.run(_main(_parse_args())))
