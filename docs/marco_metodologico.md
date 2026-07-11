# Marco metodológico — CRISP-ML adaptado

> Cifras al corte del **2026-07-10**; el catálogo se actualiza a diario.

Seguimos **CRISP-ML(Q)** (Cross-Industry Standard Process for Machine Learning with
Quality assurance), la evolución de CRISP-DM recomendada por el concurso, **adaptada a
un sistema de IA en producción continua**: DatosVivos no entrena un modelo sobre un
dataset estático — opera un catálogo vivo que se refresca a diario, con componentes de
IA generativa verificada. Las adaptaciones se explicitan en cada fase.

## Fase 1 — Entendimiento del negocio y de los datos

- **Problema**: falta de panorama consolidado del ecosistema de datos abiertos
  (ver [planteamiento del problema](planteamiento_problema.md)).
- **Exploración de fuentes**: catálogo Socrata de datos.gov.co (Discovery API + SODA +
  Metadata API), portales CKAN (Bogotá, Cali, Valle), DCAT (MEDATA Medellín) y
  federación del geoportal IGAC. Se caracterizó cobertura de metadata por fuente
  (p. ej. los federados de datos.gov.co no declaran sector; los portales CKAN sí).
- **Criterio de éxito**: que un decisor responda "¿cuántos datasets tiene mi entidad y
  cuántos al día?" en segundos, y que un ciudadano obtenga cifras verificables en
  lenguaje natural.
- *Adaptación*: el "dato" aquí es doble — la **metadata del catálogo** (25.192
  registros) y las **filas de los datasets** consultados bajo demanda.

## Fase 2 — Preparación de los datos (donde la IA depura y consolida)

Ingesta y consolidación continua en PostgreSQL (una fila por dataset, upsert
idempotente por `dataset_id` — verificado por auditoría: 0 duplicados de clave):

- **ETL diario** contra la Discovery API (nativos + federados de datos.gov.co) y
  **harvesting semanal** CKAN/DCAT de los portales territoriales.
- **Calidad verificada columna a columna**: auditoría contra la fuente Socrata con
  17/18 columnas al 100 % de fidelidad (reportes en [`eval/reports/`](../eval/reports/)).
- **IA aplicada a la depuración, consolidación y definición de casos de calidad**:
  - clasificación automática de **reportes administrativos** (Ley 1712) que separa el
    inventario de cumplimiento de los datos temáticos — enganchada al ETL, re-evalúa
    todo el catálogo en cada corrida;
  - **curación de columnas** (tipos semánticos: dimensión/métrica/fecha/geo) combinando
    heurísticas y clasificación con LLM;
  - **inferencia territorial DIVIPOLA**: asignación de departamento/municipio a cada
    dataset a partir de su metadata, con nivel de confianza registrado;
  - **guardas anti-basura**: descarte de metadata placeholder sin diligenciar
    (títulos `{{name}}`) antes de que contamine el catálogo;
  - deduplicación investigada del solapamiento cross-portal (copias federadas del mismo
    recurso), con atribución por portal de origen.
- Vistas curadas (`v_dataset_status_decisor`, `v_entity_summary_decisor`) como fuente
  única del tablero y del panorama — ver [diccionario de datos](diccionario_datos.md).

## Fase 3 — Modelado (el motor de IA)

Componentes, organizados por nivel del producto:

**En los tableros (panorama + Power BI):** los modelos de la fase 2 (clasificadores de
calidad, curación, inferencia geográfica) definen las dimensiones analíticas: semáforo
de frescura (regla `verde ≤ frecuencia declarada · amarillo ≤ 2× · rojo > 2×`),
composición temáticos/administrativos, acceso, cobertura territorial.

**En el buscador (la pieza central de IA):**
- **NL2SQL / Text-to-SQL generativo con verificación determinista de 3 capas**
  (ADR-022, basado en la literatura PV-SQL 2025-2026): el LLM genera la consulta viendo
  solo columnas curadas reales; un verificador de código (no otro LLM) valida
  existencia de columnas, semántica y seguridad **antes** de ejecutar; hay ciclo de
  reparación y, si no se puede verificar, **refusal** (la respuesta se niega antes que
  inventarse).
- **Retrieval semántico**: embeddings `multilingual-e5` sobre ChromaDB (~8.400 datasets
  tabulares indexados) para elegir el dataset correcto.
- **Clasificador de intención** (conteo/comparación/ranking/tendencia/mapa) y mapeo
  NL→chips deterministas como camino estructurado.
- **Narrativa anti-alucinación**: toda cifra de la respuesta se valida contra la lista
  calculada sobre las filas reales; un número que no esté en ella censura la oración.
- **MCP server**: las herramientas del motor (búsqueda, metadata, consulta, cruce) se
  exponen con el estándar abierto MCP para cualquier agente de IA externo.
- *Adaptación*: en lugar de "entrenar y congelar", el modelado es un **pipeline
  generación→verificación** donde la garantía de calidad es determinista.

## Fase 4 — Evaluación

- **Golden sets** versionados ([`eval/golden_queries.yaml`](../eval/golden_queries.yaml),
  [`eval/golden_chips.yaml`](../eval/golden_chips.yaml)) con corridas reproducibles y
  16 reportes históricos en `eval/reports/`.
- **35 archivos de pruebas automatizadas** (`tests/`): verificador SoQL, validador de
  números, reparación de consultas, geo/DIVIPOLA, harvesting, servidor MCP, rutas API.
- El **verificador es también el filtro de curación**: solo sobreviven respuestas cuya
  cifra se calcula de filas reales — la evaluación está embebida en el producto.

## Fase 5 — Despliegue

Producción en `datosvivos.co` sobre infraestructura del Estado: contenedores Docker con
imagen horneada (reproducible), PostgreSQL, FastAPI, Next.js, Power BI embebido
(publish-to-web) y túnel seguro de salida. Ver [guía de validación](validation_guide.md).

## Fase 6 — Monitoreo (la Q de CRISP-ML(Q))

- **Actualización diaria automática**: cron del ETL cada madrugada + harvesters
  semanales. El panorama nunca se desactualiza — se cura solo; las cifras del sitio
  son en vivo, jamás quemadas.
- **Semáforo de frescura** como métrica de salud permanente del catálogo.
- **Telemetría anónima** de consultas ciudadanas ("lo más consultado") sin datos
  personales.
- Clasificación de calidad re-ejecutada en cada corrida del ETL (idempotente), de modo
  que los datasets nuevos quedan catalogados sin intervención humana.

## Resumen de adaptaciones a CRISP-ML

| CRISP-ML canónico | Adaptación en DatosVivos |
|---|---|
| Dataset de entrenamiento estático | Catálogo vivo re-ingestado a diario |
| Entrenar → validar → congelar modelo | Generar (LLM) → **verificar (código)** → ejecutar, en cada consulta |
| Métricas de test una vez | Evaluación embebida: golden sets + verificador en producción |
| Monitoreo de deriva del modelo | Monitoreo de deriva del **catálogo** (semáforo de frescura) |
