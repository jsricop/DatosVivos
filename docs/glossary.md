# Glosario — DatosVivos

Términos del dominio que aparecen en el código, la documentación y las conversaciones del proyecto. Útil para nuevos contribuidores y agentes de IA sin contexto previo.

## Datos públicos colombianos

### datos.gov.co
Portal de datos abiertos del Estado colombiano. Operado por MinTIC. Corre sobre la plataforma **Socrata**. DatosVivos integra su catálogo (nativos + federados) junto con los portales territoriales CKAN/DCAT y el geoportal del IGAC: **25.192 datasets de 1.423 entidades** al corte 2026-07-10 (se actualiza a diario; conteo vivo en `GET /api/v1/stats/panorama`).

### DIVIPOLA
División Político-Administrativa de Colombia. Sistema oficial de códigos del DANE para identificar departamentos (2 dígitos), municipios (5 dígitos), centros poblados, etc. Es la **clave canónica** para cruzar datasets de territorios.

Ejemplos: `05` = Antioquia, `05001` = Medellín, `25` = Cundinamarca.

Dataset de referencia: `gdxc-w37w` (DIVIPOLA-Códigos municipios).

### DANE
Departamento Administrativo Nacional de Estadística. Productor oficial de DIVIPOLA y de muchos datasets estadísticos clave.

### NIT
Número de Identificación Tributaria. Usado como clave para cruzar datasets sobre empresas/personas jurídicas.

### Entidad publicadora
La organización del Estado que publica un dataset en datos.gov.co. Aparece en el campo `attribution` de la metadata. Ejemplos: MinSalud, DNP, Gobernación de Antioquia, etc.

## Stack técnico

### Socrata
Plataforma cloud (hoy parte de Tyler Technologies) que muchos gobiernos del mundo usan para publicar datos abiertos. datos.gov.co es un cliente de Socrata, igual que NYC Open Data, Chicago Data Portal, data.gov (USA), etc.

### SODA API
Socrata Open Data API. Endpoint para **consultar datos** de un dataset. URL: `https://www.datos.gov.co/resource/{dataset_id}.json`. Acepta queries SoQL.

### Discovery API
API federada de Socrata para **buscar datasets** en todo el ecosistema. Endpoint: `https://api.us.socrata.com/api/catalog/v1`. Se puede filtrar por dominio (`domains=www.datos.gov.co`).

### Metadata API
API para obtener el **esquema** de un dataset (columnas, tipos, descripción). URL: `https://www.datos.gov.co/api/views/{dataset_id}.json`.

### SoQL
Socrata Query Language. Sintaxis similar a SQL para consultar datasets vía SODA API. Soporta `$select`, `$where`, `$group`, `$order`, `$limit`, `$offset`. Ejemplo:

```sql
SELECT dpto, count(*) AS n GROUP BY dpto ORDER BY n DESC LIMIT 5
```

### MCP (Model Context Protocol)
Protocolo abierto publicado por Anthropic en nov/2024 para estandarizar cómo los LLMs consumen tools externas. Define un formato JSON-RPC y transportes (stdio, SSE) para que un cliente (host del LLM) hable con un server (que expone las tools). Spec: <https://modelcontextprotocol.io>.

### FastMCP
Framework Python del SDK oficial de MCP para construir servers con decoradores. Lo usamos en `mcp_server/server.py`.

### Tool (MCP)
Función expuesta por un MCP Server al LLM. Tiene nombre, descripción en lenguaje natural, y un JSON Schema de input. El LLM lee este catálogo y decide cuándo y cómo llamarla.

### RAG
Retrieval-Augmented Generation. Patrón donde antes de generar respuesta, el LLM consulta un índice (típicamente vectorial) para traer contexto relevante. En DatosVivos lo usamos sobre los metadatos del catálogo (Sprint 2).

## Modelos y técnicas

### Backend LLM intercambiable (`LLM_BACKEND`)
El generador de lenguaje es un componente conectable: `anthropic` (API de Claude —
**backend de producción desde 2026-07-11**, modelo Haiku), `ollama` (modelo local,
opción para réplicas sin API key) o `mock` (tests). El resto del motor (verificación,
retrieval, plantillas) no cambia con el backend. La migración a Claude bajó la
interpretación NL de 31-45 s a 1.5-1.8 s.

### Ollama
Servidor local de modelos LLM que permite correr modelos cuantizados (GGUF) en CPU/GPU sin enviar datos a APIs externas. Fue el backend inicial; los modelos se retiraron de producción el 2026-07-11 (liberó 6.2 GB) y queda como opción local vía `LLM_BACKEND=ollama`.

