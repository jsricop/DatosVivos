"""Pruebas end-to-end actuando como ciudadano real.

30 preguntas tipadas a la batería del Analyzer con Ollama real.
Reporta honestamente: intent clasificado, datasets recuperados, narrativa,
si se activó Tier 2 o Tier 3, y compara contra un criterio esperable.

No es un test pytest — es un script de evaluación cualitativa exploratoria.
El objetivo es medir el impacto de cada mitigación sobre el conjunto
representativo, no validar contra valores fijos (los datos del mundo cambian).

Categorías cubiertas (10):
  1. Geo simple (golden assertions DIVIPOLA)
  2. Salud pública
  3. Educación
  4. Contratación pública
  5. Seguridad ciudadana
  6. Economía
  7. Ambiente / clima
  8. Comparativas geográficas
  9. Temporales / histórico
 10. Adversariales / vagas (detectar alucinaciones)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from ai_engine.analyzer import Analyzer
from ai_engine.intent_classifier import IntentClassifier
from ai_engine.llm_backend import get_backend
from ai_engine.vector_index import VectorIndex


@dataclass(frozen=True)
class JourneyQuestion:
    """Una pregunta + criterio cualitativo de éxito.

    Campos opcionales (`expected_keyword_in_narrative`, `forbidden_in_narrative`,
    `expected_dataset_hint`) son señales para evaluar — no asserts.
    """

    category: str
    question: str
    # Una palabra clave que esperaríamos ver en la narrativa si el agente acertó.
    expected_keyword_in_narrative: str | None = None
    # Lista de palabras que NO deberían aparecer (alucinaciones típicas).
    forbidden_in_narrative: tuple[str, ...] = field(default_factory=tuple)
    # Sub-string que esperaríamos ver en al menos un dataset_id recuperado o
    # en la metadata (entity, name) — útil para detectar retrieval correcto.
    expected_dataset_hint: str | None = None


QUESTIONS: tuple[JourneyQuestion, ...] = (
    # 1. Geo simple — golden DIVIPOLA
    JourneyQuestion(
        category="geo_simple",
        question="¿Cuántos municipios tiene Antioquia?",
        expected_keyword_in_narrative="125",
        forbidden_in_narrative=("pensionados", "Ecuador", "Venezuela"),
        expected_dataset_hint="divipola",
    ),
    JourneyQuestion(
        category="geo_simple",
        question="¿Cuántos municipios hay en Cundinamarca?",
        forbidden_in_narrative=("Ecuador",),
        expected_dataset_hint="divipola",
    ),
    JourneyQuestion(
        category="geo_simple",
        question="Cuántos departamentos tiene Colombia",
        expected_keyword_in_narrative="33",  # 32 dptos + Bogotá D.C.
        forbidden_in_narrative=("Ecuador", "Perú"),
    ),
    # 2. Salud pública
    JourneyQuestion(
        category="salud",
        question="Vacunación contra COVID-19 en Colombia",
        forbidden_in_narrative=("Ecuador",),
        expected_dataset_hint="vacun",
    ),
    JourneyQuestion(
        category="salud",
        question="Casos de dengue por departamento",
        forbidden_in_narrative=("Ecuador", "tráfico"),
        expected_dataset_hint="dengue",
    ),
    JourneyQuestion(
        category="salud",
        question="Mortalidad materna en zonas rurales",
        forbidden_in_narrative=("Ecuador",),
    ),
    # 3. Educación
    JourneyQuestion(
        category="educacion",
        question="Datos sobre educación superior en Colombia",
        forbidden_in_narrative=("Ecuador",),
        expected_dataset_hint="educa",
    ),
    JourneyQuestion(
        category="educacion",
        question="Cuántas instituciones de educación superior hay por departamento",
        forbidden_in_narrative=("Ecuador",),
    ),
    JourneyQuestion(
        category="educacion",
        question="Matrícula escolar en básica primaria",
        forbidden_in_narrative=("Ecuador",),
        expected_dataset_hint="matr",
    ),
    # 4. Contratación pública
    JourneyQuestion(
        category="contratacion",
        question="Contratos del Ministerio de Defensa Nacional",
        forbidden_in_narrative=("Ecuador",),
    ),
    JourneyQuestion(
        category="contratacion",
        question="Contratos de obra pública en Bogotá",
        forbidden_in_narrative=("Ecuador",),
    ),
    JourneyQuestion(
        category="contratacion",
        question="Adjudicaciones SECOP del último año",
        forbidden_in_narrative=("Ecuador",),
        expected_dataset_hint="secop",
    ),
    # 5. Seguridad
    JourneyQuestion(
        category="seguridad",
        question="Datos de homicidios en Bogotá",
        forbidden_in_narrative=("accidentes de tráfico", "tránsito", "Ecuador"),
        expected_dataset_hint="homici",
    ),
    JourneyQuestion(
        category="seguridad",
        question="Hurto a personas en Medellín",
        forbidden_in_narrative=("Ecuador",),
        expected_dataset_hint="hurto",
    ),
    JourneyQuestion(
        category="seguridad",
        question="Accidentes de tránsito con muertes",
        forbidden_in_narrative=("Ecuador",),
    ),
    # 6. Economía
    JourneyQuestion(
        category="economia",
        question="Inflación en Colombia",
        # Lo correcto sería IPC del DANE; NO PIB.
        forbidden_in_narrative=("PIB", "producto interno", "Ecuador"),
        expected_dataset_hint="ipc",
    ),
    JourneyQuestion(
        category="economia",
        question="PIB departamental",
        forbidden_in_narrative=("Ecuador",),
        expected_dataset_hint="pib",
    ),
    JourneyQuestion(
        category="economia",
        question="Tasa de desempleo por ciudad",
        forbidden_in_narrative=("Ecuador",),
        expected_dataset_hint="desem",
    ),
    # 7. Ambiente / clima
    JourneyQuestion(
        category="ambiente",
        question="Quiero datos sobre el clima",
        forbidden_in_narrative=("Ecuador",),
        expected_dataset_hint="ideam",
    ),
    JourneyQuestion(
        category="ambiente",
        question="Calidad del aire en Bogotá",
        forbidden_in_narrative=("Ecuador",),
    ),
    JourneyQuestion(
        category="ambiente",
        question="Deforestación en la Amazonía colombiana",
        forbidden_in_narrative=("Ecuador",),
    ),
    # 8. Comparativas geográficas
    JourneyQuestion(
        category="comparativa",
        question="Qué departamentos tienen más instituciones de educación superior",
        forbidden_in_narrative=("Ecuador",),
    ),
    JourneyQuestion(
        category="comparativa",
        question="Ranking de municipios por inversión social",
        forbidden_in_narrative=("Ecuador",),
    ),
    JourneyQuestion(
        category="comparativa",
        question="Departamentos con mayor cobertura de salud",
        forbidden_in_narrative=("Ecuador",),
    ),
    # 9. Temporales
    JourneyQuestion(
        category="temporal",
        question="Evolución de la población colombiana",
        forbidden_in_narrative=("Ecuador",),
    ),
    JourneyQuestion(
        category="temporal",
        question="Histórico de homicidios en los últimos 10 años",
        forbidden_in_narrative=("accidentes de tráfico", "Ecuador"),
    ),
    JourneyQuestion(
        category="temporal",
        question="Cambio anual de la inflación en Colombia",
        forbidden_in_narrative=("PIB", "Ecuador"),
    ),
    # 10. Adversariales / vagas (detectar alucinaciones / sobre-respuesta)
    JourneyQuestion(
        category="adversarial",
        question="Datos",
        forbidden_in_narrative=("Ecuador",),
    ),
    JourneyQuestion(
        category="adversarial",
        question="Información sobre Colombia",
        forbidden_in_narrative=("Ecuador", "Venezuela"),
    ),
    JourneyQuestion(
        category="adversarial",
        # El catálogo es colombiano; el agente NO debe inventar datos de Ecuador.
        question="Quiero saber sobre Ecuador",
        # Aceptable: "no encontramos datos sobre Ecuador en datos.gov.co".
        # Inaceptable: inventar datos ecuatorianos.
        forbidden_in_narrative=("Quito", "sucre", "Yasuní"),
    ),
)


def fmt_section(title: str) -> str:
    return f"\n{'═' * 78}\n  {title}\n{'═' * 78}"


@dataclass
class QuestionResult:
    """Resultado evaluado de una pregunta."""

    idx: int
    category: str
    question: str
    elapsed_s: float
    intent: str
    datasets_used: list[str]
    soql_executed: str | None
    rows_count: int
    narrative: str
    # Referencias citables (id, name, entity, url) — JSON-serializables.
    references: list[dict]
    # Líneas de "Datos verificados" calculadas por pandas (vacío si no se ejecutó SoQL).
    stats_summary_lines: list[str]
    # Cuántas oraciones censuradas por `_validate_numbers` (cifras alucinadas).
    censored_count: int
    # Evaluación binaria simple para reporte:
    keyword_hit: bool | None  # None si la pregunta no tiene expected_keyword
    forbidden_hit: list[str]  # palabras prohibidas que SÍ aparecieron
    hint_in_metadata: bool | None  # None si no había hint


def evaluate(
    qq: JourneyQuestion,
    narrative: str,
    datasets_used: list[str],
    stats_lines: list[str] | None = None,
) -> tuple[bool | None, list[str], bool | None]:
    """Aplica los criterios cualitativos de qq sobre narrativa + cifras verificadas."""
    narrative_lower = (narrative or "").lower()
    # Las cifras verificadas viven en stats_lines (bloque determinista).
    full_text_lower = narrative_lower + "\n" + "\n".join(stats_lines or []).lower()

    keyword_hit: bool | None = None
    if qq.expected_keyword_in_narrative:
        keyword_hit = qq.expected_keyword_in_narrative.lower() in full_text_lower

    forbidden_hit = [
        w for w in qq.forbidden_in_narrative if w.lower() in narrative_lower
    ]

    hint_in_metadata: bool | None = None
    if qq.expected_dataset_hint:
        hint = qq.expected_dataset_hint.lower()
        hint_in_metadata = (
            any(hint in did.lower() for did in datasets_used)
            or hint in full_text_lower
        )

    return keyword_hit, forbidden_hit, hint_in_metadata


async def run_journey(output_json: Path | None = None, limit: int | None = None) -> None:
    print("Cargando motor (vector index + intent classifier + LLM backend)...")
    t0 = time.time()
    analyzer = Analyzer(
        vector_index=VectorIndex.load(),
        intent_classifier=IntentClassifier(),
        llm_backend=get_backend(),
        top_k_datasets=5,
    )
    print(f"Listo en {time.time() - t0:.1f}s. LLM backend: {type(analyzer.llm).__name__}")

    questions = QUESTIONS if not limit else QUESTIONS[:limit]
    results: list[QuestionResult] = []

    for i, qq in enumerate(questions, 1):
        print(fmt_section(f"PREGUNTA {i}/{len(questions)} [{qq.category}]: {qq.question}"))
        t_start = time.time()
        try:
            result = await asyncio.wait_for(analyzer.analyze(qq.question), timeout=240)
        except asyncio.TimeoutError:
            print("  ⏱️  TIMEOUT (>240s) — saltando")
            continue
        except Exception as e:
            print(f"  ❌ ERROR: {type(e).__name__}: {e}")
            continue
        elapsed = time.time() - t_start

        narrative = (result.narrative or "").strip()
        stats_summary_lines: list[str] = []
        stats = getattr(result, "statistics", None)
        if stats is not None:
            stats_summary_lines = list(stats.summary_lines)
        kw, forbidden, hint = evaluate(
            qq, narrative, result.datasets_used, stats_summary_lines
        )

        # Conteo de censuras: oraciones reemplazadas por el validador.
        censored_count = narrative.count(
            "no verificable"
        ) + narrative.lower().count("consulta el bloque de datos verificados")

        refs_serializable = [
            {
                "id": r.id,
                "name": r.name,
                "entity": r.entity,
                "url": r.url,
                "api_url": r.api_url,
            }
            for r in (getattr(result, "dataset_references", []) or [])
        ]

        qr = QuestionResult(
            idx=i,
            category=qq.category,
            question=qq.question,
            elapsed_s=elapsed,
            intent=result.intent,
            datasets_used=list(result.datasets_used),
            soql_executed=result.soql_executed,
            rows_count=len(result.rows or []),
            narrative=narrative,
            references=refs_serializable,
            stats_summary_lines=stats_summary_lines,
            censored_count=censored_count,
            keyword_hit=kw,
            forbidden_hit=forbidden,
            hint_in_metadata=hint,
        )
        results.append(qr)

        print(f"  ⏱️  {elapsed:.1f}s")
        print(f"  🎯 Intent:               {result.intent}")
        print(f"  📂 Datasets recuperados: {len(result.datasets_used)} → {result.datasets_used[:5]}")
        refs = getattr(result, "dataset_references", []) or []
        if refs:
            print("  🔗 Enlaces (fuentes verificables):")
            for r in refs[:3]:
                print(f"     - {r.name} → {r.url}")
        if result.soql_executed:
            print(f"  🔧 SoQL ejecutada:       {result.soql_executed}")
        if result.rows:
            print(f"  📊 Filas devueltas:      {len(result.rows)} (primera: {result.rows[0]!r})")
        if stats_summary_lines:
            print("  ✅ Cifras verificadas (pandas):")
            for line in stats_summary_lines[:6]:
                print(f"     • {line}")
        if censored_count > 0:
            print(f"  🛡️  Oraciones censuradas por validador: {censored_count}")
        if narrative:
            preview = narrative[:400] + ("..." if len(narrative) > 400 else "")
            print(f"  💬 Narrativa:\n     {preview}")
        else:
            print("  💬 (sin narrativa)")
        # Evaluación
        verdict_parts = []
        if kw is True:
            verdict_parts.append(f"✅ keyword '{qq.expected_keyword_in_narrative}' presente")
        elif kw is False:
            verdict_parts.append(f"❌ keyword '{qq.expected_keyword_in_narrative}' ausente")
        if forbidden:
            verdict_parts.append(f"❌ prohibidas presentes: {forbidden}")
        if hint is True:
            verdict_parts.append(f"✅ hint '{qq.expected_dataset_hint}' detectado")
        elif hint is False:
            verdict_parts.append(f"⚠️  hint '{qq.expected_dataset_hint}' no detectado")
        if verdict_parts:
            print("  🧪 Evaluación: " + " | ".join(verdict_parts))

    # Resumen agregado
    print(fmt_section("RESUMEN AGREGADO"))
    total = len(results)
    if not total:
        print("Sin resultados.")
        return

    kw_evaluated = [r for r in results if r.keyword_hit is not None]
    kw_pass = sum(1 for r in kw_evaluated if r.keyword_hit)

    forbidden_clean = sum(1 for r in results if not r.forbidden_hit)
    forbidden_dirty = total - forbidden_clean

    hint_evaluated = [r for r in results if r.hint_in_metadata is not None]
    hint_pass = sum(1 for r in hint_evaluated if r.hint_in_metadata)

    soql_runs = sum(1 for r in results if r.soql_executed)
    with_stats = sum(1 for r in results if r.stats_summary_lines)
    total_censored = sum(r.censored_count for r in results)

    print(f"Total preguntas:                {total}")
    print(f"Tiempo total:                   {sum(r.elapsed_s for r in results):.1f}s")
    print(
        f"Keyword esperada presente:      {kw_pass}/{len(kw_evaluated)}"
        if kw_evaluated
        else "Keyword esperada presente:      (sin criterios)"
    )
    print(f"Sin palabras prohibidas:        {forbidden_clean}/{total}")
    print(
        f"Hint dataset detectado:         {hint_pass}/{len(hint_evaluated)}"
        if hint_evaluated
        else "Hint dataset detectado:         (sin criterios)"
    )
    print(f"SoQL ejecutado contra Socrata:  {soql_runs}/{total}")
    print(f"Con cifras verificadas pandas:  {with_stats}/{total}")
    print(f"Oraciones censuradas (total):   {total_censored}")

    by_category: dict[str, list[QuestionResult]] = {}
    for r in results:
        by_category.setdefault(r.category, []).append(r)
    print("\nPor categoría:")
    for cat, rs in sorted(by_category.items()):
        forbidden_dirty_cat = sum(1 for r in rs if r.forbidden_hit)
        print(f"  {cat:15s}  n={len(rs):2d}  alucinaciones={forbidden_dirty_cat}")

    if forbidden_dirty:
        print("\nPreguntas con palabras prohibidas (alucinaciones detectadas):")
        for r in results:
            if r.forbidden_hit:
                print(f"  [{r.idx:2d}] {r.question!r}  →  {r.forbidden_hit}")

    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        with output_json.open("w", encoding="utf-8") as fh:
            json.dump(
                [r.__dict__ for r in results],
                fh,
                ensure_ascii=False,
                indent=2,
            )
        print(f"\n📝 Resultados JSON: {output_json}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="User journey test sobre 30 preguntas reales.")
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path JSON para guardar los resultados (opcional).",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limitar a las primeras N preguntas (para iteraciones rápidas).",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_journey(output_json=args.output, limit=args.limit))
