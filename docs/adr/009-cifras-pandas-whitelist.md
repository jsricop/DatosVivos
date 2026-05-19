# ADR-009: Cifras solo desde pandas; LLM interpreta pero no inventa números

**Estado:** Aceptada
**Fecha:** 2026-05-19 (Sprint 6 — Beta-1)

## Decisión

Toda **cifra, estadística o cuantificación** que aparece en una respuesta de DatosVivos viene de cálculo determinista con `pandas` sobre los rows reales devueltos por Socrata. El LLM contribuye solo con **interpretación cualitativa** (qué significan los datos, tendencias, comparaciones contextuales). Si el LLM intenta incluir un número fuera de la lista blanca calculada por pandas, ese número (y la oración que lo contiene) se censura post-hoc.

Componentes:

1. **`ai_engine/stats_computer.py`**: `StatsComputer.compute(rows, soql)` devuelve un `Statistics` con `summary_lines` (texto es-CO listo para mostrar) + `whitelist_numbers` (cifras autorizadas) + `derived_numbers` (ratios, deltas, porcentajes razonables).

2. **`ai_engine/analyzer.py::_validate_numbers(text, stats)`**: extrae cada número de la salida del LLM con regex `r"(?<![A-Za-z0-9_-])-?\d[\d\.,]*"` (ignora IDs alfanuméricos como `gdxc-w37w`). Normaliza con `_normalize_number()` (3 dígitos finales = miles, 1-2 = decimal). Si la cifra no está en `whitelist ∪ derived`, se elimina la **oración entera** que la contiene. Si todas las oraciones se censuran, fallback determinista.

3. **Renderización**: la respuesta final incluye dos bloques claramente separados — narrativa cualitativa del LLM + bloque "📊 Datos verificados" con cifras pandas (siempre presente, intocable).

## Razón

El journey de 30 preguntas con Qwen 2.5 Coder 3B (2026-05-18) detectó alucinaciones de cifras consistentes:

- "¿Cuántos municipios tiene Antioquia?" → SoQL devolvió `n=0` (dataset incorrecto), narrativa inventó **"92 municipios"**.
- "Histórico de homicidios últimos 10 años" → 50 filas reales, narrativa sintetizó **"39 presuntos homicidios"** (suma errónea).
- "¿Cuál departamento con más X?" → LLM citaba cifras razonables pero no contrastables contra los rows.

La instrucción negativa en el prompt (*"no inventes cifras"*) NO es suficiente para un modelo 3B. La única garantía operativa es **separar el cálculo del texto** y validar la salida del LLM contra el cálculo.

## Trade-offs

- **Pérdida de fluidez narrativa**: la respuesta se vuelve más estructurada (prosa + tabla) y menos "historia continua". El intercambio vale: la trazabilidad y verificabilidad son requisitos del jurado MinTIC.
- **Atribución incorrecta no se detecta**: si el LLM cita una cifra correcta (presente en whitelist) pero la atribuye a un concepto distinto al del row (ej. "125 departamentos" cuando son "125 municipios"), el validador no lo captura. Mitigación: bloque pandas debajo de la narrativa con la etiqueta correcta permite al ciudadano contrastar. Mejora futura registrada en [`PROD_IMPROV.md`](../PROD_IMPROV.md#5-validación-geográfica-de-rows-anti-atribución-incorrecta).
- **Censura agresiva**: si el LLM calcula un porcentaje no anticipado por `derived_numbers`, será censurado aunque sea matemáticamente correcto. Por eso `derived_numbers` incluye: deltas max-min, ratios top-N categorías, tolerancia ±0.5 en porcentajes redondeados.
- **Idempotencia y determinismo**: el flujo pandas es 100% reproducible. Dos invocaciones con los mismos rows producen el mismo `Statistics`. Tests congelados (`tests/test_stats_computer.py`) lo verifican explícitamente.

## Métricas de validación

Journey final 30 preguntas (2026-05-19):

| Métrica | Valor |
|---|---|
| Preguntas completadas sin crash | 30/30 |
| Sin palabras prohibidas en narrativa | 30/30 |
| Oraciones censuradas por el validador | 0 |
| Cifras verificadas con pandas | 16/30 |
| SoQL ejecutado contra Socrata | 16/30 |

Cero alucinaciones de cifras detectadas en el conjunto.

## Referencias

- `ai_engine/stats_computer.py` — implementación.
- `ai_engine/analyzer.py::_validate_numbers`, `_number_in_whitelist`.
- `tests/test_stats_computer.py` (8 tests congelados) + `tests/test_number_validator.py` (8 tests congelados).
- [`docs/crisp_mlq/05_evaluation.md`](../crisp_mlq/05_evaluation.md) — evaluación con journey.
- Plan original: `~/.claude/plans/merry-puzzling-pie.md` (interno).
- Commit `4aaecae`.
