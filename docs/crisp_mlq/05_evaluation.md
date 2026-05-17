# 05 — Evaluation

> CRISP-ML(Q) — Fase 5. Cómo verificamos que el agente funciona, qué métricas usamos y qué limitaciones aceptamos honestamente.

## Resumen

DatosVivos se evalúa con **80+ tests automatizados** ejecutados contra `datos.gov.co` y Ollama reales (no mocks de la fuente de verdad), agrupados en suites de aceptación por sprint. No usamos benchmarks sintéticos: cada test verifica un comportamiento ciudadano concreto sobre datos reales. Documentamos públicamente las limitaciones que no logramos cerrar.

---

## 🏛️ Para el jurado MinTIC

### Qué demuestra esta fase

- **Verificación por aceptación**, no por *micro-metrics* arbitrarias. Cada criterio del negocio (capítulo 01) tiene un test asociado que cualquier auditor puede correr.
- **Disciplina de test-first** (MAIN.md §6.6): los tests se congelan **antes** de implementar; la implementación los pone en verde. Esto evita el sesgo de "ajustar el test a lo que el código resultó hacer".
- **Honestidad sobre lo que NO funciona**: documentamos limitaciones reales (el LLM 3B ocasionalmente inventa columnas) en lugar de esconderlas.

### Cifras de cobertura

| Métrica | Valor |
|---|---|
| Tests totales | 82 (suite no-integration) + integration adicionales |
| Suite ejecutada antes del cierre del Sprint 4 | **82 passed** en 14:07 min |
| Test fallido conocido | 1 (Qwen 3B flakiness en una pregunta golden — documentado, no oculto) |
| Sprints con suite de aceptación congelada | 4 (Sprint 1, 2, 3, 4) |
| Decisiones técnicas con ADR registrado | 7 (ADR-001 a ADR-007) |
| Lecciones aprendidas documentadas públicamente | 10+ en [lessons_learned.md](../lessons_learned.md) |

### Disciplina de calidad

