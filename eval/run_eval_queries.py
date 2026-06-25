#!/usr/bin/env python3
"""Eval del camino generativo (NL2SQL) sobre el SSE de /api/v1/query — ADR-022 Fase 6.

A diferencia de run_eval_chips.py (camino determinista), este harness ejercita el
motor generativo con verificación: consume el stream SSE, recoge los eventos
(intent, citations, interpretation, refusal, soql) y evalúa:

  - Selección de dataset (top-1 de citations) vs expected_dataset_id, cuando
    needs_curation=false.
  - not_acceptable_datasets: si aparece como top-1 → failure.
  - Verificación: el outcome observado (verified | refused | fallback_template |
    unverified) vs expected_verification.

KPI primario — "falsos verificados": para las preguntas trampa (category: trap),
el ÉXITO es rehusar / degradar a template / marcar sin-verificar; el FALLO es
presentar una cifra como verificada. Mide cuántas trampas se cuelan como cifra
oficial plausible-pero-equivocada (debe tender a 0).

Uso:
    EVAL_BASE_URL=https://datosvivos.co python eval/run_eval_queries.py
    python eval/run_eval_queries.py --base-url http://localhost:8000 --only trap

Salida: stdout + eval/reports/queries_<fecha>.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError:
    print("ERROR: requiere `pip install pyyaml`", file=sys.stderr)
    sys.exit(1)

BASE_URL_DEFAULT = os.environ.get("EVAL_BASE_URL", "https://datosvivos.co")
GOLDEN = Path(__file__).parent / "golden_queries.yaml"
REPORTS = Path(__file__).parent / "reports"
UA = "DatosVivos/run_eval_queries"


def load_cases() -> list[dict]:
    with open(GOLDEN, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("queries") or []


def call_query(base_url: str, q: str, timeout: float = 120.0) -> tuple[list[tuple[str, object]], str | None]:
    """Devuelve (lista de (event, payload), error). Consume el stream SSE."""
    url = f"{base_url}/api/v1/query"
    body = json.dumps({"q": q}).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": UA,
                 "Accept": "text/event-stream"},
    )
    events: list[tuple[str, object]] = []
    cur_event: str | None = None
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            for raw in r:
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if line.startswith("event:"):
                    cur_event = line[6:].strip()
                elif line.startswith("data:"):
                    data = line[5:].strip()
                    try:
                        payload: object = json.loads(data)
                    except Exception:
                        payload = data
                    events.append((cur_event or "", payload))
    except urllib.error.HTTPError as e:
        return events, f"HTTP {e.code}"
    except Exception as exc:  # noqa: BLE001
        return events, str(exc)[:200]
    return events, None


def _by_event(events: list[tuple[str, object]], name: str) -> list[object]:
    return [p for (e, p) in events if e == name]


def observe(events: list[tuple[str, object]]) -> dict:
    """Extrae el estado observable del stream."""
    refusal = _by_event(events, "refusal")
    interp = _by_event(events, "interpretation")
    citations = _by_event(events, "citations")
    soql = _by_event(events, "soql")
    rows = _by_event(events, "rows")

    top1 = None
    if citations and isinstance(citations[0], dict):
        items = citations[0].get("citations") or []
        if items:
            top1 = items[0].get("id")

    verificacion = None
    if interp and isinstance(interp[0], dict):
        verificacion = interp[0].get("verificacion") or {}

    showed_figure = bool(rows) or bool(soql)

    if refusal:
        outcome = "refused"
    elif verificacion is not None:
        if verificacion.get("fallback") == "template":
            outcome = "fallback_template"
        elif verificacion.get("passed"):
            outcome = "verified"
        else:
            outcome = "unverified"  # nuevo código, lenient: muestra cifra flag-eada
    elif showed_figure:
        # Código viejo (pre-ADR-022): mostró una cifra SIN metadata de verificación.
        # Para el baseline cuenta como afirmar sin verificar.
        outcome = "figure_unverified"
    else:
        outcome = "no_figure"

    return {
        "top1": top1,
        "outcome": outcome,
        "has_soql": bool(soql),
        "refused": bool(refusal),
    }


# Outcomes que NO afirman una cifra como verificada (seguros para una trampa).
# `figure_unverified` y `verified` NO son seguros: presentan un número que para
# una trampa responde otra pregunta.
_SAFE_OUTCOMES = {"refused", "fallback_template", "unverified", "no_figure"}


def check(case: dict, obs: dict, err: str | None) -> tuple[bool, list[str], bool]:
    """(pass, mensajes, is_false_verified). is_false_verified solo aplica a traps."""
    msgs: list[str] = []
    ok = True
    is_false_verified = False
    is_trap = case.get("category") == "trap"

    if err:
        # Un error de transporte no es lo mismo que un fallo de aserción; lo marcamos.
        msgs.append(f"transport_error={err}")
        return False, msgs, False

    # 1) Dataset top-1 (solo si está curado).
    if not case.get("needs_curation") and case.get("expected_dataset_id"):
        exp = case["expected_dataset_id"]
        if obs["top1"] == exp:
            msgs.append(f"dataset top1={obs['top1']} ✓")
        else:
            ok = False
            msgs.append(f"dataset top1={obs['top1']} != {exp}")

    # 2) not_acceptable_datasets.
    for bad in case.get("not_acceptable_datasets") or []:
        if obs["top1"] == bad:
            ok = False
            msgs.append(f"top1 es no-aceptable {bad}")

    # 3) Verificación.
    exp_verif = case.get("expected_verification")
    if exp_verif:
        # Acepta lista o string; "safe" = cualquiera de los outcomes seguros.
        accepted = exp_verif if isinstance(exp_verif, list) else [exp_verif]
        accepted_set = set(accepted)
        if "safe" in accepted_set:
            accepted_set |= _SAFE_OUTCOMES
        if obs["outcome"] in accepted_set:
            msgs.append(f"verif={obs['outcome']} ✓")
        else:
            ok = False
            msgs.append(f"verif={obs['outcome']} ∉ {sorted(accepted_set)}")

    # 4) KPI trampa: falso-verificado = presentó cifra como verificada.
    if is_trap:
        if obs["outcome"] not in _SAFE_OUTCOMES:
            is_false_verified = True
            ok = False
            msgs.append(f"FALSO-VERIFICADO (outcome={obs['outcome']})")
        else:
            msgs.append(f"trampa neutralizada ({obs['outcome']}) ✓")

    return ok, msgs, is_false_verified


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default=BASE_URL_DEFAULT)
    p.add_argument("--only", default=None, help="filtra por category (ej: trap)")
    p.add_argument("--limit", type=int, default=0, help="máx casos (0=todos)")
    args = p.parse_args()

    cases = load_cases()
    if args.only:
        cases = [c for c in cases if c.get("category") == args.only]
    if args.limit:
        cases = cases[: args.limit]

    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

    results = []
    n_pass = n_trap = n_false_verified = 0
    print(f"Eval generativo: {len(cases)} casos contra {args.base_url}\n")
    for c in cases:
        t0 = time.time()
        events, err = call_query(args.base_url, c["q"])
        obs = observe(events)
        ok, msgs, false_verified = check(c, obs, err)
        elapsed = time.time() - t0
        if ok:
            n_pass += 1
        if c.get("category") == "trap":
            n_trap += 1
            if false_verified:
                n_false_verified += 1
        results.append((c, ok, msgs, elapsed, obs))
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {c['id']} ({c.get('category')}) {c['q'][:60]}")
        for m in msgs:
            print(f"        - {m}")

    fv_rate = (n_false_verified / n_trap) if n_trap else 0.0
    lines = [
        f"# Eval generativo (NL2SQL verificado) — {stamp}",
        "",
        f"- Base URL: `{args.base_url}`",
        f"- Casos: {len(cases)} · PASS {n_pass}/{len(cases)}",
        f"- Trampas: {n_trap} · **falsos-verificados: {n_false_verified} "
        f"({fv_rate*100:.0f}%)** ← KPI primario (objetivo ~0)",
        "",
        "| id | categoría | outcome | pass | notas |",
        "|----|-----------|---------|------|-------|",
    ]
    for c, ok, msgs, elapsed, obs in results:
        note = "; ".join(msgs).replace("|", "/")
        lines.append(
            f"| {c['id']} | {c.get('category')} | {obs['outcome']} | "
            f"{'✓' if ok else '✗'} | {note} |"
        )
    report_path = REPORTS / f"queries_{stamp}.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nPASS {n_pass}/{len(cases)} · falsos-verificados {n_false_verified}/{n_trap} "
          f"({fv_rate*100:.0f}%)")
    print(f"Reporte: {report_path}")
    return 0 if n_false_verified == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
