# ADR-015: Tiered LLM models por task (Ollama 3B + 7B)

**Estado:** Aceptada
**Fecha:** 2026-05-22
**Supersedida parcialmente:** [ADR-001](./001-ollama-local.md) — sigue valiendo que el backend es Ollama local, pero la selección de **modelo** se vuelve por-task.

## Decisión

Cada llamada LLM del pipeline `/api/v1/query` ahora elige modelo según la tarea:

| Task | Modelo | Por qué |
|---|---|---|
| `rerank` | `OLLAMA_MODEL_FAST` (default `qwen2.5-coder:3b`) | Output ≤10 tokens, JSON simple. El 14B era overkill — 30× más lento sin diferencia de calidad medible. |
| `soql` | `OLLAMA_MODEL_FAST` | Generación de SoQL es código estructurado. Qwen Coder 3B fue entrenado específicamente en SQL/SoQL — mejor que un general 14B y ~6× más rápido. |
| `dashboard` | `OLLAMA_MODEL_FAST` | El JSON DashboardSpec es schema-driven; tareas mecánicas no necesitan razonamiento profundo. |
| `narrative` | `OLLAMA_MODEL_NARRATIVE` (default `qwen2.5:7b`) | Prosa es-CO interpretativa: tendencias, comparaciones cualitativas. El 7B tiene mejor manejo de español que el Coder y es 2× más rápido que el 14B. |
| `reformulate` | `OLLAMA_MODEL_FAST` | Generación de 3-5 keywords. Tarea trivial. |

Routing implementado en `ai_engine/llm_backend.py:model_for_task(task)`. Los callers (analyzer, query_generator, dashboard_spec_generator) pasan `model=` al `OllamaBackend.generate()`.

## Razón

Baseline 2026-05-22 con `qwen2.5:14b` único:
- Rerank: ~1 s (max_tokens=10).
- SoQL gen + retry: hasta 60 s.
- Narrative: ~40 s.
- Dashboard spec: ~90 s.
- **End-to-end: ~118 s** — inaceptable para UX y para sustentación MinTIC.

Meta: **P95 ≤ 10 s** para queries deterministas, ≤ 20 s para queries libres. Sin GPU. Sin presupuesto para APIs externas.

Token rates empíricos Qwen en CPU 8-core Xeon Gold 6542Y:
- 14B: ~10 tok/s → 400 tokens = 40 s.
- 7B: ~22 tok/s → 400 tokens = 18 s.
- Coder 3B: ~35 tok/s → 300 tokens = 9 s.

Con tiered:
- Rerank: 0.3 s
- SoQL (3B): ~9 s (sin retry, con plantilla determinista cubre ~35% queries en 0 s).
- Narrative (7B): ~18 s.
- Dashboard (3B): ~25 s — **se emite post-`done`** (decisión combinada con desacoplo del cierre SSE).

End-to-end estimado: 12-20 s para queries libres, 2-5 s para deterministas. Cumple meta para deterministas; queries libres quedan en límite.

## Trade-off

- **Calidad narrativa 7B vs 14B**: ~5-10% peor en preguntas ambiguas tipo P13 ("homicidios Bogotá" puede mencionar "tránsito" si el dataset top está mal). Mitigación: `OLLAMA_FALLBACK_MODEL=qwen2.5:14b` queda descargado en VM; rollback en 2 min (`sed` en `.env` + restart api).
- **Dos modelos en RAM simultáneos**: ~8 GB total (3B ~2 GB + 7B ~5 GB). VM tiene 31 GB libres — sin problema. Ollama cachea modelos LRU; el segundo modelo se carga al primer uso de su task.
- **Más complejidad de operación**: dos env vars en lugar de una. Documentado en `deployment_runbook.md`. Default sensato (las env vars opcionales caen a defaults vía `model_for_task`).
- **Caché de modelo cold-start**: la primera query post-restart paga ~5 s extra de cargar el segundo modelo en RAM. Mitigación: keep-alive Ollama via `OLLAMA_KEEP_ALIVE=24h` en VM systemd unit.

## Co-dependencias

- **Plan optimización latencia (este PR)**: streaming Ollama (`OllamaBackend.generate_stream`) baja TTFB de 4 s a 200 ms para narrative.
- **Desacoplar dashboard del `done`**: `api/routes/query.py` emite `done` antes de esperar `dashboard_spec`; el cliente lo renderiza diferido. Permite que dashboard tarde 25 s sin penalizar latencia percibida.
- **Caché embeddings**: `VectorIndex._encode_query_cached` ahorra ~150 ms en queries repetidas.

## Verificación

```bash
# VM: descargar modelos
ollama pull qwen2.5-coder:3b
ollama pull qwen2.5:7b

# Build + deploy
docker compose build api
docker compose up -d api

# Validar que tareas distintas usan modelos distintos
docker compose logs api | grep -E "model=qwen"
```

Telemetría: tabla `queries` agregará columnas `phase_*_ms` con timings por fase. Comparar P95 antes/después.

## Referencias

- [ADR-001](./001-ollama-local.md) — Ollama local como backend (sigue válido para `LLM_BACKEND=ollama`).
- [ADR-013](./013-fastapi-sse-vs-mcp-http.md) — FastAPI SSE: los eventos canónicos siguen igual, solo cambia la latencia.
- [`ai_engine/llm_backend.py`](../../ai_engine/llm_backend.py) — `model_for_task()` factory.
- [`docs/PROD_IMPROV.md`](../PROD_IMPROV.md) — mejoras #1 (LLM upgrade) cerradas aquí.
