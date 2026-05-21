# Roadmap de mejoras post-Beta

> Documento operativo, priorizado por **impacto** sobre la experiencia del ciudadano y el jurado MinTIC. Generado al cierre del ciclo iterativo Beta-1 (2026-05-19) a partir de los hallazgos del journey final + 3 sesiones exploratorias + telemetría inicial.

**Estado de Beta-1**: lo que se publica garantiza cifras verificables, cero alucinaciones detectadas en 30 + 36 preguntas reales y trazabilidad completa con enlaces a `datos.gov.co`. Las mejoras de este documento son **incrementales** sobre esa base estable.

## Convención

| Símbolo | Significado |
|---|---|
| 🔥 | Alto impacto, dependencia externa |
| ⚡ | Quick win local |
| 🧪 | Requiere datos de uso real (telemetría) |
| 🏗️ | Refactor o módulo nuevo |

---

## 1. 🔥 Migrar a LLM más robusto en producción

**Problema actual**: Qwen 2.5 Coder 3B genera SoQL inválido en ~47% de los casos del journey (16/30 ejecutan SoQL real). Inventa columnas, rompe sintaxis, ocasionalmente cita "NINGUNO" cuando hay datasets relevantes (corregido con fallback al top-1, ver commit `eadab82`).

**Mejora**: cambiar `OLLAMA_MODEL` a `qwen2.5-coder:7b` cuando la VM tenga ≥6 GB RAM/VRAM disponible, o adoptar Claude Haiku 4.5 vía `LLM_BACKEND=anthropic` si se prefiere API.

**Impacto esperado**: SoQL ejecutado sube de 53% (16/30) a 75-85%. Latencia media: comparable con 7B local, ~3× más rápida con API.

**Esfuerzo**: bajo — el backend ya es intercambiable (`ai_engine/llm_backend.py`).

**Criterio de éxito**: el journey de 30 preguntas alcanza ≥23/30 SoQL ejecutados y ≥10/12 hint detectado.

**Dependencia**: capacidad de la VM de producción o presupuesto API.

---

## 2. 🧪 Cache local de datasets calientes

**Problema actual**: cada consulta vuelve a pegarle a `datos.gov.co`. Para datasets cuasi-estáticos (DIVIPOLA, catálogos administrativos) esto es trabajo repetido.

**Mejora**: cache en `data/dataset_cache/{id}/` (Parquet + schema.json + meta.json) con manifest SQLite (`id`, `last_fetched`, `schema_hash`, `rows_count`, `hits`, `ttl_h`).

**TTL por categoría** (regla simple, ajustar con telemetría):

| Tipo de dataset | TTL |
|---|---|
| DIVIPOLA / catálogos administrativos | 30 días |
| Indicadores económicos (IPC, PIB) | 7 días |
| Vacunación / salud pública | 12 h |
| SECOP / contratación | 6 h |
| Default sin categoría conocida | 1 h |

**Verificación pre-servir**: `HEAD` o `metadata.get(id)` rápido para comparar `updated_at` y `rowsCount`. Si difiere → re-descarga. Triple firma:
1. `dataset_id` (4×4 Socrata).
2. `updated_at` del metadata.
3. `hash(schema columns + types)`.

Si **cualquiera** difiere → invalidar.

**Impacto esperado**: latencia ↓60% para los 20 datasets más pedidos según telemetría. Resistencia a caídas de `datos.gov.co`.

**Esfuerzo**: alto — módulo nuevo `ai_engine/dataset_cache.py` (~400 LoC) + 15 tests.

**Criterio de selección de qué cachear**: tras 2-4 semanas de Beta-1, mirar `data/telemetry/queries.csv` y filtrar datasets con ≥5 hits únicos. Hardcodear esa lista para Beta-2.

**Dependencia**: 2-4 semanas de telemetría real con usuarios.

---

## 3. ⚡ Cobertura completa de municipios DIVIPOLA

**Problema actual**: `geo_resolver.py` solo tiene 32 capitales + 7 mpios grandes. Si un ciudadano pregunta sobre Yopal, Ibagué, Soledad, etc., los detecta. Si pregunta sobre municipios menores (Ciénaga, Quibdó alterno, etc.) no los resuelve y cae a vector search puro.

**Mejora**: cargar dinámicamente los ~1100 municipios del dataset DIVIPOLA `gdxc-w37w` en build-time (script en `scripts/build_geo_dict.py`) y persistir el resultado en `ai_engine/geo_resolver_data.py` similar a `topic_keywords_data.py`.

**Impacto esperado**: cobertura de matching de 39 a ~1130 mpios (29×). Resuelve preguntas sobre municipios pequeños sin pasar por fuzzy match degradado.