### Qwen 2.5 Coder (3B / 7B, Q4_K_M)
Modelo LLM de Alibaba, especializado en código y consultas estructuradas. **Default operativo: 3B (~2 GB RAM)** para correr en hardware modesto del Estado; **upgrade documentado: 7B (~5 GB RAM)** vía `OLLAMA_MODEL` env var cuando hay GPU/RAM disponible. Genera SoQL, narrativa y reformulaciones Tier 3.

### Llama 3 8B (Q4_K_M)
Modelo LLM de Meta. Alternativa de fallback considerada para narrativa en español. No es default; documentado como swap posible via `OLLAMA_MODEL`.

### sentence-transformers / multilingual-e5-large
Modelo de embeddings multilingüe (Microsoft, familia `intfloat/multilingual-e5`) que mapea texto a vectores de **768 dimensiones** (variante `base`). Lo usamos para el clasificador de intención (centroides) y el índice vectorial de datasets.

### ChromaDB
Base de datos vectorial open-source. Persistencia en disco. Búsqueda por similitud coseno. Alternativa considerada: FAISS (ver ADR-005).

## Conceptos CRISP-ML(Q)

### CRISP-ML(Q)
Cross-Industry Standard Process for Machine Learning with Quality assurance. Metodología en 6 fases (Business Understanding, Data Understanding, Data Preparation, Modeling, Evaluation, Deployment & Monitoring). Requerida por el concurso.

### Precision@k
Métrica de búsqueda: fracción de resultados relevantes en los primeros k retornados. La usamos para evaluar el índice vectorial.

### Intent classification
Clasificación de la intención de una pregunta NL en un conjunto fijo de categorías. En DatosVivos: `search`, `descriptive`, `comparative`, `temporal`, `cross_source`.

## Búsqueda multi-tier (ADR-007)

### 3-tier search
Estrategia de búsqueda en cascada implementada en `mcp_server/socrata/discovery_client.py` + `topic_keywords.py` + `ai_engine/analyzer.py`. El ciudadano rara vez nombra a la entidad publicadora; los tres niveles compensan:

1. **Tier 1 — Acrónimos** (`acronyms.py`, 117 entidades / 562 aliases). Si la query menciona "DANE", se expande a "Departamento Administrativo Nacional de Estadística" antes de pegarle a Socrata.
2. **Tier 2 — Topic keywords iterativos** (`topic_keywords.py`, ~3 050 keywords). Si Tier 1 + Socrata directo retornan vacío, se itera grupos de 2 entidades temáticamente afines ordenadas por overlap.
3. **Tier 3 — Reformulación por LLM** (`analyzer._llm_reformulate`). Como último recurso, el LLM produce 3-5 keywords alternativas y se reintenta la búsqueda.

### Topic keywords
Diccionario de keywords temáticos por entidad. Generado data-driven desde el corpus indexado (TF-IDF sobre nombre + descripción + columnas) + suplementos manuales para casos críticos. Persistido en `mcp_server/socrata/topic_keywords_data.py`.

### Cross-datasets (N=1..5)
Tool MCP `cross_datasets` que integra entre 1 y 5 datasets vía `pandas.merge`. Soporta join por una o varias claves (típicamente `cod_dpto` o `cod_mpio`). Guardia anti-falsos-positivos: si los datasets no comparten valores en la clave, devuelve 0 filas en lugar de inventar joins.

### Golden assertion
Hecho del mundo real verificable contra fuente oficial, usado como criterio de aceptación en tests. Ejemplo: *Antioquia tiene 125 municipios en DIVIPOLA* — verificable contra el dataset `gdxc-w37w` del DANE.

## Cifras verificadas y validador de alucinaciones (ADR-009)

### StatsComputer
Módulo `ai_engine/stats_computer.py`. Calcula determinísticamente con pandas los estadísticos a partir de los rows reales devueltos por Socrata. Devuelve un `Statistics` con `total_rows`, `column_summaries` (uno por columna con kind = numeric|categorical|datetime|id), `aggregate_hits` (líneas de agregados detectados del SoQL), `summary_lines` (texto es-CO listo para mostrar), `whitelist_numbers` y `derived_numbers`.

### Statistics
Dataclass frozen con todos los productos del `StatsComputer.compute()`. Expuesto en `AnalysisResult.statistics`. El bloque "📊 Datos verificados" que ve el ciudadano se construye a partir de sus `summary_lines`.

### whitelist_numbers
Conjunto (`frozenset[str]`) de cifras que el LLM puede citar en su narrativa interpretativa. Se construye en `_build_whitelist` con: cada valor numérico literal de los rows + cada agregado calculado (count, min, max, mean, sum) + conteos y porcentajes top-N + año/fecha min/max para columnas temporales. Las cifras se normalizan canónicamente con `_normalize_number` para que "125.000" (es-CO miles) y "125000" se traten como la misma.

