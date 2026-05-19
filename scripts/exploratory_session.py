"""Sesión exploratoria como usuario real — 12 preguntas FUERA del journey.

El journey de 30 preguntas (user_journey_test.py) es el benchmark
canónico. Este script complementa probando combinaciones nuevas que el
ciudadano podría hacer y que NO están en el set congelado.

Objetivos:
- Detectar gaps de retrieval/comparativa no cubiertos por el journey.
- Generar telemetría real (la app pasaría por el chat de Streamlit, pero
  acá usamos directamente Analyzer para tener trazas estructuradas).
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path

from ai_engine.analyzer import Analyzer
from ai_engine.intent_classifier import IntentClassifier
from ai_engine.llm_backend import get_backend
from ai_engine.vector_index import VectorIndex


@dataclass(frozen=True)
class ExploratoryQuestion:
    category: str
    question: str
    note: str  # qué esperamos observar


QUESTIONS: tuple[ExploratoryQuestion, ...] = (
    ExploratoryQuestion(
        "geo_count",
        "Cuántos hospitales hay en Cundinamarca",
        "geo+count; espera SoQL con cod_dpto='25'",
    ),
    ExploratoryQuestion(
        "ranking_explicit",
        "Top 10 ciudades con más homicidios",
        "ranking N=10; espera plantilla determinista GROUP BY+ORDER BY",
    ),
    ExploratoryQuestion(
        "vs_mpios",
        "Compara Medellín con Cali en seguridad",
        "vs entre 2 mpios; espera comparison_mode='vs' con cod_mpio IN",
    ),
    ExploratoryQuestion(
        "acronym",
        "Datos sobre el SISBÉN",
        "acrónimo Tier 1; espera retrieval relevante DPS/DNP",
    ),
    ExploratoryQuestion(
        "no_geo",
        "Calidad del aire",
        "temático sin geo; espera GeoResolver=None y retrieval IDEAM/SDA",
    ),
    ExploratoryQuestion(
        "geo_count_choco",
        "Cuántas instituciones de salud hay en Chocó",
        "geo+count en dpto periférico; espera cod_dpto='27'",
    ),
    ExploratoryQuestion(
        "ranking_implicit",
        "Top 5 municipios más poblados",
        "ranking implícito; espera plantilla con groupby cod_mpio",
    ),
    ExploratoryQuestion(
        "vs_mpios_economia",
        "Inflación en Bogotá vs Medellín",
        "vs entre 2 mpios; pregunta económica (no típica de SoQL filtrable)",
    ),
    ExploratoryQuestion(
        "vs_national",
        "Tasa de homicidios en Antioquia respecto al promedio nacional",
        "vs_national; espera detectar el patrón + target Antioquia + national",
    ),
    ExploratoryQuestion(
        "acronym_institution",
        "ICETEX créditos otorgados",
        "acrónimo + temático; espera retrieval de educación financiera",
    ),
    ExploratoryQuestion(
        "geo_count_mpio",
        "Pobreza en Quibdó",
        "geo a nivel mpio; espera SoQL con cod_mpio='27001'",
    ),
    ExploratoryQuestion(
        "thematic_no_geo",
        "Datos sobre el agua potable en zonas rurales",
        "temático complejo sin geo; ver si retrieval encuentra MVCT/IDEAM",
    ),
)


async def main(output_path: Path | None = None) -> None:
    print("Cargando motor...")
    t0 = time.time()
    analyzer = Analyzer(
        vector_index=VectorIndex.load(),
        intent_classifier=IntentClassifier(),
        llm_backend=get_backend(),
        top_k_datasets=5,
    )
    print(f"Listo en {time.time() - t0:.1f}s\n")

    results: list[dict] = []
    for i, q in enumerate(QUESTIONS, 1):
        print(f"\n{'═' * 78}\n  [{i:2d}/{len(QUESTIONS)}] [{q.category}] {q.question}\n  ➤ {q.note}\n{'═' * 78}")
        t_q = time.time()
        try:
            r = await asyncio.wait_for(analyzer.analyze(q.question), timeout=240)
        except asyncio.TimeoutError:
            print("  ⏱️  TIMEOUT (>240s)")
            continue
        except Exception as e:
            print(f"  ❌ ERROR: {type(e).__name__}: {e}")
            continue
        elapsed = time.time() - t_q

        geo = r.geo_context
        geo_str = "—"
        if geo:
            parts = []
            if geo.dpto_code:
                parts.append(f"dpto={geo.dpto_code}")
            if geo.mpio_code:
                parts.append(f"mpio={geo.mpio_code}")
            if geo.comparison_mode:
                parts.append(f"mode={geo.comparison_mode}")
            if geo.groupby:
                parts.append(f"gb={geo.groupby}")
            geo_str = " ".join(parts) if parts else "scope=" + geo.scope

        print(f"  ⏱️  {elapsed:.1f}s | intent={r.intent} | geo={geo_str}")
        print(f"  📂 datasets: {r.datasets_used[:3]}")
        if r.soql_executed:
            print(f"  🔧 soql: {r.soql_executed}")
        if r.statistics and r.statistics.summary_lines:
            print(f"  📊 verificadas: {r.statistics.summary_lines[0]}")
            if len(r.statistics.summary_lines) > 1:
                print(f"     {r.statistics.summary_lines[1][:160]}")
        # Narrativa (truncada)
        nar = (r.narrative or "").split("\n📊")[0].strip()  # solo el bloque LLM
        print(f"  💬 {nar[:240]}{'…' if len(nar) > 240 else ''}")

        results.append({
            "idx": i,
            "category": q.category,
            "question": q.question,
            "elapsed_s": round(elapsed, 1),
            "intent": r.intent,
            "geo_context": {
                "dpto_code": geo.dpto_code if geo else None,
                "mpio_code": geo.mpio_code if geo else None,
                "comparison_mode": geo.comparison_mode if geo else None,
                "groupby": geo.groupby if geo else None,
                "scope": geo.scope if geo else None,
            } if geo else None,
            "datasets_used": list(r.datasets_used),
            "soql_executed": r.soql_executed,
            "rows_count": len(r.rows or []),
            "stats_summary": list(r.statistics.summary_lines) if r.statistics else [],
            "narrative": nar,
        })

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n📝 Resultados JSON: {output_path}")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=Path("data/journey_runs/exploratory.json"))
    args = p.parse_args()
    asyncio.run(main(args.output))