**Esfuerzo**: bajo — un script + 1 import + 1 test de carga. ~80 LoC.

**Criterio de éxito**: 10 preguntas sobre municipios no-capital resuelven correctamente `mpio_code`.

---

## 4. 🏗️ Detección de comparativa implícita

**Problema actual**: el resolver detecta "top N", "compara A y B", "A vs B" y "respecto al nacional" explícitos. **No** detecta frases naturales del ciudadano: *"qué departamento tiene más X"*, *"cuál es la región más afectada"*, *"cuál ciudad tiene la tasa más alta"*.

**Mejora**: agregar patrones a `_detect_comparison_mode`:

```python
_IMPLICIT_RANKING = re.compile(
    r"\b(qu[eé]|cu[aá]l)\s+(\w+\s+){0,3}"
    r"(tiene|tienen|registra|registran|presenta|presentan)\s+"
    r"(m[aá]s|menos|mayor|menor|m[aá]xim[oa]|m[ií]nim[oa])\b",
    re.IGNORECASE,
)
```

+ tests congelados con las variantes naturales.

**Impacto esperado**: detección de ranking sube de ~3 a ~8 del journey + sesiones exploratorias. Mejora directamente las preguntas comparativas del jurado MinTIC.

**Esfuerzo**: medio — ~40 LoC + 6 tests congelados.

**Criterio de éxito**: en el journey, intent `comparative` activa `comparison_mode='ranking'` en ≥80% de preguntas que pidan ordenamiento implícito.

---

## 5. 🏗️ Validación geográfica de rows (anti-atribución-incorrecta)

**Problema actual**: en P1 del journey ("¿Cuántos municipios tiene Antioquia?"), el dataset retornado fue *Cifras de Víctimas Municipal* en lugar de DIVIPOLA. El SoQL ejecutó `WHERE estado_depto = 'Antioquia'` y obtuvo 940.451. El validator de cifras permitió la cifra (sí estaba en whitelist porque pandas la calculó) pero la **atribución** fue incorrecta: 940.451 no son municipios, son víctimas.

**Mejora**: nuevo verificador `_validate_geographic_attribution(geo_ctx, rows, top_dataset)`:

- Si `geo_ctx.dpto_code` está seteado, verificar que los rows incluyen al menos una fila con `cod_dpto == geo_ctx.dpto_code` (o columna equivalente).
- Si no, marcar la respuesta como "los datos devueltos pueden no corresponder exactamente al territorio consultado" en el bloque verificado.

**Impacto esperado**: cierra el "riesgo residual #1" reconocido en `lessons_learned.md`. Convierte una atribución silenciosamente incorrecta en una advertencia visible.

**Esfuerzo**: medio — ~70 LoC + 5 tests congelados.

**Criterio de éxito**: en sesión exploratoria, ningún caso muestra cifra correcta pero atribución conceptualmente equivocada (ej. víctimas en vez de municipios).

---

## 6. 🏗️ Multi-query para `vs_national`

**Problema actual**: hoy `vs_national` ejecuta una sola SoQL agrupada por dpto y deja al ciudadano comparar mentalmente "Antioquia vs el resto". Funciona pero la interpretación cualitativa del LLM no siempre es precisa.

**Mejora**: para `comparison_mode='vs_national'`, ejecutar **dos consultas paralelas**:

1. `SELECT count(*) AS n WHERE cod_dpto = '{target}'`
2. `SELECT cod_dpto, count(*) AS n GROUP BY cod_dpto`

Calcular en pandas: `target_count`, `national_mean`, `national_max`, `delta_pct`. Pasar al `Statistics.summary_lines` con líneas tipo:

```
Antioquia: 12.345
Promedio nacional: 3.456
Diferencia: +257% sobre promedio
```

**Impacto esperado**: comparaciones del estilo "cómo está X respecto al país" devuelven cifra concreta del delta, no narrativa vaga.

**Esfuerzo**: medio — refactor parcial de `_execute_soql` + ampliación de `StatsComputer` (~120 LoC + 4 tests).

**Criterio de éxito**: P9 del journey ("Tasa de homicidios en Antioquia respecto al promedio nacional") muestra delta% concreto y verificable.

---

## 7. ⚡ Migrar telemetría CSV → PostgreSQL

**Problema actual**: telemetría se guarda en `data/telemetry/queries.csv`. Funciona para Beta-1 pero el análisis es manual (`pandas.read_csv` ad-hoc). Sin queries SQL ni dashboards.