### derived_numbers
Conjunto análogo de cifras "derivadas razonables": deltas max-min, ratios top-N, número de períodos en series temporales, porcentajes redondeados (±0.5). Permite al LLM citar combinaciones evidentes sin que el validador las censure.

### Post-validador de cifras
`ai_engine/analyzer.py::_validate_numbers(text, stats)`. Extrae cada cifra del texto LLM con regex (excluye IDs como `gdxc-w37w`), normaliza es-CO, y censura la **oración entera** que contenga una cifra fuera de `whitelist ∪ derived`. Si todas las oraciones se censuran, fallback determinista "Consulta el bloque de datos verificados a continuación".

### Normalización es-CO de números
Heurística pragmática implementada en `_normalize_number`: si el último separador (.,) es seguido por **3 dígitos**, se trata como **miles** (`125.000` → `125000`). Si es seguido por 1-2 dígitos, se trata como **decimal** (`12.5` → `12.5`). Esto invierte la convención inglesa pero refleja el uso es-CO predominante en datos públicos colombianos.

## Geolocalización y comparativa multi-target (ADR-010)

### GeoResolver
Módulo `ai_engine/geo_resolver.py`. Detecta menciones a territorios colombianos en la pregunta del ciudadano y devuelve un `GeoContext` canónico. Cobertura inicial: 32 departamentos + Bogotá D.C. con sinónimos comunes + 39 capitales y mpios grandes. Fuzzy match con `difflib` (cutoff 0.78). Protección contra falsos positivos: lista negra de países extranjeros.

### GeoTarget
Dataclass frozen con `name`, `code` (DIVIPOLA o None si nivel nacional) y `level` (`"national"` | `"dpto"` | `"mpio"`). El `GeoContext.targets` es una lista de hasta 5 targets, usada para comparativas multi-target.

### GeoContext
Contexto geográfico resuelto. Expone `targets`, `comparison_mode`, `groupby`, `scope`, `confidence`, `notes`, `top_n`. Accessors retrocompatibles `dpto_code`/`dpto_name`/`mpio_code`/`mpio_name` que infieren del primer target del tipo correspondiente.

### comparison_mode
Tipo de comparativa detectada por GeoResolver. Valores:
- `"vs"`: dos o más territorios a comparar (`"compara A y B"`, `"A vs B"`).
- `"ranking"`: top-N o ranking (`"top 10 ciudades con más X"`).
- `"vs_national"`: target local vs agregado nacional (`"X respecto al promedio nacional"`).
- `None`: no es comparativa.

### Plantillas SoQL deterministas
Función `build_comparison_soql(ctx, columns)` en `geo_resolver.py`. Para `comparison_mode` no-None, construye el SoQL **sin pasar por LLM** usando los códigos/nombres del `GeoContext`. Reconoce columnas-código (`cod_dpto`, `codigo_dane_departamento`) y columnas-nombre (`departamento_del_hecho_dane`, `municipio`) con `lower(col) IN (...)` y variantes sin tildes.

### Regla anti-capital
Si la pregunta usa plural genérico (`"municipios"`, `"departamentos"`) Y nombra un dpto pero NO un mpio explícito, el resolver descarta los matches de mpios que sean capitales del dpto mencionado. Evita que `"municipios de Antioquia"` colapse a `Medellín`.

## Telemetría operativa Beta-1

### Telemetría CSV
Logger best-effort en `ai_engine/telemetry.py`. Persiste cada consulta en `data/telemetry/queries.csv` con schema fijo: `timestamp_iso, question, intent, datasets_used, soql_executed, rows_count, censored_count, elapsed_s, had_statistics`. Errores silenciosos (telemetría no debe tumbar el flujo). Migración planificada a PostgreSQL en `PROD_IMPROV.md#7`.

## Concurso / contexto

### Datos al Ecosistema 2026
Concurso de MinTIC para impulsar el uso de datos abiertos con IA. Cierre: 13 julio 2026. Sustentación: 14-17 julio. Finalistas: 24 julio. Final presencial: 1ra semana agosto.

### Reto 7 (id 102) — Innovación y Tecnología
"Diseñar asistentes virtuales que faciliten el acceso ciudadano a datos abiertos". Es el reto en el que participa DatosVivos: Equipo 93, Nivel Avanzado.

### ANI
Agencia Nacional de Infraestructura. Entidad para la cual trabaja el equipo. La Oficina de Tecnología lidera DatosVivos.

## Sistema visual (Beta-2)

