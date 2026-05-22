# Changelog

Historial de versiones del proyecto **DatosVivos**, agrupado por sprint del concurso *"Datos al Ecosistema 2026: IA para Colombia"* (Reto #07).

Formato adaptado de [Keep a Changelog](https://keepachangelog.com/). Categorías: **Agregado** · **Cambiado** · **Corregido** · **Eliminado** · **Seguridad**.

---

## [Beta-2 — Latencia P95 ≤ 10s: tiered LLM + dashboard async + caché embeddings] — 2026-05-22

Baseline 118s → meta P95 ≤ 10s. Sin GPU, sin presupuesto API externa. Decisión clave: dividir la carga entre dos modelos Ollama según tarea (ADR-015).

### Agregado
- **`docs/adr/015-tiered-llm-models.md`**: ADR de la decisión arquitectónica. Rerank/SoQL/dashboard al modelo rápido (Qwen Coder 3B, ~35 tok/s); narrative al modelo medio (Qwen 7B, ~22 tok/s).
- **`ai_engine/llm_backend.py:model_for_task(task)`**: factory que resuelve modelo por tarea con env vars `OLLAMA_MODEL_FAST` y `OLLAMA_MODEL_NARRATIVE`. Cae a `OLLAMA_MODEL` legacy si las específicas no están seteadas.
- **`OllamaBackend.generate_stream()`**: streaming token-a-token de Ollama. Reduce TTFB de ~4s a ~200ms en narrative.
- **`MockBackend.generate_stream()`**: paridad con OllamaBackend para tests.
- **Cache LRU de embeddings** en `VectorIndex._encode_query_cached()` (256 entradas, normalizado lowercase sin tildes). Ahorra ~150ms en queries repetidas.

### Cambiado
- **`OllamaBackend.generate()`**: acepta `model=` kwarg para override por llamada. Sin breakage de callers existentes (kwarg-only).
- **`Analyzer._rerank_with_llm()`**: usa `model_for_task("rerank")`.
- **`Analyzer._narrate_with_data()`** y **`_narrate_metadata_only()`** y **`_narrate_search_results()`**: usan `model_for_task("narrative")`.
- **`Analyzer._llm_reformulate()`**: usa `model_for_task("reformulate")`.
- **`QueryGenerator.generate()`**: usa `model_for_task("soql")`.
- **`DashboardSpecGenerator._ask_and_parse()`**: usa `model_for_task("dashboard")`.
- **`api/routes/query.py`**: emite `event: done` **antes** de esperar `dashboard_spec`. El dashboard se emite post-done con timeout 60s. El cliente Next.js lee hasta que el reader cierre el stream — sigue procesando dashboard sin penalizar latencia percibida.
- **`.env.example` + `docker-compose.yml`**: nuevas vars `OLLAMA_MODEL_FAST` / `OLLAMA_MODEL_NARRATIVE`. Defaults sensatos para que upgrade sea zero-touch.

### Operación
- **VM**: pull de modelos previo al deploy: `ollama pull qwen2.5-coder:3b && ollama pull qwen2.5:7b`. RAM combinada ~8 GB (de 31 disponibles).
- **Desmontaje gradual de Qwen 14B**: se mantiene como fallback durante 72h post-deploy. Si telemetría confirma P95 ≤ 15s y `soql_hit_rate` no baja >5pp, `ollama rm qwen2.5:14b` libera ~9 GB.
- **Rollback en caliente** (post-desmontaje): `ollama pull qwen2.5:14b` (~5 min) + `OLLAMA_MODEL_NARRATIVE=qwen2.5:14b` + restart api.

### Verificación
- Suite crítica: 77 passed, 2 skipped, 6 deselected (sin regresión).
- Smoke determinista esperado: ≤5s end-to-end hasta `done`.
- Smoke libre esperado: ≤18s end-to-end hasta `done`; dashboard llega post-done.
- Telemetría granular (`phase_*_ms`) en `queries` table — comparar P95 antes/después.

---

## [Beta-2 — UI/UX clarity pass: ColorModeToggle + Chip cards + QueryBuilderBar] — 2026-05-21

Iteración de claridad de affordance en la home Next.js basada en feedback del usuario (screenshot 2026-05-21): el selector de modo se leía como tres palabras corridas en el header y los chips parecían decorativos. Sin cambios al motor IA ni a la API.

### Agregado
- **`web/src/components/QueryBuilderBar.tsx`** (~100 LoC): nueva barra con `<aside role="status" aria-live="polite">` que aparece **solo si hay chips seleccionados**. Lista chips removibles agrupados por eje (TEMA/TIPO/TERRITORIO/ENTIDAD) + botón "Buscar →" que navega a `/buscar?<axis>=<value>...`. Da feedback visible de "construcción de consulta" antes de ejecutar.
- Iconos `sun` y `moon` en `web/src/components/Icon.tsx` (outline only, `currentColor`, stroke 1.5, viewBox 24×24 — cumple BRAND.md §6.2). Set MVP pasa de 16 a 18 iconos.
- Microcopia debajo del HeroSearch en home: *"O construye tu consulta con los filtros de abajo. Cada selección se va sumando a la barra inferior."* — crea conexión mental input ↔ chips.

### Cambiado
- **`web/src/components/ColorModeToggle.tsx`**: label visible "Apariencia" en `font-mono uppercase text-caption text-ink-muted` (oculto en mobile <640px para no romper header). Cada modo usa **icono distintivo** (sun/moon/contrast) en lugar de tres `contrast` iguales. `aria-labelledby="color-mode-label"` agregado para asociar label al group. Persistencia `datosvivos:theme` y anti-FOUC sin cambios.
- **`web/src/components/ChipGroup.tsx`**: wrapper `<fieldset>` ahora es **tarjeta visual** con borde `1px solid var(--hairline)` + fondo `var(--bg-elev)/60` + padding `pt-4 pb-5 px-5`. Legend con kicker mono anclado en el borde superior. Hint `description` movido a `<p>` debajo del legend en lugar de inline.
- **`web/src/components/HomeSearchPanel.tsx`**: integra QueryBuilderBar (handler `clearOne(axis, value)`) y wrapping de grid con microcopia. `gap-y` de la grilla de tarjetas pasa de 7 a 5 (más aire vertical compensa el borde adicional).
- **`docs/BRAND.md` §6.2**: tabla de iconos actualizada a 18 entradas con `sun`/`moon`.
- **`docs/BRAND.md` §8.3**: spec de `ChipGroup` actualizada — explícita la tarjeta visual con borde.
- **`docs/BRAND.md` §8.3-bis**: nueva sección con spec de `QueryBuilderBar`.
- **`docs/BRAND.md` §8.11**: spec de `ColorModeToggle` actualizada — label "Apariencia", `aria-labelledby`, iconos distintivos por modo.

### Verificación
- Local: `cd web && npm run build` compila sin errores en mis archivos (`pg`-error preexistente en `auth.ts`, no introducido por este PR).
- Type-check: `npx tsc --noEmit -p tsconfig.json` sin errores en los archivos modificados.
- Manual smoke en producción tras deploy: ver `https://datosvivos.co/` desktop (label visible) y mobile (label oculto, control compacto).

---

## [Sprint 6 — Beta-1: cifras verificadas + GeoResolver + comparativa] — 2026-05-19

Sprint dedicado al endurecimiento del motor para lanzamiento beta. Foco: cero alucinaciones de cifras, trazabilidad por enlaces, comparativas geográficas multi-target y telemetría operativa. Push directo a `develop` con 8 commits granulares (`4aaecae` → `eadab82`) para rollback quirúrgico.

### Agregado
- **`ai_engine/stats_computer.py`** (290 LoC): cálculo determinista de estadísticas con pandas. `Statistics` expone `summary_lines` (texto es-CO), `whitelist_numbers` (cifras autorizadas), `derived_numbers` (ratios y deltas). Auto-cast de strings SODA a numérico/fecha (pandas 3.0 / PyArrow). Helper `_normalize_number` con heurística es-CO (3 dígitos finales = miles, 1-2 = decimal).
- **`ai_engine/geo_resolver.py`** (485 LoC): detección de territorios colombianos con DIVIPOLA. 32 departamentos + Bogotá D.C. con sinónimos comunes. 39 capitales y municipios grandes. Fuzzy match con `difflib` (cutoff 0.78). Multi-target: `GeoContext.targets: list[GeoTarget]` + `comparison_mode` (`vs`/`ranking`/`vs_national`/None). Plantillas SoQL deterministas via `build_comparison_soql()` que reconoce columnas-código y columnas-nombre (`cod_dpto`, `departamento_del_hecho_dane`, `municipio`, etc.).
- **`ai_engine/telemetry.py`** (68 LoC): logger CSV append-only para fase beta. Schema fijo: timestamp, question, intent, datasets_used, soql_executed, rows_count, censored_count, elapsed_s, had_statistics. Best-effort: errores no rompen el flujo principal.
- **`scripts/exploratory_session.py`**: batería de 12 preguntas fuera del journey congelado para detectar gaps no cubiertos.
- **Tests congelados** (45 nuevos):
  - `test_stats_computer.py` (8): aggregations, auto-cast, normalización es-CO, determinismo.
  - `test_number_validator.py` (8): whitelist, censura por oración, formato es-CO, IDs alfanuméricos, fallback.
  - `test_geo_resolver.py` (13): matriz de 5 patrones, sinónimos, fuzzy, anti-falsos-positivos.
  - `test_geo_comparison.py` (16): multi-target, comparison_mode, plantillas SoQL, columnas-nombre.
- **`docs/PROD_IMPROV.md`**: roadmap post-beta con 10 mejoras priorizadas (LLM 7B, cache local, cobertura mpios, ranking implícito, validación geo de rows, etc.).
- **ADRs 009 y 010**: cifras pandas + whitelist; GeoResolver DIVIPOLA + plantillas SoQL deterministas.

### Cambiado
- **`ai_engine/analyzer.py`**: integración completa de StatsComputer + GeoResolver + plantillas SoQL. `_narrate_with_data` ahora:
  - Si 0 filas → respuesta determinista sin LLM.
  - Si filas → LLM recibe rows + ficha de cifras autorizadas; toda cifra de la salida se valida contra whitelist; oraciones con cifras no autorizadas se censuran.
- `_narrate_no_matches` → ahora es **determinista**, sin LLM (corrige alucinación P30 'Ecuador' que inventaba datasets ecuatorianos).
- `_llm_reformulate` → timeout duro de 60 s (corrige caso P30 que se atascó 67 min en versión previa).
- `_rerank_with_llm` → cuando dice 'NINGUNO' conserva el top-1 (en vez de descartar todo, lo que provocaba falsos negativos del LLM 3B — corrige regresión P6 'Chocó').
- Retrieval híbrido vector + Discovery API con timeout 5 s + GEO_BOOST adicional cuando geo_ctx resuelve un territorio mencionado en metadata.
- `AnalysisResult` expone tres campos nuevos: `dataset_references` (id + name + entity + url página + url JSON), `statistics: Statistics`, `geo_context: GeoContext`.
- **`app/pages/chat.py`**: nuevo bloque visible "📚 Fuentes consultadas (verifícalo tú mismo)" con enlaces clicables a `https://www.datos.gov.co/d/{id}` y al endpoint JSON SODA. Disclaimer beta en header. Telemetría por consulta.
- **`scripts/user_journey_test.py`**: ampliado de 8 a **30 preguntas en 10 categorías** (geo simple, salud, educación, contratación, seguridad, economía, ambiente, comparativa, temporal, adversarial). Métricas nuevas: SoQL ejecutado, cifras verificadas pandas, oraciones censuradas.

### Corregido
- **Alucinación de cifras** (`"92 municipios"`, `"39 homicidios"`, etc.): toda cifra ahora viene exclusivamente de cálculo pandas sobre rows reales. Validador post-LLM censura oraciones con números fuera de whitelist.
- **Alucinación de datasets** (caso adversarial 'Ecuador'): la respuesta sin matches ahora es texto fijo, sin invocar LLM.
- **Crash `IndexError`** cuando rerank devolvía `[]` y el flujo accedía `hits[0]`: ahora la lista vacía cae al branch de no_matches determinista. Eliminó 3 crashes del journey.
- **Bug del overlap "Cauca" ⊂ "Valle del Cauca"**: dedup de matches por rango contenido.
- **Regla anti-capital**: si la pregunta usa plural genérico ("municipios", "departamentos") y nombra un dpto, NO se infiere el municipio capital (resuelve "¿cuántos municipios tiene Antioquia?" sin colapsar a Medellín).

### Métricas finales del journey 30 preguntas (2026-05-19)

| Métrica | Pre-Sprint 6 | Sprint 6 final | Δ |
|---|---|---|---|
| Tiempo total | 5218 s | 626 s | **−88%** |
| Completadas sin crash | 27/30 | 30/30 | +3 |
| Sin palabras prohibidas | 30/30 | 30/30 | mantenido |
| SoQL ejecutado | 12/30 | 16/30 | +33% |
| Cifras verificadas pandas | 12/30 | 16/30 | +33% |
| Oraciones censuradas | 2 | 0 | −100% |
| Suite tests verdes | 24 | 55 | +129% |

---

## [Sprint 5 — Documentación CRISP-ML(Q)] — 2026-05-16

PR [#12](https://github.com/jsricop/DatosVivos/pull/12).

### Agregado
- `docs/crisp_mlq/` con **9 documentos**: índice + 6 fases CRISP-ML(Q) + capítulo especial MCP + checklist MinTIC.
- Cada doc con tres lentes explícitos (🏛️ jurado · 🛠️ técnico · 👥 ciudadanía).
- `docs/adr/` con ADRs **001-008** extraídos como archivos públicos auditables.
- `CHANGELOG.md` (este archivo).
- Sección **"🏛️ Para el jurado MinTIC"** en `README.md` con tabla de entradas rápidas.

### Cambiado
- `docs/glossary.md`: corrijo info desactualizada (`e5-base 768-dim` → `e5-large 1024-dim`, LLM default `7B` → `3B con upgrade documentado a 7B`).
- Placeholders `docs/0{1..6}_*.md` convertidos en redirects de 1 línea al subfolder canónico.

### Corregido
- **Qwen 3B flakiness ocasional** en `test_query_generator_produces_executable_soql_for_golden_question`: endurecimos el prompt con tres ejemplos canónicos, subimos `max_retries` a 2, y agregamos feedback específico cuando la columna inventada parece alias agregado (`cantidad_*` / `total_*` / `num_*`). 3 corridas consecutivas verdes en 2-8 s.

---

## [Sprint 4 — UI Streamlit + accesibilidad] — 2026-05-14 a 2026-05-16

PR [#11](https://github.com/jsricop/DatosVivos/pull/11).

### Agregado
- `app/main.py` + páginas (`chat.py`, `explorer.py`, `about.py`) con `st.navigation` multipage.
- `app/agent_client.py`: sync wrapper sobre `ai_engine.Analyzer` con `asyncio.run`.
- `app/components/chart_renderer.py`: Plotly auto-detección por tipo de columna.
- `app/components/map_renderer.py`: Folium con marcadores desde lat/lon.
- `app/components/accessibility/`: Web Speech API (`speech_input.py`, `speech_output.py`), alt-text auto-generado (`chart_narrator.py`), toggle global (`a11y_toggle.py`).
- `requirements.streamlit.txt`, `.streamlit/config.toml` (tema dark accesible).
- `Dockerfile.streamlit` + servicio `streamlit` en `docker-compose.yml`.
- `tests/test_sprint4_acceptance.py` (16 tests, todos verdes).

### Cambiado
- Scope ajustado: **Power BI sale del entregable** (queda como integración externa opcional). Ver [ADR-008](docs/adr/008-scope-sin-powerbi.md).
- `docs/architecture.md` Capa 3 reescrita como "Streamlit" (singular).

### Corregido
- Estructura de carpetas `app/` alineada con la documentación tras detectar scaffolding previo (preservamos nombres existentes: `chart_renderer`, `map_renderer`, subfolder `accessibility/`).

---

## [Extensión MCP — Acrónimos + Topic Keywords] — 2026-05-13 a 2026-05-15

PRs [#8](https://github.com/jsricop/DatosVivos/pull/8) (acrónimos) y [#9](https://github.com/jsricop/DatosVivos/pull/9) (topic keywords) + [#10](https://github.com/jsricop/DatosVivos/pull/10) (cobertura de tests).

### Agregado
- `mcp_server/socrata/acronyms.py`: **117 entidades, 562 aliases** del sector público colombiano (Tier 1).
- `mcp_server/socrata/topic_keywords.py` + `topic_keywords_data.py`: ~3 050 keywords temáticos (Tier 2).
- `ai_engine/analyzer.py::_llm_reformulate`: Tier 3 fallback con reformulación por LLM.
- `scripts/extract_topic_keywords.py`: extracción data-driven.
- `tests/test_acronyms_acceptance.py` (11) + `test_topic_keywords_acceptance.py` (11+) + `test_scripts_reproducibility.py` (2).
- [ADR-007: Búsqueda con fallback en 3 tiers](docs/adr/007-busqueda-3-tiers.md).

### Cambiado
- `OllamaBackend` timeout 60s → 120s (bajo carga concurrente).
- `DiscoveryClient.search()` integra Tier 1 (expansión de acrónimos) antes de pegarle a Socrata.

### Corregido
- Migración del pair de datasets DIVIPOLA a `gdxc-w37w` + `t7kp-7a7c` (los previos no compartían `cod_dpto`).
- 4 gaps de cobertura cerrados tras auditoría honesta (PR [#10](https://github.com/jsricop/DatosVivos/pull/10)).

---

## [Sprint 3 — LLM end-to-end + cross_datasets] — 2026-05-11 a 2026-05-13

PR [#6](https://github.com/jsricop/DatosVivos/pull/6) + extensión cross-multi en [#7](https://github.com/jsricop/DatosVivos/pull/7).

### Agregado
- `ai_engine/analyzer.py`: orquestador end-to-end (intent → vector search → LLM narrativa).
- `ai_engine/llm_backend.py`: Protocol + `OllamaBackend` + `AnthropicBackend` (stub) + `MockBackend`.
- `ai_engine/query_generator.py`: NL → SoQL con esquema y `sample_rows`.
- `mcp_server/tools/cross_datasets.py`: cruce de **1 a 5 datasets** con guardia anti-falsos-positivos.
- `tests/test_sprint3_acceptance.py` (16) + `test_cross_multi_acceptance.py` (8).
- [ADR-001: Ollama local](docs/adr/001-ollama-local.md).

### Corregido
- Qwen 3B confundía `cod_dpto` vs `dpto`: agregamos `sample_rows` al prompt.

---

## [Sprint 2 — Motor de IA local] — 2026-05-09 a 2026-05-11

PR [#5](https://github.com/jsricop/DatosVivos/pull/5).

### Agregado
- `ai_engine/vector_index.py`: ChromaDB local con `sentence-transformers/multilingual-e5-large` (1024-dim).
- `ai_engine/intent_classifier.py`: clasificador por centroides de embeddings (sin LLM).
- `scripts/build_index.py`: pipeline reproducible que indexa los **8 389 datasets** del catálogo.
- `tests/test_sprint2_acceptance.py` (11) + tests unitarios.
- [ADR-005: ChromaDB vs pgvector](docs/adr/005-chromadb-vs-pgvector.md).

### Cambiado
- `DiscoveryClient` refactorizado para paginación completa del catálogo (no solo top 100).

### Corregido
- `httpx` default User-Agent rechazado por Socrata: ahora `DatosVivos/0.1`.
- `.env` con comentarios inline rompía pydantic-settings: reescrito con comentarios en líneas propias.

---

## [Sprint 1 — MCP Server + Docker] — 2026-04-28 a 2026-05-08

PRs [#1](https://github.com/jsricop/DatosVivos/pull/1) a [#4](https://github.com/jsricop/DatosVivos/pull/4).

### Agregado
- `mcp_server/server.py` con 3 tools iniciales: `search_datasets`, `get_metadata`, `query_data`.
- `mcp_server/socrata/` con 3 clientes: Discovery, Metadata, SODA.
- Transportes **SSE** y **stdio** soportados.
- `Dockerfile.mcp` + servicio `mcp-server` en `docker-compose.yml`.
- `tests/test_mcp_tools.py` (10) + `test_mcp_server_sse.py` (4) + `test_mcp_server_stdio.py` (2).
- Documentación pública extraída a `docs/` (`architecture.md`, `accessibility.md`, `glossary.md`, `lessons_learned.md`).
- LICENSE MIT.

### Corregido
- FastMCP ignoraba `MCP_PORT` env: pasamos `host`/`port` explícitos desde settings.
- FastMCP serializa `list[dict]` como N TextContent blocks (no es bug, es spec): helper `_extract_blocks` para parsearlo.
- Reglas del repo en `MAIN.md §6.5/§6.6` (test-first y doc-first).

---

## Próxima entrega — 2026-07-13

- Publicación en `datos.gov.co` y `herramientas.datos.gov.co/usos` (coordinación con MinTIC).
- Demo público con dominio + TLS.
- Pitch / video para sustentación Jul 14-17.
