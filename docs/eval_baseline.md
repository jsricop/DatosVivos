# Eval baseline — Fase 0 (2026-05-23)

Este documento congela el estado del pipeline `/api/v1/query` ANTES de empezar Fase 1 del audit top-down. Cada PR posterior compara su delta contra estos números.

## Cómo se generó

```bash
EVAL_BASE_URL=https://datosvivos.co .venv/bin/python scripts/run_eval.py
```

- **Base URL**: `https://datosvivos.co` (producción)
- **Golden set**: `eval/golden_queries.yaml` (33 queries — 30 de `data/journey_runs/journey_final.json` + 3 known-bad)
- **Reporte JSON**: `eval/reports/2026-05-23T02-41-56.json`
- **Reporte MD**: `eval/reports/2026-05-23T02-41-56.md`
- **Stack en VM**: commit `dd8d644` (PR #30 mergeado), migration 001 aplicada, `LLM_BACKEND=ollama` con `OLLAMA_NUM_PARALLEL=2`.

## Métricas base

| Métrica | Baseline | Target post-audit | Brecha |
|---|---:|---:|---:|
| `accuracy@1` (datasets curados) | **0.67** (2/3) | ≥ 0.90 | +23 pts |
| `intent_accuracy` | **0.45** (15/33) | ≥ 0.90 | +45 pts |
| `forbidden_dataset_hits` | **0** | 0 | OK |
| `hallucination_rate` | **0.06** (2/33) | < 0.05 | -1 pt |
| `p50_latency_s` | **31.1** | ≤ 10 | **-21s** |
| `p95_latency_s` | **147.9** | ≤ 10 | **-138s** |

## Hallazgos clave

### 1. El bug "Estudiantes Bogotá → UPTC" ya no aparece en producción
Queries `q090..q092` (los 3 casos known_bad capturados de telemetría real) devolvieron datasets distintos a UPTC:
- q090 `¿Cuántos estudiantes hay en Bogotá?` → `96hn-dzkr` (no UPTC `nxxq-mwbf`).
- q091 `¿Cuántos estudiantes hay en Antioquia?` → `u798-xnjg`.
- q092 `Estudiantes universidades públicas de Boyacá` → `ytq7-fiqn`.

`forbidden_dataset_hits = 0` confirma que la mitigación de PR #29 (penalty por entity de otro territorio + omisión de dashboard) está activa. **Pendiente validar manualmente** que los datasets retornados sean los semánticamente correctos (SED Bogotá, SED Antioquia, dataset Boyacá).

### 2. Latencia es el peor problema funcional
- p95 = 148s (objetivo 10s). 9/33 queries (27%) tardaron >60s. 5/33 (15%) >90s.
- Las queries lentas son las que disparan `comparative` o `cross_source` con LLM streaming completo.
- Ollama 7B CPU-only no soporta esta carga; concurrencia 2 con `OLLAMA_NUM_PARALLEL=2` no es suficiente para queries que internamente hacen 2 LLM calls (intent + narrative).

Implicación: la Fase 1 (chips deterministas) debería REDUCIR carga LLM por query porque elimina la necesidad de re-ranking + intent classification para el path principal. Si chips funciona, p95 debería bajar a 5-20s.

### 3. Intent classifier desalineado con golden set
El sistema solo emite 5 etiquetas (`comparative=17`, `temporal=8`, `search=4`, `cross_source=3`, `descriptive=1`). El golden usa una taxonomía más fina (incluye `count`, `count_in`, `list`, `aggregate`). El mismatch del 55% **no significa que el clasificador esté roto** — significa que las dos taxonomías no se hablan.

Implicación: la Fase 1 (chips) introduce un campo TIPO con 5 opciones (Cuántos, Comparar, Ranking, Tendencia, Mapa) que **reemplaza** este eje. Después del pivote, `intent_accuracy` debería medirse contra TIPO marcado por el usuario, no contra el clasificador embeddings.

### 4. Adversariales pasan cuando deberían rechazar
Las 3 queries adversariales (q028 "Datos", q029 "Información sobre Colombia", q030 "Quiero saber sobre Ecuador") devuelven dataset arbitrario en lugar de pedir refinamiento o avisar fuera de cobertura. El sistema no tiene noción de "rechazo razonado".

Implicación: en Fase 1 chips, si el usuario no marca ningún chip y solo escribe texto vago, la UI debe sugerir marcar chips antes de buscar. La rejection lógica vive en frontend.

### 5. Hallucinations bajas pero presentes
2/33 queries dispararon `narrative_correction` (q004 vacunación, q023 ranking inversión social). El validator `_validate_numbers` está funcionando — la cifra inventada no llega al usuario. Pero la fuente del problema (LLM proponiendo números fuera del whitelist) persiste.

### 6. Catálogo de datasets emitidos
Los 33 queries tocaron ~30 datasets distintos. Algunos coincidencias notables:
- `kgyi-qc7j` aparece como top-1 en **dos queries distintas** (q016 Inflación, q017 PIB) — sospechoso, puede ser un dataset macro económico que el embedding atrae sin discriminar tema preciso.
- `4hrb-y62g` (instituciones educación superior por dpto) aparece en q008 y q022 — consistente, está bien.
- `ji8i-4anb` (matrícula escolar) aparece en q009 (correcto) y q027 (Cambio anual inflación — **claramente mismatch**).

Estos casos refuerzan que el retrieval ML híbrido tiene falsos positivos consistentes — confirma la decisión de pivote a chips.

## Implicaciones para Fase 1

| Decisión | Justificación |
|---|---|
| **Mantener el plan: chips primero** | Los hallazgos 1-6 muestran que el problema raíz es retrieval open-text sobre un catálogo no curado. Chips deterministas atacan exactamente eso. |
| **Adelantar curación de metadata** | Sin `tema`, `jurisdiccion_geo_codes`, `socrata_tags` por dataset, los chips devuelven listas vacías o sucias. Es el prerequisito de Fase 1. |
| **Reducir LLM calls por query** | p95=148s exige bajar la carga. En el path chips, no hay rerank LLM ni intent classifier — solo narrative final. Eso debería bajar p95 al rango 10-30s. |
| **Validar manualmente q090-q092** | Antes de declarar el bug Bogotá resuelto, confirmar que `96hn-dzkr` y `u798-xnjg` son los datasets correctos (SED locales). Curar el golden con `expected_dataset_id`. |

## Riesgos a vigilar

| Riesgo | Mitigación |
|---|---|
| El baseline tiene N=33; muestra pequeña, métricas ruidosas | Ampliar golden a 50+ queries a medida que descubramos casos en telemetría real (`failure_type` ahora se loggea). |
| `accuracy@1` solo aplica sobre 3 queries curadas (Bogotá no aplica todavía) | Cada PR de Fase 1 debe sacar ≥3 queries de `needs_curation: true`. |
| p95 incluye queries con narrativa LLM completa que en Fase 1 ya no van a correr | Mantener el eval harness midiendo `done_emitted_s` separado de `dashboard_emitted_s` para no comparar peras con manzanas post-pivote. |

## Next step

Cerrar Fase 0 y arrancar **Fase 1 prerequisito: curación de metadata del catálogo** (ver `merry-puzzling-pie.md` sección Fase 1). Primer entregable: script `scripts/curate_chip_metadata.py` + migration `002_chip_metadata.sql`.
