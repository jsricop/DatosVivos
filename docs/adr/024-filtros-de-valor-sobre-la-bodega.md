# ADR-024: Filtros de valor sobre la bodega + diccionario ciudadano↔institucional

**Estado:** Aceptada
**Fecha:** 2026-07-13
**Relacionada:** [ADR-017](./017-arquitectura-hibrida-ia-determinista.md) (chips deterministas
— este ADR los extiende HACIA DENTRO del dataset), [ADR-022](./022-motor-nl2sql-generativo-verificado.md)
(garantía anti-alucinación — se preserva íntegra), migración 027 (bodega Parquet — este ADR
es la razón de ser de esa bodega: no solo velocidad, sino consulta y filtrado).

## Contexto

Los chips (TEMA/TIPO/TERRITORIO) filtran el **catálogo** — eligen QUÉ dataset responde —
pero no filtran las **filas** del dataset elegido. El ciclo ciudadano de 50 preguntas dejó
el patrón claro: "¿Cuántos colegios **públicos** hay en Boyacá?" respondía 2.184 (oficiales
+ no oficiales), "¿en **2024**?" respondía el histórico completo, y una pregunta
departamental sobre un dataset nacional sobre-contaba el país entero. Sin filtros, la bodega
de 10.280 Parquet (6,6 GB) era solo un acelerador de latencia.

Además, el diagnóstico transversal (2026-07-13): las correcciones venían siendo puntuales
porque faltaban tres piezas estructurales — el vocabulario ciudadano↔institucional vivía
solo en un prompt (probabilístico, no testeable), y no existía mecanismo alguno de recorte
dentro del dataset.

## Decisión

**Filtrar dentro del dataset con valores REALES del dato, nunca con SQL escrito por un
LLM.** Cuatro fases sobre la bodega Parquet, más el diccionario como capa transversal:

### Fase 1 — Perfil de filtrables (determinista)

`scripts/profile_filter_values.py` precalcula con DuckDB, por cada Parquet descargado:
- **kind='valor'**: valores de columnas de texto de baja cardinalidad (2..30 distintos),
  excluyendo identificadores y valores-basura (NR, N/A, …).
- **kind='anio'**: años presentes en columnas fecha nativas.

Resultado en `dataset_filter_values` (migración 028): el **catálogo de lo filtrable**.
Bootstrap inicial: 10.280 datasets → 297.275 valores en ~7 min. Mantenimiento: incremental,
enganchado al ETL diario tras el farmeo (solo re-perfila parquets nuevos/refrescados).

### Fase 2 — Chips de filtro en la UI

`GET /datasets/{id}/filters` expone el perfil; `FilterBar` pinta chips por columna
("SECTOR: OFICIAL · 1.721 | NO OFICIAL · 463"). Un filtro por columna, URL compartible
(`?filtro=col:valor`). `execute` **valida cada (col, value) contra el perfil**: lo que no
existe exacto se descarta con nota honesta. Con filtro en un conteo se devuelve también el
total sin filtrar ("1.721 de 2.184") — la escala nunca se oculta.

### Fase 3 — Auto-filtro desde la pregunta

`execute` recibe la pregunta original; el LLM (Haiku, camino de producto) recibe las
columnas filtrables **con sus valores exactos** y solo puede señalar pares de esa lista
(máx. 2). "públicos" → `SECTOR=OFICIAL`. Todo par fuera del perfil se descarta. El SQL lo
sigue armando el template — el LLM elige, nunca escribe. En la UI el auto-filtro aparece
como chip activo removible; si el usuario toca los filtros, la pregunta deja de mandar.

### Fase 4 — Territorio dentro del dataset

Pregunta departamental + dataset **nacional** → se busca el nombre canónico del
departamento entre los valores de las columnas geo del Parquet (comparación normalizada
sin tildes); si existe, `WHERE departamento = <valor tal cual está almacenado>`.
Determinista, sin LLM, verificado contra el dato. Sin match → sin filtro. Esto convierte
"dataset nacional sobre-cuenta" en "dataset nacional recortado al territorio".

### Diccionario ciudadano↔institucional (transversal)

`ai_engine/vocabulario_ciudadano.py`: ~130 pares curados del ciclo de 50 preguntas
("colegios"→"establecimientos educativos", "robos"→"hurto", "plata"→"presupuesto").
Expande de forma **determinista** el word-boost y el texto del re-ranking semántico en
`query_chips`. El prompt del mapper mantiene la instrucción equivalente como refuerzo,
pero el piso ya no depende del LLM. Cada par nuevo es testeable.

## Por qué así

- **Solo rama bodega**: el perfil describe las columnas del Parquet (encabezados del CSV),
  que no coinciden con los field-names de SODA. Filtrar en vivo con un perfil ajeno sería
  mentir. Si la bodega no aplica, se responde sin filtro Y se dice.
- **Valores exactos, no interpretados**: `OFICIAL` se compara y se inyecta tal cual está
  en el dato (ident whitelisted + comilla doblada). La cadena de verificación de ADR-022
  no se rompe en ningún punto.
- **DuckDB, no pandas**: predicate pushdown sobre Parquet local (~71 ms), un solo motor de
  ejecución ya probado, cero copias en memoria.

## Consecuencias

- "¿Cuántos colegios públicos hay en Boyacá?" responde **1.721** (de 2.184) con el WHERE
  visible — antes respondía 108 (dataset municipal equivocado) y luego 2.184 (sin filtro).
- Preguntas con año/sector/territorio dejan de ser el grupo "débil" del ciclo ciudadano
  (c36, c48, c50 eran exactamente esto).
- Costo operativo: +1 llamada Haiku por consulta CON pregunta (~1,5 s); el perfil añade
  ~300k filas a Postgres y minutos al ETL diario.
- Deuda consciente: filtros solo-bodega (federados en vivo sin filtro), municipios aún no
  (solo departamentos en F4 — la cardinalidad municipal no cabe en el perfil; se resolverá
  con el mismo patrón de verificación directa contra el Parquet si se necesita).
