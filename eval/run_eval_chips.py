"""Eval harness para el golden set de chips (Hito 1).

Lee `eval/golden_chips.yaml`, llama POST /api/v1/query/chips/execute por
cada caso, y reporta pass/fail por aserción + tabla resumen.

Uso:
    python eval/run_eval_chips.py
    python eval/run_eval_chips.py --base-url https://datosvivos.co
    python eval/run_eval_chips.py --case-id subsidios_vivienda_total

Salida: stdout + `eval/reports/chips_<fecha>.md`.
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
GOLDEN = Path(__file__).parent / "golden_chips.yaml"
REPORTS = Path(__file__).parent / "reports"
UA = "DatosVivos/run_eval_chips"


def load_cases() -> list[dict]:
    with open(GOLDEN, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("cases") or []


def call_execute(
    base_url: str, dataset_id: str, tipo: str, timeout: float = 90.0
) -> tuple[int, dict | None, str | None]:
    """(http_status, json_response_or_None, error_msg_or_None)."""
    url = f"{base_url}/api/v1/query/chips/execute"
    body = json.dumps({"dataset_id": dataset_id, "tipo": tipo}).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": UA},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r), None
    except urllib.error.HTTPError as e:
        try:
            body_txt = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            body_txt = ""
        return e.code, None, body_txt
    except Exception as exc:  # noqa: BLE001
        return 0, None, str(exc)[:200]


def check(case: dict, status: int, resp: dict | None, err: str | None) -> tuple[bool, list[str]]:
    """Devuelve (pass, lista_de_messages)."""
    expect = case.get("expect") or {}
    msgs: list[str] = []
    ok = True

    # 1) http_status esperado.
    exp_status = expect.get("http_status")
    if exp_status:
        if status != exp_status:
            ok = False
            msgs.append(f"http_status {status} != {exp_status}")
        else:
            msgs.append(f"http_status={status} ✓")
        return ok, msgs  # ya no aplica el resto

    # Otras aserciones requieren JSON 200 OK.
    if status != 200 or not resp:
        ok = False
        msgs.append(f"http_status={status} no-json err={err!r}")
        return ok, msgs

    # 2) error_substring (espera response.error contenga substring).
    es = expect.get("error_substring")
    if es:
        actual = (resp.get("error") or "").lower()
        if es.lower() in actual:
            msgs.append(f"error contiene {es!r} ✓")
        else:
            ok = False
            msgs.append(f"error={resp.get('error')!r} no contiene {es!r}")
        return ok, msgs

    # 3) row_count exacto o rango.
    rc = resp.get("row_count")
    if "row_count" in expect:
        if rc != expect["row_count"]:
            ok = False
            msgs.append(f"row_count {rc} != {expect['row_count']}")
        else:
            msgs.append(f"row_count={rc} ✓")
    if "row_count_min" in expect or "row_count_max" in expect:
        lo = expect.get("row_count_min", 0)
        hi = expect.get("row_count_max", 10**9)
        if rc is None or not (lo <= rc <= hi):
            ok = False
            msgs.append(f"row_count {rc} fuera de [{lo},{hi}]")
        else:
            msgs.append(f"row_count={rc} en [{lo},{hi}] ✓")

    # 4) first_row_must_contain.
    frc = expect.get("first_row_must_contain")
    if frc:
        rows = resp.get("rows") or []
        if not rows:
            ok = False
            msgs.append("rows vacíos, esperaba primer fila")
        else:
            first = rows[0]
            for k, v in frc.items():
                actual = first.get(k)
                if str(actual) != str(v):
                    ok = False
                    msgs.append(f"first_row.{k}={actual!r} != {v!r}")
                else:
                    msgs.append(f"first_row.{k}={actual} ✓")

    # 5) first_row_field_min: cifra >= threshold (tolerante a crecimiento).
    fmin = expect.get("first_row_field_min")
    if fmin:
        rows = resp.get("rows") or []
        if not rows:
            ok = False
            msgs.append("rows vacíos, esperaba primer fila")
        else:
            first = rows[0]
            for k, threshold in fmin.items():
                actual = first.get(k)
                try:
                    n = int(float(str(actual)))
                except (TypeError, ValueError):
                    ok = False
                    msgs.append(f"first_row.{k}={actual!r} no es número")
                    continue
                if n < threshold:
                    ok = False
                    msgs.append(f"first_row.{k}={n} < min {threshold}")
                else:
                    msgs.append(f"first_row.{k}={n} ≥ {threshold} ✓")

    return ok, msgs


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default=BASE_URL_DEFAULT)
    p.add_argument("--case-id", default=None,
                   help="Si se pasa, corre solo ese caso")
    args = p.parse_args()

    cases = load_cases()
    if args.case_id:
        cases = [c for c in cases if c.get("id") == args.case_id]
        if not cases:
            print(f"No encontré caso {args.case_id!r}")
            return 2

    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    report_path = REPORTS / f"chips_{stamp}.md"

    n_pass = n_fail = 0
    lines: list[str] = [
        f"# Eval chips path — {stamp}", "",
        f"Base URL: `{args.base_url}`", f"Casos: {len(cases)}", "",
        "| id | dataset | tipo | ms | resultado | notas |",
        "|---|---|---|---:|---|---|",
    ]
    for case in cases:
        t0 = time.time()
        status, resp, err = call_execute(
            args.base_url, case["dataset_id"], case["tipo"],
        )
        elapsed = int((time.time() - t0) * 1000)
        ok, msgs = check(case, status, resp, err)
        if ok:
            n_pass += 1
        else:
            n_fail += 1
        verdict = "✓" if ok else "✗"
        notes = " · ".join(msgs)
        lines.append(
            f"| `{case['id']}` | `{case['dataset_id']}` | {case['tipo']} | "
            f"{elapsed} | {verdict} | {notes} |"
        )
        print(f"  {verdict} {case['id']} ({elapsed}ms)")

    lines += [
        "",
        f"**Resumen:** {n_pass}/{len(cases)} pass · {n_fail} fail",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReporte: {report_path}")
    print(f"Resumen: {n_pass}/{len(cases)} pass · {n_fail} fail")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
