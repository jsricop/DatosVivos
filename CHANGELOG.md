# Changelog

Historial de versiones del proyecto **DatosVivos**, agrupado por sprint del concurso *"Datos al Ecosistema 2026: IA para Colombia"* (Reto #07).

Formato adaptado de [Keep a Changelog](https://keepachangelog.com/). Categorías: **Agregado** · **Cambiado** · **Corregido** · **Eliminado** · **Seguridad**.

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
