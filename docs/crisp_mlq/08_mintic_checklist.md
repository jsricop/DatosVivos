# 08 — Checklist de criterios MinTIC

> Documento operativo. Mapea cada criterio explícito (o razonablemente inferible) de las bases del concurso *"Datos al Ecosistema 2026: IA para Colombia"* — Reto #07 — a la evidencia concreta en este repositorio.

## Convención

| Símbolo | Significado |
|---|---|
| ✅ | Cumplido y verificable en el repo |
| 🟡 | Cumplido parcialmente — gap documentado |
| 🔜 | Pendiente (Sprint 5 FASE 8-9) |
| — | No aplica al Reto #07 |

## Categoría 1 — Solución de IA

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1.1 | Aplicación funcional sobre datos abiertos colombianos | ✅ | UI Streamlit corriendo (`app/`), MCP server consultando `datos.gov.co` (`mcp_server/`). |
| 1.2 | Uso de lenguaje natural por parte del ciudadano | ✅ | Chat con `st.chat_input`, NL → SoQL en `ai_engine/query_generator.py`. |
| 1.3 | Respuestas verificables (con trazabilidad de fuente) | ✅ | `AnalysisResult` expone `datasets_used`, `soql_executed`. Cada respuesta cita `dataset_id` y permalink. |
| 1.4 | Cobertura no trivial del catálogo | ✅ | 8 389 datasets indexados via `scripts/build_index.py`. |
| 1.5 | Visualizaciones (cuando aplica) | ✅ | Plotly (`chart_renderer.py`) auto-detecta líneas/barras/scatter. Folium (`map_renderer.py`) para geo. |
| 1.6 | Cruces entre datasets | ✅ | Tool `cross_datasets` (N=1..5) con guardia anti-FP. Tests `test_cross_multi_acceptance.py`. |

## Categoría 2 — Accesibilidad (Ley 1618 / WCAG 2.1)

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 2.1 | Entrada por voz (STT) | ✅ | Web Speech API `es-CO` en `app/components/accessibility/speech_input.py`. Fallback a `st.chat_input`. |
| 2.2 | Salida por voz (TTS) | ✅ | `SpeechSynthesis es-CO` en `speech_output.py`, toggle activable en sidebar. |
| 2.3 | Alt-text para gráficos | ✅ | `chart_narrator.narrate_chart` genera descripción estadística determinista. |
| 2.4 | Contraste accesible (WCAG AA) | ✅ | Tema dark configurado en `.streamlit/config.toml` con paleta slate + azul. |
| 2.5 | Navegación por teclado | ✅ | Streamlit nativo soporta tab/enter/space; toggle a11y en `aria-live`. |
| 2.6 | Toggle global de accesibilidad | ✅ | `a11y_toggle.render_a11y_toggle()` en sidebar de todas las páginas. |

## Categoría 3 — Soberanía técnica y privacidad

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 3.1 | LLM ejecutado localmente (sin enviar consultas ciudadanas a terceros) | ✅ | Default `LLM_BACKEND=ollama` con Qwen 2.5 Coder local. ADR-001. |
| 3.2 | Backend intercambiable (no captura tecnológica) | ✅ | `ai_engine/llm_backend.py` Protocol + Ollama/Anthropic/Mock implementations. |
| 3.3 | Sin recolección obligatoria de datos personales del usuario | ✅ | App sin login, sin formularios PII. `db/init.sql` queda como referencia inactiva. |
| 3.4 | Open source con licencia permisiva | ✅ | Código público en GitHub bajo licencia **MIT** (`LICENSE` en raíz del repo). |

