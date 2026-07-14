"""Corre las 50 preguntas ciudadanas contra producción y registra la
"respuesta entregada" en detalle: chips mapeados, dataset elegido, artefacto
que renderiza la UI, muestra de filas, tiempos y degradaciones.

Uso:  python eval/ciudadano/correr_ciclo.py [ciclo]   (default: 1)
Salida: eval/ciudadano/entregado_ciclo{N}.yaml
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

import yaml

BASE = "https://datosvivos.co/api/v1"
AQUI = Path(__file__).parent


def post(path: str, body: dict, timeout: int = 90) -> dict:
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "User-Agent": "DatosVivos-eval/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def artefacto_ui(tipo: str | None, rows: list) -> str:
    """Qué renderiza ChipsResultPanel con esta respuesta (espejo del frontend)."""
    if not rows:
        return "panel 'Sin datos'"
    if tipo == "Cuántos":
        return "KPI grande + nota 'cuenta registros, no suma'"
    if tipo in ("Comparar", "Ranking"):
        return "barras horizontales (categoria × valor)"
    if tipo == "Tendencia":
        return "línea (periodo × n)"
    if tipo == "Mapa":
        numericas = sum(
            1 for r in rows
            if str(r.get("region", "")).strip().isdigit()
        )
        if numericas < len(rows) / 2:
            return "barras por región (fallback: regiones por nombre, sin códigos)"
        return "mapa choropleth por departamento"
    return "tabla cruda"


def correr(pregunta: str) -> dict:
    reg: dict = {}
    try:
        t0 = time.time()
        chips = post("/chips/from-nl", {"q": pregunta})
        reg["chips"] = {k: chips.get(k) for k in
                        ("tema", "tipo", "territorio", "entidad", "refinador")
                        if chips.get(k)}
        reg["ms_interpretacion"] = round((time.time() - t0) * 1000)

        t1 = time.time()
        cand = post("/query/chips", reg["chips"])
        reg["subset"] = cand.get("total_in_subset")
        chosen = cand.get("chosen_dataset_id")
        reg["candidatos_top3"] = [
            f"{c['dataset_id']} · {c['name'][:70]}"
            for c in (cand.get("candidates") or [])[:3]
        ]
        if not chosen:
            reg["entregado"] = (
                f"SIN RESPUESTA EJECUTADA — mensaje del sistema: "
                f"{cand.get('message') or '(sin mensaje)'}"
            )
            return reg
        nombre = next((c["name"] for c in cand.get("candidates") or []
                       if c["dataset_id"] == chosen), "?")
        reg["dataset_elegido"] = f"{chosen} · {nombre[:80]}"

        tipo = reg["chips"].get("tipo") or "Cuántos"
        # Espejo del frontend (ADR-024): la pregunta habilita el auto-filtro
        # y el territorio el recorte territorial sobre datasets nacionales.
        ex = post("/query/chips/execute", {
            "dataset_id": chosen, "tipo": tipo,
            "territorio": reg["chips"].get("territorio"),
            "pregunta": pregunta,
        })
        reg["ms_ejecucion"] = round((time.time() - t1) * 1000)
        rows = ex.get("rows") or []
        reg["consulta"] = (ex.get("soql") or "")[:140]
        if ex.get("error"):
            reg["entregado"] = f"ERROR HONESTO: {ex['error']}"
            return reg
        reg["artefacto"] = artefacto_ui(tipo, rows)
        reg["filas"] = len(rows)
        reg["muestra"] = [
            {k: v for k, v in r.items()} for r in rows[:3]
        ]
        origen = "bodega Parquet local" if "{src}" in (ex.get("soql") or "") \
            else "consulta en vivo"
        extras = []
        if ex.get("filters_applied"):
            extras.append("filtrado: " + ", ".join(
                f"{f['col']}={f['value']}" for f in ex["filters_applied"]))
        if ex.get("unfiltered_total") is not None:
            extras.append(f"de {ex['unfiltered_total']} sin filtro")
        if ex.get("row_unit"):
            extras.append(f"unidad: {ex['row_unit']}")
        reg["entregado"] = (
            f"{reg['artefacto']} · {len(rows)} fila(s) · {origen} · "
            + (" · ".join(extras) + " · " if extras else "")
            + "con nota 'cifra verificada' + nombre del dataset + toggle SoQL"
        )
    except Exception as exc:  # noqa: BLE001
        reg["entregado"] = f"EXCEPCIÓN DE TRANSPORTE: {exc}"
    return reg


def main() -> None:
    ciclo = sys.argv[1] if len(sys.argv) > 1 else "1"
    data = yaml.safe_load((AQUI / "preguntas_50.yaml").read_text())
    salida = []
    for p in data["preguntas"]:
        print(f"{p['id']}: {p['q'][:60]}...", flush=True)
        reg = {"id": p["id"], "q": p["q"], **correr(p["q"])}
        salida.append(reg)
    out = AQUI / f"entregado_ciclo{ciclo}.yaml"
    out.write_text(yaml.safe_dump(
        {"ciclo": int(ciclo), "resultados": salida},
        allow_unicode=True, sort_keys=False, width=100))
    con_datos = sum(1 for r in salida
                    if r.get("filas") and not str(r["entregado"]).startswith(("ERROR", "SIN", "EXCEPCIÓN")))
    print(f"\n{out.name}: {con_datos}/{len(salida)} con artefacto y datos")


if __name__ == "__main__":
    main()
