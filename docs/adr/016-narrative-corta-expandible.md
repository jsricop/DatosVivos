# ADR-016: Narrativa corta+expandible con streaming real (TTFB ≤ 1s)

**Estado:** Aceptada
**Fecha:** 2026-05-22
**Complementa:** [ADR-013](./013-fastapi-sse-vs-mcp-http.md) (eventos SSE), [ADR-015](./015-tiered-llm-models.md) (tiered LLM).

## Decisión

El endpoint `POST /api/v1/query` emite **dos versiones** de la narrativa via SSE, ambas con streaming token-a-token desde Ollama:

1. **`narrative_chunk_summary`** — respuesta corta (2-3 frases, `max_tokens=120`). Llega primero. TTFB del primer token ≤ 1s en producción.
2. **`narrative_chunk_extended`** — respuesta completa con bloque "Datos verificados" determinista al cierre (`max_tokens=400`). Llega después, con `done: true` en el último chunk.

Adicionalmente:
- **`narrative_correction`** (opcional) — versión censurada del extended si `_validate_numbers` quitó cifras no autorizadas.
- **`narrative_chunk`** (legacy) — se sigue emitiendo en paralelo al extended para clientes que no migraron al nuevo contrato. Será removido en Beta-3.

Backend: `Analyzer._narrate_with_data_stream()` AsyncIterator + `defer_narrative=True` flag en `Analyzer.analyze()`. Frontend: nuevo componente `NarrativeBlock` que muestra summary siempre y extended en `<details>` colapsable.

## Razón

Tras PR #23 (tiered LLM Qwen 3B+7B), la latencia bajó de 118s a 22s end-to-end (15.68s hasta `event: done`). Sin embargo, **el primer token visible al usuario seguía tardando ~15s** porque `_narrate_with_data` esperaba la respuesta LLM completa antes de empezar a emitir `narrative_chunk` pre-fragmentado.

Objetivo: TTFB ≤ 1s para que el ciudadano perciba respuesta inmediata. Con LLM 7B CPU-only (~22 tok/s), una llamada de 400 tokens nunca puede completarse en 1s. La única forma de hit TTFB ≤ 1s es:
1. **Streaming real** desde Ollama (token-a-token, sin esperar a `done`).
2. **Respuesta corta primero** (~120 tokens = ~5s completo, pero el primer token llega en ~300ms).

El usuario puede expandir para ver la versión completa con todos los datos verificados.

## Trade-off

- **Dos llamadas LLM en lugar de una**: el tiempo total agregado de ambas (~5s summary + ~18s extended) supera ligeramente a una sola (~18s). Pero la **percepción** del usuario es respuesta inmediata. Trade-off favorable porque la mayoría de usuarios consume el summary, no la versión extendida.
- **El bloque "Datos verificados" queda dentro de `<details>` colapsado**: existe el riesgo de que un ciudadano no lo vea si no expande. Mitigación: el **summary cita la cifra principal explícitamente** (la whitelist de stats garantiza no-alucinación). La microcopia del toggle ("Ver respuesta completa con datos verificados") deja claro que hay más datos.
- **Backward-compat duplica eventos**: clientes nuevos consumen `narrative_chunk_extended`; clientes viejos consumen `narrative_chunk` (legacy). El cliente Next.js usa un flag `hasExtendedEvents` para ignorar el legacy si ya recibió extended y evitar duplicación. Otros clientes consumidores (MCP RPC) deben migrar antes de Beta-3.
- **Validación de cifras requiere buffer completo**: `_validate_numbers` opera sobre el extended completo. Si censura cifras, emite `narrative_correction` con texto censurado que reemplaza al extended en el cliente. Los chunks parciales ya emitidos quedan visibles momentáneamente antes del replace — aceptable porque la corrección llega <500ms después del último chunk.
- **Streaming Ollama puede cortarse a mitad**: try/except en el AsyncIterator emite lo recibido y loggea warning. El cliente sigue funcionando con texto parcial.

## Compatibilidad con dashboard

**Cero impacto en el `DashboardSpecGenerator`**. Verificado en Phase 1 del plan:

- `DashboardSpecGenerator.generate()` recibe solo `question, intent, dataset_name, columns, rows, stats, geo_ctx` — **no recibe narrativa** (`ai_engine/dashboard_spec_generator.py:57-67`).
- `api/routes/query.py` lanza `dashboard_task = asyncio.create_task(...)` antes del streaming de narrativa; ambos corren independientes.
- `event: dashboard_spec` se emite post-`done`. El cliente Next.js sigue procesando el stream después del done (`ResultStream.tsx` no cierra el reader hasta que el remoto cierra la conexión).
- Tests Playwright validan: query con narrativa nueva → dashboard llega post-done renderizado correctamente.

## Verificación

```bash
# Tests unitarios (sin LLM real)
pytest tests/test_sprint3_acceptance.py tests/test_analyzer_streaming.py -q

# Smoke producción (TTFB)
time curl -sN -X POST https://datosvivos.co/api/v1/query \
  -H 'Content-Type: application/json' \
  -d '{"q":"¿Cuántos municipios tiene Antioquia?"}' \
  | head -c 500
# Esperado: el primer chunk `narrative_chunk_summary` aparece en <1s.
```

## Referencias

- [ADR-013](./013-fastapi-sse-vs-mcp-http.md) — Eventos SSE canónicos (ahora con summary/extended).
- [ADR-015](./015-tiered-llm-models.md) — Tiered LLM models (modelo de narrative ya usado acá).
- [`ai_engine/analyzer.py`](../../ai_engine/analyzer.py) — `_narrate_with_data_stream`, `_build_summary_prompt`, `_build_extended_prompt`.
- [`web/src/components/NarrativeBlock.tsx`](../../web/src/components/NarrativeBlock.tsx) — nuevo componente con `<details>` collapsible.