## Categoría 4 — Reproducibilidad y verificabilidad

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 4.1 | Repositorio público con código completo | ✅ | https://github.com/jsricop/DatosVivos |
| 4.2 | Tests automatizados | ✅ | 82+ tests, ejecución: 14:07 min con integration. |
| 4.3 | Build reproducible (Docker) | ✅ | `Dockerfile.mcp`, `Dockerfile.streamlit`, `docker-compose.yml`. |
| 4.4 | Pipelines de preparación reproducibles | ✅ | `scripts/build_index.py`, `scripts/extract_topic_keywords.py` + `tests/test_scripts_reproducibility.py`. |
| 4.5 | Documentación CRISP-ML(Q) completa | ✅ | `docs/crisp_mlq/00..07_*.md`. |
| 4.6 | Decisiones de arquitectura registradas | ✅ | ADRs 001-008 en `MAIN.md §9` (privado del equipo) — referenciados en cada decisión técnica. |

## Categoría 5 — Interoperabilidad

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 5.1 | Estándar abierto para integración | ✅ | MCP (Model Context Protocol) — JSON-RPC 2.0, spec pública. |
| 5.2 | Cliente independiente puede consumir la API | ✅ | Tests `test_mcp_server_sse.py` y `test_mcp_server_stdio.py` usan cliente externo. |
| 5.3 | Documentación de integración con asistentes comunes | ✅ | `07_mcp_integrations.md` — guías paso a paso para Claude Desktop, Gemini, Cursor, SDK Python, SDK TS. |

## Categoría 6 — Marco normativo colombiano

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 6.1 | Cumplimiento Ley 1581 de 2012 (datos personales) | ✅ | No recolectamos PII; mencionado en `01_business_understanding.md`. |
| 6.2 | Cumplimiento Ley 1712 de 2014 (transparencia) | ✅ | Toda data consultada es pública vía datos.gov.co. |
| 6.3 | Cumplimiento Ley 1618 de 2013 (accesibilidad) | ✅ | Modo accesible + WCAG 2.1 AA, ver Categoría 2. |
| 6.4 | Atribución correcta a entidades publicadoras | ✅ | Toda respuesta cita la entidad (`attribution` Socrata) y enlaza al dataset original. |

## Categoría 7 — Publicación y diseminación

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 7.1 | Publicación en `datos.gov.co` (como uso de datos) | 🔜 | FASE 8 antes de 2026-07-13. |
| 7.2 | Publicación en `herramientas.datos.gov.co/usos` | 🔜 | FASE 8 antes de 2026-07-13. |
| 7.3 | Demo accesible al jurado | 🔜 | URL pública con TLS pendiente — VM lista por VPN. |
| 7.4 | Video / pitch deck | 🔜 | Por producir antes de sustentación (Jul 14-17). |

## Gaps abiertos al cierre del Sprint 5 FASE 0-8

1. **Publicación pública** — pendiente coordinación con MinTIC del proceso (`datos.gov.co` y `herramientas.datos.gov.co/usos`).
2. **Pitch / video** — entregable de sustentación, no del repo.
3. **Test fallido conocido del Qwen 3B** — visible en `test_sprint3_acceptance.py`. Mitigación: upgrade a 7B en producción si hardware lo permite.
4. **Demo público con TLS** — la VM corre por VPN; falta exponerla con dominio HTTPS antes de sustentación.

## Cómo el jurado puede verificar todo

```bash
# 1. Clonar repo
git clone https://github.com/jsricop/DatosVivos && cd DatosVivos

# 2. Levantar entorno
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.mcp.txt -r requirements.ai.txt \
            -r requirements.streamlit.txt -r requirements-dev.txt
curl -fsSL https://ollama.com/install.sh | sh
ollama serve & ollama pull qwen2.5-coder:3b

# 3. Construir índice
python -m scripts.build_index   # ~10 min

# 4. Correr tests
pytest -m "not integration" -q  # ~30s

# 5. Levantar la app
streamlit run app/main.py
# → abrir http://localhost:8501

# 6. Verificar integración MCP (Claude Desktop)
# → seguir docs/crisp_mlq/07_mcp_integrations.md
```

Toda afirmación de este checklist es verificable con `git grep`, `pytest` o ejecutando la app.