### Civic Editorial
**(Superado por el sistema gov.co — ver abajo.)** Dirección estética adoptada en [ADR-012](./adr/012-civic-editorial-design-system.md) para el rebranding de Beta-2. Inspiración: periódico colombiano + atlas estadístico + gaceta oficial. Tipografía serif/sans/mono, paletas papel-tinta, bordes rectos. Reemplazado el 2026-06-24 por el sistema alineado con gov.co.

### Sistema gov.co (entidad pública moderna)
Identidad visual vigente, adoptada en [ADR-021](./adr/021-sistema-diseno-gov-co.md). Alinea DatosVivos con el registro del Estado colombiano: tipografía **Nunito Sans** (oficial gov.co) + IBM Plex Mono para datos, superficie blanca, azul institucional `#004884`, semánticos gov.co para el semáforo, barra GovHead con atribución **textual** (sin logo gov.co ni escudo — no estamos habilitados). Documento operativo: [`BRAND.md`](./BRAND.md).

### Token (de diseño)
Variable CSS expuesta bajo `:root[data-theme="..."]` con un nombre semántico estable (`--bg`, `--ink`, `--accent`, `--hairline`, `--focus-ring`, etc.). Su valor cambia entre modos de color; el nombre no. Todo CSS productivo en `web/` se escribe sobre tokens, nunca sobre hex literales.

### Hairline
Borde o regleta de 1px (1.5px para SVG, 2px en modo alto contraste). Color `var(--hairline)`. Se usa para separar paneles, filas de tabla y secciones — actúa como tipografía estructural, no como decoración. Sustituye a las sombras box-shadow que están prohibidas.

### Modo (light / dark / contrast)
Estado seleccionable por el usuario que cambia la tabla de valores de los tokens. `light` (papel crema + tinta, default), `dark` (tinta profunda + papel), `contrast` (B/N puro + acento saturado, con sub-variantes `contrast-light` y `contrast-dark`). Persistido en `localStorage` bajo `datosvivos:theme` y aplicado en `<html data-theme="...">`.

### IBM Plex
Familia tipográfica de IBM (libre, latín extendido completo, mantenida activamente). DatosVivos usa tres pesos del set: **Serif** (display, h1-h2, citas), **Sans** (body/UI, h3-h6), **Mono** (data, IDs, kickers, SoQL). Self-hosted en `web/public/fonts/`; está prohibido cargarla desde Google Fonts CDN.

### Kicker
Etiqueta corta en IBM Plex Mono uppercase con `letter-spacing: 0.08em` que precede a un título, eje de chips o sección. Ejemplos: `TEMA`, `TIPO DE PREGUNTA`, `TERRITORIO`, `ENTIDAD`, `FUENTES CONSULTADAS`, `LO MÁS CONSULTADO ESTA SEMANA`.

### Pleca
Carácter ASCII `|` que separa las dos mitades del wordmark `Datos|Vivos`. Se renderiza en `var(--accent)` para actuar como acento editorial. **No es decoración** — es estructura del wordmark; copiar/pegar el wordmark debe preservar la pleca.

### Wordmark
La forma escrita del nombre de marca. En DatosVivos es `Datos|Vivos` (Nunito Sans ExtraBold con pleca en `--accent` azul institucional). **No hay logo gráfico separado** — el wordmark es el logo, distinto del lockup gov.co (que no usamos).

### Anti-FOUC (Flash of Unstyled Content)
Patrón inspirado en GOV.UK: script inline en `<head>` lee `localStorage["datosvivos:theme"]` y aplica `data-theme` en `<html>` **antes** del hidrato de React. Evita que el usuario vea un parpadeo de modo claro cuando tiene modo oscuro guardado.

### SSE (Server-Sent Events)
Estándar HTTP nativo para streaming unidireccional servidor→cliente. Eventos `text/event-stream` con líneas `data: {...}\n\n`. DatosVivos lo usa para emitir progreso del LLM (`intent`, `dataset_hits`, `narrative_chunk`, `rows`, `citations`, `done`) durante los 30-90s que toma una consulta. Decisión: [ADR-013](./adr/013-fastapi-sse-vs-mcp-http.md).

### Cuneta de lectura
Ancho máximo de línea para texto continuo. `72ch` para narrativa (`<article>` en `/buscar`), `60ch` para manifiesto (`/acerca`). Garantiza legibilidad sin saltos visuales en pantallas anchas.

### Glifo tipográfico
Carácter Unicode usado como decoración estructural en sustitución de iconos: `·` (separador), `—` (em-dash), `→` (resultado), `↵` (submit), `▾` `▸` (acordeón), `¶` (referencia), `§` (sección), `|` (pleca). Renderizados en la propia tipografía del contexto — no son SVG.