**Mejora**: cuando el archivo supere 10k filas, migrar a `db/init.sql` (schema ya existe) + adaptar `ai_engine/telemetry.py` para hacer `INSERT` en lugar de append CSV.

**Impacto esperado**: posibilita métricas operativas en tiempo real (latencia p50/p95/p99, datasets más pedidos, tasa de censura por categoría, intents con mayor fallo).

**Esfuerzo**: bajo — el schema PostgreSQL ya está. Solo agregar conexión + INSERT idempotente. ~50 LoC.

**Criterio de selección**: cuando la beta acumule ≥10k consultas (estimado 4-8 semanas).

---

## 8. 🧪 Re-ranker más estable

**Problema actual**: el re-ranker LLM con Qwen 3B oscila entre runs (P6 "Chocó instituciones" entre iter1 y iter2 — corregido conservando top-1 en commit `eadab82`). Sigue habiendo variabilidad de ±10% del SoQL ejecutado entre runs idénticos.

**Mejora**: dos opciones acumulables:

a. **Threshold de confianza**: pedir al LLM responder con número + confianza (`2:high` / `3:low`). Solo aplicar reorden si confidence ≥ alta. ~30 LoC.

b. **Re-ranker semántico no-LLM**: usar embeddings de `multilingual-e5-large` para comparar pregunta vs `(name + description)` de cada candidato y reordenar por similitud. Determinista, sin variabilidad. ~80 LoC.

**Impacto esperado**: estabilidad entre runs (mismo input → mismo output) + posiblemente mejor recall.

**Esfuerzo**: medio (opción b) — más limpio.

**Criterio de éxito**: tres runs consecutivos del journey producen métricas dentro de ±2 SoQL ejecutados.

---

## 9. 🧪 Sugerencias en respuestas vacías (post `_deterministic_no_matches`)

**Problema actual**: cuando no hay datasets relevantes, se muestra el mensaje genérico *"No encontré datasets… reformula con palabras clave más específicas"*. No sugiere alternativas concretas.

**Mejora**: cuando `_deterministic_no_matches` se dispara, llamar al `topic_keywords` (Tier 2) para sugerir 2-3 keywords cercanas y mostrar:

> No encontré datasets sobre «inflación en Bogotá vs Medellín». Quizá quisiste:
> - "IPC anual nacional" (DANE)
> - "Inflación por ciudades capitales"
> - "Variación de precios al consumidor"

**Impacto esperado**: reduce frustración del usuario en ~30% de las preguntas vagas o demasiado específicas.

**Esfuerzo**: medio — ~60 LoC + 3 tests.

---

## 10. 🏗️ Streamlit: render del bloque "Datos verificados" como tabla

**Problema actual**: el bloque "📊 Datos verificados" se renderiza como markdown bullets. Funciona, pero el ciudadano que quiere comparar valores fila a fila tiene que leer corrido.

**Mejora**: si `result.statistics.column_summaries` tiene alguna columna con `top_values`, renderizar `st.dataframe` con 2 columnas: categoría + conteo + porcentaje. Mantener summary_lines abajo como contexto.

**Impacto esperado**: experiencia más cercana a un panel BI. Mejor para preguntas comparativas y ranking.

**Esfuerzo**: bajo — ~40 LoC en `app/pages/chat.py`.

---

## Orden recomendado de ejecución

| Fase | Iteraciones | Mejoras |
|---|---|---|
| **Beta-1** (publicada hoy) | — | base estable: cifras pandas + geo + comparativa + telemetría |
| **Beta-1.1** (semana 1) | quick wins locales | 3 (mpios completos), 4 (ranking implícito), 10 (tabla en UI) |
| **Beta-1.2** (semana 2-3) | con datos parciales | 5 (validación geo de rows), 9 (sugerencias vacías) |
| **Beta-2** (post 4 semanas telemetría) | con datos reales | 1 (LLM 7B/Claude), 2 (cache local), 7 (PostgreSQL) |
| **Producción** | tras Beta-2 estable | 6 (multi-query vs_national), 8 (re-ranker semántico) |

## Cómo se mide el progreso

Cada mejora tiene su **criterio de éxito** explícito arriba. Una mejora se considera "aplicada" cuando:

1. Tests congelados pasan (test-first §6.6).
2. Journey de 30 preguntas mantiene **30/30 sin alucinaciones** y métrica objetivo sube según criterio.
3. Sesión exploratoria de 12 preguntas no introduce regresiones (≥ iter3 actual).
4. Commit con SHA registrado en `CHANGELOG.md` para rollback granular.

Si una mejora introduce regresión, `git revert <sha>` y archivar la lección en `docs/lessons_learned.md`.