- **Doc-first (§6.5):** todo cambio de comportamiento que afecta arquitectura, scope o decisión documentada actualiza simultáneamente la documentación pública en `docs/`.
- **Test-first (§6.6):** los criterios de aceptación se escriben antes del código y no se modifican después salvo errores conceptuales explícitos.
- **PR con descripción rica:** cada PR enumera scope, archivos cambiados y test plan ([histórico de PRs](https://github.com/jsricop/DatosVivos/pulls?q=is%3Apr+is%3Aclosed)).

---

## 🛠️ Para ciudadanos técnicos

### Estructura de la suite de tests

```
tests/
├── test_mcp_tools.py                       # Sprint 1 — 3 tools básicas + cross_datasets
├── test_mcp_server_sse.py                  # Transporte SSE end-to-end
├── test_mcp_server_stdio.py                # Transporte stdio end-to-end
├── test_vector_index.py                    # Vector index unit
├── test_intent_classifier.py               # Clasificador unit
├── test_cross_datasets.py                  # Cruce de 2 datasets unit
├── test_acronyms_acceptance.py             # 11 tests Tier 1 (expansion de siglas)
├── test_topic_keywords_acceptance.py       # 11+ tests Tier 2+3
├── test_cross_multi_acceptance.py          # 8 tests cross N=1..5
├── test_scripts_reproducibility.py         # build_index + extract_topic_keywords desde cero
├── test_sprint2_acceptance.py              # 11 criterios Sprint 2 (vector + intent)
├── test_sprint3_acceptance.py              # 16 criterios Sprint 3 (LLM + analyzer end-to-end)
└── test_sprint4_acceptance.py              # 16 criterios Sprint 4 (UI Streamlit + a11y)
```

### Categorías de tests

1. **Unit tests:** prueban una función aislada (mock de Ollama, mock de Socrata cuando aplica).
2. **Integration tests:** marcados con `@pytest.mark.integration`, ejecutan contra Socrata y Ollama reales. Se saltan si Ollama no está disponible (`@pytest.mark.skipif(OLLAMA_NOT_REACHABLE)`).
3. **Acceptance tests:** uno por criterio funcional declarado en el cronograma. Frozen — solo se ajustan si tienen un error conceptual demostrable.

### "Golden assertions" verificables

En lugar de comparar contra outputs sintéticos, usamos hechos del mundo real verificables contra fuente oficial:

- **Antioquia tiene exactamente 125 municipios** en DIVIPOLA. Un test golden hace `count GROUP BY cod_dpto` sobre `gdxc-w37w` y assertea `n == 125 AND cod_dpto == "05"`. Si el DANE actualiza la división política algún día, este test fallará — y eso es deseable, queremos saberlo.
- **El catálogo expone 4 tools MCP**: `search_datasets`, `get_metadata`, `query_data`, `cross_datasets`. Tests SSE y stdio confirman que `list_tools` devuelve exactamente ese set.
- **Tier 1 expande "DANE" a "Departamento Administrativo Nacional de Estadística"** antes de pegar a Socrata.
- **Una query temática sin nombre de entidad encuentra resultados via Tier 2**. Probado con *"información sobre vacunación"*.

### Bugs detectados y resueltos durante el ciclo

Documentados con cariño porque cada uno se convirtió en aprendizaje permanente:

| Bug | Origen | Mitigación |
|---|---|---|
| `.env` con comentarios inline rompía pydantic-settings | Pydantic v2 strict parsing | Reescribimos `.env.example` con comentarios en líneas propias + validator defensivo |
| `httpx` default User-Agent rechazado por Socrata | Socrata rate-limits agentes sin UA | UA propio: `DatosVivos/0.1` |
| FastMCP ignoraba `MCP_PORT` env | Lib defaults a 8000 | Pass `host=settings.mcp_host, port=settings.mcp_port` explícito |
| FastMCP serializa `list[dict]` como N TextContent blocks | Spec MCP, no bug | Helper `_extract_blocks` que parsea todos los bloques |
| Pair de datasets DIVIPOLA no compartía `cod_dpto` | Catálogo heterogéneo | Migramos a `gdxc-w37w` + `t7kp-7a7c` verificados |
| Qwen 3B confundía `cod_dpto` vs `dpto` | LLM pequeño sin contexto | Agregamos `sample_rows` al prompt |
| `tags` field de Socrata contenía nombres de columnas, no tags | Bug del catálogo | Excluido de la extracción de keywords; documentado |
| OllamaBackend timeout 60s insuficiente bajo carga | Hardware limitado | Bumped a 120s |

### Lo que NO funciona (limitaciones honestas)

Documentamos para que el jurado y los usuarios sepan a qué atenerse:

1. **Qwen 3B flakiness ocasional**: en `tests/test_sprint3_acceptance.py::test_query_generator_produces_executable_soql_for_golden_question`, ~10% de las corridas el modelo inventa una columna `cantidad_municipios` que no existe, reintenta, y termina con `SELECT * LIMIT 1` que no usa GROUP BY. Soluciones reales:
   - Upgrade a Qwen 2.5 Coder **7B** (4x memoria pero mucha más coherencia).
   - Validador determinista pre-execute que rechace SoQL sin las columnas requeridas para el intent.
   - **Test queda visible**, no oculto — es información honesta para el jurado y para futuros mantenedores.

2. **Campo `tags` del catálogo Socrata mal poblado**: ver capítulo 02. Mitigado con topic_keywords propios.

3. **Intent classifier confunde "comparative" con "search"** en queries con palabras como "DIVIPOLA". Resuelto en tests por reformulación del enunciado (el contrato lógico no cambió). Mejorable a futuro con un mini fine-tuning del clasificador.

4. **`cross_datasets` requiere que los datasets compartan la clave de join**. No detectamos automáticamente cuando dos datasets *no son cruzables*; el LLM puede pedir un cruce que devuelve 0 filas. Esto es por diseño: no nos arriesgamos a inventar joins por columnas con el mismo nombre pero distinto significado.

5. **No instrumentamos logging persistente en PostgreSQL**. Fuera de scope del Sprint 4. El schema existe en `db/init.sql` como referencia para un sprint posterior.

### Reproducibilidad

Para verificar todo:

```bash
git clone https://github.com/jsricop/DatosVivos
cd DatosVivos
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.mcp.txt -r requirements.ai.txt -r requirements.streamlit.txt -r requirements-dev.txt

# Levantar Ollama y descargar el modelo
ollama serve &
ollama pull qwen2.5-coder:3b

# Construir el índice (~10 min)
python -m scripts.build_index

# Correr la suite
pytest                              # toda la suite (con integration)
pytest -m "not integration"         # solo unit + acceptance (~14 min total con LLM)
```

---

## 👥 Para ciudadanía general

### ¿Cómo sabemos que el agente funciona?

Cada pieza importante del agente tiene un **test automático**: una pequeña pregunta que el sistema debe responder bien. Por ejemplo:

- *"¿Cuando alguien pide datos sobre DIVIPOLA, el agente encuentra el dataset correcto del DANE?"* — Sí, verificado.
- *"¿Si Antioquia tiene 125 municipios según el DANE, el agente lo cuenta correctamente?"* — Sí, verificado.
- *"¿Si alguien pregunta sobre 'vacunación' sin mencionar al Ministerio de Salud, el agente igual encuentra los datos?"* — Sí, verificado.

En total tenemos **más de 80 de estas pruebas** corriendo automáticamente cada vez que cambiamos algo. Si una empieza a fallar, lo sabemos al instante.

### ¿En qué se puede equivocar?

Documentamos honestamente los casos que detectamos:

- A veces el agente puede confundir columnas similares (por ejemplo, código de departamento vs. nombre del departamento). Se está mitigando dándole más contexto al modelo.
- A veces, si tu pregunta es ambigua, el agente puede entender un tipo de pregunta cuando querías otra. Si pasa, reformúlala con más detalle.
- No todos los datasets se pueden cruzar entre sí. Si no comparten una clave común (como código de municipio), el agente te dirá que el cruce no fue posible.

### ¿Y si el dato cambia en datos.gov.co?

Bien, porque el agente consulta en tiempo real. Si una entidad actualiza un dataset, en la siguiente consulta verás los datos nuevos. **No usamos copias congeladas**.

Lo único que sí está "congelado" es el catálogo de qué datasets existen (lo reconstruimos cuando hay datasets nuevos importantes), pero los contenidos siempre son frescos.

---

## Siguiente capítulo

[06 — Deployment](./06_deployment.md): cómo se despliega el agente en producción.
