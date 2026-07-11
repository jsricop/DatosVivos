# ADR-022: Motor NL2SQL generativo + verificado (verificación de consulta de 3 capas)

**Estado:** Aceptada
**Fecha:** 2026-06-25
**Implementa / refina:** [ADR-017](./017-arquitectura-hibrida-ia-determinista.md) §3 (SoQL asistido por IA con validación)
**Relacionada:** [ADR-018](./018-ui-transparencia-soql.md) (SoQL visible), ADR-009 (cifras desde filas reales; ADR temprano no conservado)
**No supersede a ADR-017** — lo realiza. ADR-017 definió el principio ("la IA razona; el
motor determinista ejecuta y verifica") y prometió un validador que verifica el SoQL generado
**antes** de ejecutar. Este ADR es la *implementación* concreta de ese validador, enriquecida con
la literatura text-to-SQL 2025-2026.

## Contexto

ADR-017 prometió: *"para preguntas fuera de las plantillas TIPO, la IA genera SoQL viendo solo
columnas curadas reales; un validador verifica (las columnas existen, hay filtro geo cuando
aplica, es read-only) **antes** de ejecutar […] Nunca se ejecuta SoQL no validado."*

Una auditoría del código (2026-06-25) reveló que **ese validador no está realmente
implementado** en el camino generativo (`/api/v1/query` → `ai_engine/analyzer.py` →
`ai_engine/query_generator.py`):

1. La validación actual (`_validate_numbers`) verifica los **números de la narrativa**, no la
   **corrección de la consulta**. Un SoQL plausible-pero-equivocado devuelve un número **real
   pero que responde otra pregunta** — y pasa el filtro.
2. El camino generativo arma el esquema desde la **Metadata API de Socrata**, no desde
   `dataset_columns_curated`. Es decir, ni siquiera ve los `semantic_type` curados que ADR-017
   asumía. La verificación semántica que ADR-017 describía no tiene de dónde leer.
3. El "validador" de `query_generator.py` solo chequea columnas inexistentes, con 1 reintento.

Para un servicio de datos públicos del Estado, una **cifra oficial con pinta de verificada pero
semánticamente equivocada** es el peor modo de fallo (ADR-017 ya lo dice). La literatura lo
confirma: el "performance cliff" — los modelos rinden 85-92% en benchmarks fáciles (Spider 1.0)
pero **6-21%** en realistas (BIRD, Spider 2.0), y la causa #1 es el *schema-linking a escala*
(DatosVivos cataloga ~10k datasets). El fallo típico documentado: *"resultados plausibles pero
incorrectos"*.

## Decisión

Promover el camino generativo (NL2SQL) a entrada primaria e implementar la **verificación a
nivel de consulta** que ADR-017 prometió, con tres patrones probados de la literatura
2025-2026 (ver [NL2SQL_BASE.md](../NL2SQL_BASE.md) para fuentes). **No se construye sobre un
framework** (LangChain/Vanna/LlamaIndex): ninguno habla SoQL ni resuelve "elegir entre 10k
datasets"; se adoptan **patrones**, no librerías.

### 1. Verificación de consulta de 3 capas (patrón PV-SQL)
Entre la generación del SoQL y la ejecución que trae filas:
- **Capa 1 — sintaxis (sin ejecutar):** parser heurístico (SoQL no es SQL estándar: sin `FROM`,
  funciones Socrata). Empieza con `SELECT`, paréntesis balanceados, `GROUP BY` coherente,
  columnas referenciadas ⊆ columnas reales del dataset.
- **Capa 2 — ejecución barata:** `SELECT … LIMIT 0` contra SODA (SoQL **no tiene `EXPLAIN`**;
  `LIMIT 0` es el sustituto correcto: valida la consulta sin traer datos). Captura el `400` de
  Socrata como mensaje de error dirigido.
- **Capa 3 — restricciones semánticas:** se extrae la intención de la pregunta a restricciones
  verificables ("cuántos"→`count(*)`, "por X"→`GROUP BY` sobre columna `dimension/geo`, "top
  k"→`ORDER BY DESC LIMIT`, "tendencia"→columna `fecha`, filtro geo→`WHERE col_geo = código`) y
  se verifica que el SoQL las cumpla, **contra `dataset_columns_curated`** (los `semantic_type`).

### 2. Bucle de reparación (reparar > rechazar)
Reemplaza el "1 reintento" por hasta 4 reparaciones dirigidas: se le devuelve al LLM el SoQL
anterior + el error específico por capa (no se regenera desde cero). Patrón con ~91% de
reparación exitosa en la literatura.

### 3. Refusal y degradación segura (precisión sobre cobertura)
Si tras reparar la verificación no pasa:
- **Degradar al template determinista** (`ai_engine/soql_templates.build_soql`, el mismo motor
  de los chips) cuando la pregunta encaja en una de las 5 formas TIPO — correcto por construcción.
- Si no encaja → **rehusar** explícitamente ("No puedo afirmar esto con confianza") en vez de
  inventar. También se rehúsa cuando el retrieval es débil o el dataset no tiene las columnas que
  la pregunta exige (ej. "tendencia" sobre un dataset sin columna `fecha`).

### 4. "Esto entendí" (human-in-the-loop ligero)
Antes de afirmar la cifra, el frontend muestra la interpretación (dataset elegido + intención +
filtros + columnas usadas + estado de verificación). Informativo, no bloqueante (el contrato SSE
es una sola request). Refuerza ADR-018 (transparencia): el ciudadano ve *qué entendió* el sistema,
no solo el SoQL.

## Razón

- **Cumple el principio de ADR-017** sin reabrirlo: la IA razona, el motor verifica y ejecuta.
  Esto cierra la brecha entre la intención escrita de ADR-017 y el código real.
- **El campo converge en lo mismo que ya defendíamos:** capa semántica (los templates),
  generación, verificación multinivel, y *rehusar antes que adivinar*. Las recomendaciones de la
  literatura (limitar alcance a vistas curadas, capa de métricas, validación multi-agente,
  human-in-the-loop, sandboxing read-only) mapean casi 1:1 a lo que DatosVivos ya tiene.
- **Los templates NO se botan.** El error de framing inicial era "NL2SQL reemplaza a los chips".
  En realidad los templates son la **capa semántica de respaldo** que el campo recomienda
  explícitamente; los chips quedan además para clasificación de catálogo.

## Trade-offs

- **Parsear SoQL es heurístico** (no es SQL estándar; `sqlglot` no lo soporta). Riesgo de falsos
  negativos en la capa 1 → mitigado porque la capa 2 (`LIMIT 0` real) atrapa lo que el parser no ve.
- **Latencia:** hasta 5 llamadas LLM + N `LIMIT 0` antes del primer token de narrativa. Mitigación:
  evento SSE `verification_progress`, caps de tiempo por iteración, modelo `OLLAMA_MODEL_FAST`.
- **Costo LLM** ×~5 en el peor caso; la mayoría de queries pasa en 0-1 reparaciones (se instrumenta
  `verification_repairs` para vigilar la distribución).
- **Curación parcial:** donde no hay `dataset_columns_curated`, la capa 3 clasifica al vuelo con
  `column_classifier` (menor confianza) → el refusal por columnas ausentes es conservador ahí.
- **Cobertura puede bajar levemente** a cambio de eliminar los "falsos verificados". Es el
  intercambio deseado para un servicio del Estado ("precisión sobre cobertura").

## Métrica de éxito

KPI primario: **tasa de "falsos verificados"** (consulta plausible-equivocada que devuelve cifra)
medida con un set de preguntas trampa en `eval/golden_queries.yaml` (`category: trap`) vía el
nuevo runner `eval/run_eval_queries.py` → debe bajar a ~0. KPI secundario: cobertura de queries
respondidas con cifra verificada (se acepta una baja moderada).

## Referencias

- Base académica y fuentes: [docs/NL2SQL_BASE.md](../NL2SQL_BASE.md)
- ADR-017 (arquitectura híbrida), ADR-018 (SoQL visible), ADR-009 (cifras desde filas)
- Memoria: `reference_nl2sql_academic_base`
