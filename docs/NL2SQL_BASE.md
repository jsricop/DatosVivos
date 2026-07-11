# NL2SQL — base académica y técnica

> Fundamento del motor "Generativo + verificado" de DatosVivos (ver [ADR-022](./adr/022-motor-nl2sql-generativo-verificado.md)).
> Escaneo del estado del arte realizado 2026-06-25.

## 1. Qué es (y qué NO es) NL2SQL

**NL2SQL (text-to-SQL) es un *área de problema*, no un estándar ni una librería que se instala.**
Lo que existe:

- **Benchmarks** que definen y miden el problema: **Spider 1.0**, **Spider 2.0**, **BIRD**,
  EHRSQL, ScienceBenchmark. Son la vara de medir, no código adoptable.
- **Librerías/frameworks**: LangChain/LangGraph SQL agents, **Vanna.ai** (RAG sobre esquema),
  **LlamaIndex** (`NLSQLTableQueryEngine`, *object retrieval* para esquemas grandes),
  **sqlcoder/Defog** (modelo afinado a SQL, self-host), Google NL2SQL Studio.
- **Servicios cerrados**: Snowflake Cortex Analyst, Databricks Genie.

### Por qué DatosVivos lo hizo "a mano" (y fue correcto)
Todas esas librerías asumen **dos cosas que el caso DatosVivos rompe**:
1. **SQL estándar sobre una base que controlas.** DatosVivos consulta mayormente **SoQL** (el
   dialecto restringido de Socrata sobre HTTP, sin `FROM`, sin `EXPLAIN`, con funciones propias
   como `date_trunc_ym`). Las librerías genéricas **no hablan SoQL**. Solo la rama federada
   (DuckDB) es SQL casi-estándar.
2. **Un esquema único y conocido.** DatosVivos tiene **~10k datasets remotos**, cada uno con su
   esquema. *Elegir el dataset correcto es media tarea* — la hace el `Analyzer` (retrieval
   híbrido: vector + Discovery API + boosts geográficos). **Ningún framework NL2SQL hace ese
   paso**; empiezan donde ya sabes la tabla.

**Conclusión:** se adoptan **patrones**, no frameworks.

## 2. El "performance cliff" (por qué la verificación es obligatoria)

- Benchmarks fáciles (**Spider 1.0**): 85-92% accuracy. Benchmarks realistas (**BIRD**,
  **Spider 2.0**): **6-21%** según modelo. Caída de ~75%.
- **Causa #1 = el caso DatosVivos:** *schema-linking a escala* (de 5 tablas a 500+ tablas /
  10k+ columnas → errores combinatorios). El fallo típico: *"resultados plausibles pero
  incorrectos"* — exactamente el riesgo que el motor verificado ataca.
- Otras causas: ambigüedad semántica sin capa de métricas ("silent logical errors"); esquemas
  sucios; fragilidad ante renombres de columna.
- **Recomendaciones del campo** (mapean 1:1 a DatosVivos): limitar alcance a vistas curadas;
  **capa semántica de métricas predefinidas** (= los templates por TIPO); validación multi-agente;
  human-in-the-loop para cifras sensibles; sandboxing read-only; **precisión sobre cobertura**.

## 3. Modelos SOTA (y dónde aplican)

- **Arctic-Text2SQL-R1** (Snowflake): #1 en BIRD; modelos 7B/14B/32B; entrenado por RL con
  recompensa = **corrección de ejecución**; self-hosteable.
- **sqlcoder / Defog**: modelo afinado a SQL, local, para entornos privados.
- **Aplicabilidad a DatosVivos:** un modelo especializado en SQL solo ayuda en la **rama DuckDB**
  (SQL real). Para **SoQL** (no estándar) rinde menos que un generalista con buen prompting +
  verificación. **El diferenciador es la verificación, no el modelo.**

## 4. Los 3 patrones adoptados (verificación)

Investigación 2025-2026: PV-SQL, G²SQL, MAGIC, SQLCritic, COVE, LatentRefusal, Boundary-Aware NL2SQL.

### 4.1 Verificación de 3 capas (PV-SQL)
1. **Sintaxis** — parse sin ejecutar (en DatosVivos: parser SoQL heurístico; DuckDB: `sqlglot`).
2. **Ejecución** — captura errores de tipo/runtime (en DatosVivos: `LIMIT 0` contra SODA, porque
   SoQL no tiene `EXPLAIN`).
3. **Restricciones semánticas** — extrae la intención por patrones (10 tipos: Distinct, Top-K,
   Ranking, Count, Percent, Sum, Average, Extreme, Temporal, Compare) y verifica que el SQL la
   cumpla vía análisis del AST. *"Precisión sobre cobertura"* (99.39% en el paper).

### 4.2 Bucle de reparación (reparar > rechazar)
Hasta ~5 iteraciones con **mensajes de error dirigidos** al LLM (no regenera desde cero).
~91% de reparación exitosa, 8.7% de regresión.

### 4.3 Refusal / boundary-aware
Detectar preguntas **no respondibles** y **rehusar** en vez de inventar. Es el fundamento del
fallback "No puedo afirmar esto con confianza" / "No encontré datos".

## 5. Cómo se instancia en DatosVivos

| Patrón del campo | Implementación DatosVivos | Archivo |
|---|---|---|
| Capa semántica / métricas predefinidas | templates por TIPO (5 formas) | `ai_engine/soql_templates.py` |
| Extracción de restricciones | `QueryConstraints` desde NL | `ai_engine/query_constraints.py` (NEW) |
| Verificación 3 capas | `verify_soql()` | `ai_engine/soql_verifier.py` (NEW) |
| Bucle de reparación | `generate_verified()` | `ai_engine/query_generator.py` |
| Refusal + degradación | decisión en `_execute_soql` + evento SSE | `ai_engine/analyzer.py`, `api/routes/query.py` |
| Human-in-the-loop ("esto entendí") | evento SSE `interpretation` | `web/src/components/InterpretationBlock.tsx` (NEW) |
| Fuente de verdad de tipos de columna | `dataset_columns_curated` | `ai_engine/column_classifier.py` |
| Eval con preguntas trampa | KPI falsos-verificados | `eval/run_eval_queries.py` (NEW) |

## 6. Fuentes

- The Text-to-SQL Performance Cliff (2026) — https://medium.com/@visrow/the-text-to-sql-performance-cliff-2026-why-natural-language-to-sql-breaks-a7281a23dbea
- Arctic-Text2SQL-R1 (Snowflake) — https://www.snowflake.com/en/engineering-blog/arctic-text2sql-r1-sql-generation-benchmark/
- PV-SQL: Probing + Rule-based Verification — https://arxiv.org/html/2604.17653v1
- G²SQL: guarded two-stage verification — https://www.sciencedirect.com/science/article/abs/pii/S0957417426001892
- LatentRefusal: refusing unanswerable text-to-SQL — https://arxiv.org/pdf/2601.10398
- SQLCritic: clause-wise correction — https://arxiv.org/pdf/2503.07996
- MAGIC: self-correction guideline — https://arxiv.org/pdf/2406.12692
- Natural Language to SQL: Complete 2026 Guide (Vanna/LlamaIndex/sqlcoder) — https://www.blazesql.com/blog/natural-language-to-sql
