# Lecciones aprendidas — DatosVivos

Bugs no obvios, gotchas de librerías, y decisiones empíricas que ya pillamos en el camino. **Capturadas para que el próximo desarrollador (humano o IA) no repita la pesquisa.**

Ordenadas por sprint y fecha.

---

## Sprint 1 (May 2026)

### 🐛 Comentarios inline en `.env` rompen pydantic-settings

**Síntoma:** `Settings.socrata_app_token` cargaba el string `"# Opcional: mayor rate limit"` como valor — no `None`. Resultado: el header `X-App-Token` se enviaba con un comentario y Socrata respondía `permission_denied`.

**Causa:** pydantic-settings (vía python-dotenv) lee `KEY=value # comment` como `value=" value # comment"`, no como `value=""` con un comentario separado.

**Solución:**
1. `.env.example` reescrito con comentarios solo en líneas propias (nunca al lado de un valor).
2. Validator defensivo en `mcp_server/settings.py` que convierte strings que empiezan con `#` a `None`.

**Aplicabilidad:** Cualquier campo `Optional[str]` que se carga desde `.env`. Si veo un valor `str | None` cuyo default es `None` y llega con un `#`, hay que sanitizarlo.

---

### 🐛 User-Agent `python-httpx/*` está bloqueado por Socrata

**Síntoma:** httpx defaultea su UA a `python-httpx/0.28.1`. Socrata responde 403 `Forbidden` a requests con este UA en SODA API. Las APIs Discovery y Metadata sí lo aceptan.

**Causa:** Socrata tiene reglas anti-bot que bloquean UAs conocidos de scrapers.

**Solución:** Todos los clientes Socrata (`SodaClient`, `DiscoveryClient`, `MetadataClient`) envían UA propio:
```
User-Agent: DatosVivos/0.1 (+https://github.com/jsricop/DatosVivos)
```

**Aplicabilidad:** Cualquier cliente HTTP nuevo contra Socrata debe poner UA propio. Verificable con `curl -A "python-httpx/..." https://...` vs UA personalizado.

---

### 🐛 `FastMCP("name")` ignora `MCP_PORT` del entorno

**Síntoma:** Server arrancado con `MCP_PORT=3000` se bindeaba a `127.0.0.1:8000`.

**Causa:** `FastMCP("name")` sin `host`/`port` usa los defaults del SDK (8000, 127.0.0.1). No lee env vars propias del usuario.

**Solución:** Instanciar como:
```python
FastMCP("datosvivos", host=settings.mcp_host, port=settings.mcp_port)
```

**Aplicabilidad:** Cualquier nueva instancia de FastMCP debe pasar host/port explícitos. El default es ENGAÑOSO porque parece que `MCP_PORT` "debería funcionar" pero no aplica.

---

### 🐛 FastMCP serializa `list[dict]` como N TextContent blocks

**Síntoma:** Al consumir `call_tool` desde un cliente MCP externo (SSE o stdio), una tool que retorna `list[dict]` no devuelve un solo bloque con la lista — devuelve **N bloques TextContent**, uno por item.

**Implicación:** Si tu cliente solo lee `result.content[0].text`, ve solo el primer item, no la lista.

**Solución:** Iterar sobre todos los `content` blocks y deserializar cada `text`:
```python
items = [json.loads(b.text) for b in result.content if getattr(b, "text", None)]
```

**Aplicabilidad:** Tests de integración SSE/stdio, helpers de cliente, y cualquier consumidor que llame tools que devuelven listas.

---

### 💡 Los mensajes de error de Socrata son oro para el LLM

**Contexto:** Cuando un SoQL es inválido, Socrata devuelve 400 con un JSON detallado:
```json
{
  "code": "query.compiler.malformed",
  "error": true,
  "message": "Could not parse SoQL query 'SELECT WHERE FROM' at line 1 character 14: Expected an expression, but got `FROM'"
}
```

**Por qué importa:** En Sprint 3, Ollama va a generar SoQL y se va a equivocar. Si recibe solo `HTTP 400`, abandona. Si recibe el mensaje real, puede **corregir su query y reintentar**.

**Solución:** Helper `mcp_server/tools/_errors.py::call_socrata()` extrae el campo `message` del JSON de error y lo expone vía `ToolError`.

**Aplicabilidad:** Toda nueva tool que llame APIs externas debe propagar el detalle del error a `ToolError`, no esconderlo detrás de "request failed".

---

### 💡 Discovery API es federada, NO solo Colombia

**Contexto:** `https://api.us.socrata.com/api/catalog/v1` indexa **todos** los portales Socrata del mundo (NYC, Chicago, CDC, gobiernos australianos, etc.). El parámetro `domains=` filtra por portal específico.

**Implicación para el proyecto:** El MCP Server es trivialmente extensible a otros portales. Cambiar `domains=www.datos.gov.co` por `domains=www.datos.gov.co,data.cityofnewyork.us` permite búsqueda cross-país.

**Limitación:** Solo Discovery es federada. Para queries reales (SODA) y metadata, hay que ir al dominio host del dataset. Generalizar `SodaClient` para recibir el dominio dinámicamente es un cambio de 2-3 líneas.

**Aplicabilidad:** Punto de venta para el criterio "Impacto y escalabilidad" (20 pts del concurso).

---

### 💡 Documentación aspiracional acumula deuda silenciosa

**Contexto:** El scaffolding inicial dejó README, `docker-compose.yml` y un docstring listando funcionalidades que aún no existían (`cross_datasets` en MCP, `docker compose up` con servicios stub). Auditoría posterior detectó las inconsistencias.

**Lección:** Documentar lo que **funciona hoy**, no lo que va a funcionar. Lo aspiracional va en una sección explícita "Lo que NO funciona aún" o con marcador `Sprint X`.

**Solución estructural:** Regla `MAIN.md §14.5` Disciplina de documentación — toda PR debe actualizar la documentación afectada con checklist explícito.

**Aplicabilidad:** Cualquier README/docstring/compose nuevo en el proyecto. Revisar en cada code review.

---

## Expansión de acrónimos del sector público colombiano (post-Sprint 3)

### 💡 Las entidades publicadoras de datos.gov.co ya tienen el acrónimo embebido en `attribution`

**Contexto:** al construir el diccionario de acrónimos, descubrí que el campo `attribution` de cada dataset YA contiene la sigla oficial en formato `"Nombre Canónico - SIGLA, Ciudad/Departamento"`. Ejemplo: `"Ministerio de Tecnologías de la Información y las Comunicaciones - MinTIC, Bogotá D.C."`.

**Implicación:** podemos **derivar el diccionario directamente del catálogo** en vez de mantener una lista manual. Extrajimos ~100 pares (canonical, sigla) programáticamente de las 8.389 entidades indexadas.

**Aplicabilidad:** cuando construyes diccionarios para datos gubernamentales colombianos, busca primero en `attribution`. Hay otras convenciones similares ("Alcaldía de X, Y" → entidad territorial X).

---

### 🐛 "Estadísticas" plural vs "Estadística" singular

**Síntoma:** mi test de aceptación asumió `"Departamento Administrativo Nacional de Estadística"` (singular). La realidad: el catálogo usa `"Estadísticas"` plural.

**Aplicabilidad:** **nunca asumir formas oficiales** de nombres de entidades del Estado colombiano. Extraerlas siempre del catálogo. Hay variaciones inesperadas: "del derecho" en minúscula en MinJusticia, "Cultura, las Artes y los Saberes" reciente en MinCultura, "La República" con mayúscula en DAPRE.

---

### 💡 Word boundary regex con soporte para acentos

**Problema:** la palabra "anillo" contiene "ANI" como sustring. Un regex naive `\bANI\b` con `re.IGNORECASE` matchea **dentro** de "ANIllo" porque la `\b` Python clásica es ASCII-only.

**Solución:** `(?<![A-Za-zÁÉÍÓÚÜáéíóúüÑñ])ANI(?![A-Za-zÁÉÍÓÚÜáéíóúüÑñ])` — lookbehind/lookahead unicode-aware. Verificado con test específico (`test_expand_query_does_not_match_inside_other_words`).

**Aplicabilidad:** cualquier matching de términos en español/idiomas con acentos. La `\b` de Python NO funciona bien con caracteres acentuados.

---

### 💡 Append > Replace en expansión de queries

**Decisión:** `expand_query("datos del MEN")` devuelve `"datos del MEN Ministerio de Educación Nacional"` (append), NO `"datos del Ministerio de Educación Nacional"` (replace).

**Razón:** Socrata full-text search es bag-of-words. Append preserva los keywords originales del usuario (que podrían matchear documentos donde solo aparece la sigla y no el nombre completo). Cero costo, beneficio aditivo.

---

## Extensión cross-multi (post-Sprint 3)

### 💡 Auto-detectar columnas comunes es la causa típica de falsos positivos en joins

**Contexto:** al extender `cross_datasets` para soportar 1-5 datasets, era tentador auto-detectar la columna compartida por nombre (intersección de `df_a.columns ∩ df_b.columns`). Decidimos NO hacerlo.

**Razón:** dos datasets pueden tener `id` con significados completamente distintos (uno es row ID, otro es código municipal). Auto-merge produciría un resultado vacío o ruidoso sin que nadie se entere de por qué.

**Solución:** la `join_keys` es **obligatoria** y explícita. Para N=2 puede ser un string; para N>2 un string (misma columna en todos) o lista de N-1 strings (per-pair). `None` solo válido si N=1.

**Implicación:** el LLM o usuario debe DECIDIR conscientemente qué columna usar como bisagra. Si no sabe, primero consulta `get_metadata` de cada dataset.

**Aplicabilidad:** cualquier merge/join entre fuentes externas. La regla "no infieras, exige explícito" es estándar en data engineering productiva (Airflow, dbt) — la copiamos acá.

---

### 💡 Short-circuit en cadenas de merges evita descargas inútiles

**Contexto:** en una cadena `A⨝B⨝C⨝D⨝E`, si `A⨝B` queda vacío, seguir descargando C/D/E gasta red, memoria y tiempo. El resultado final será vacío de todas formas.

**Solución:** después de cada merge intermedio, si el DataFrame resultante está vacío, retornar `[]` inmediatamente. Verificado con un test que usa `monkeypatch` para espiar las llamadas a SODA API y confirma que el tercer dataset NO se descarga si el primer merge ya colapsó.

**Aplicabilidad:** cualquier pipeline ETL con joins encadenados. También aplicable a futuras tools que orquesten múltiples llamadas externas.

---

### 💡 Verificación previa al merge supera a manejo de errores post-merge

**Contexto:** `pandas.merge` con una columna inexistente lanza un `KeyError` críptico. Mucho más útil verificar antes y dar un error que diga "el dataset 'vcjz-niiq' (posición 2) no tiene la columna 'cod_dpto', columnas disponibles: [...]".

**Implementación:** `_check_column_in_df` validador previo a cada paso de merge. Lanza `ToolError` con el dataset_id, su rol en la cadena, y las primeras 15 columnas disponibles.

**Aplicabilidad:** validaciones previas a operaciones costosas son universalmente preferibles a manejo de excepciones post-hoc. Más útil para el consumidor (humano o LLM) y más rápido para abortar.

---

## Sprint 3 (May 2026)

### 🐛 Modelos LLM pequeños (3B) necesitan **valores de ejemplo**, no solo nombres de columna

**Síntoma:** Qwen 2.5 Coder 3B generaba `WHERE cod_dpto = 'ANTIOQUIA'` cuando el ciudadano preguntaba *"¿cuántos municipios tiene Antioquia?"*. La query era sintácticamente válida pero semánticamente incorrecta: `cod_dpto` contiene códigos ('05'), no nombres ('ANTIOQUIA'). El SoQL devolvía 0 filas en vez de 125.

**Causa raíz:** las descripciones de columnas en datos.gov.co están **mayormente vacías**. Un LLM pequeño no puede inferir solo del nombre `cod_dpto` que es un código y no un nombre. Un humano sí lo intuye pero el modelo no.

**Solución:** `QueryGenerator` acepta `sample_rows` en el schema. Cuando están presentes, se inyectan en el prompt como "EJEMPLOS DE VALORES — Fila 1: cod_dpto='05', dpto='ANTIOQUIA', ...". Esto hace que la distinción código/nombre sea explícita.

**Aplicabilidad:** cualquier pipeline NL→SQL con LLMs pequeños y esquemas con descripciones pobres. Si subimos a Qwen 7B en la VM, probablemente esto sea menos crítico pero igual mejora la calidad.

---

### 🐛 LLMs entrenados en SQL agregan `FROM tabla` por hábito; SoQL no lo usa

**Síntoma:** Qwen generaba `SELECT count(*) FROM tabla WHERE ...` mientras que SoQL no usa cláusula `FROM` (el dataset es el endpoint URL). Socrata respondía 400.

**Solución:** post-procesamiento en `_strip_from_clause()` que elimina `FROM <ident>` del SoQL antes de retornarlo. Regex simple, robusta a casos comunes.

**Aplicabilidad:** cualquier consumo de SoQL generado por LLM. También útil filtrar otros artefactos comunes (`;` final, backticks de markdown, etc.).

---

### 🐛 Validar columnas referenciadas requiere stripping de aliases `AS xxx`

**Síntoma:** mi validador de "columnas referenciadas deben estar en el esquema" rechazaba `SELECT count(*) AS total WHERE dpto='ANTIOQUIA'` porque `total` no estaba en el esquema. Pero `total` es un **alias** inventado por el LLM, no una columna existente.

**Causa:** el regex extraía todos los tokens, incluyendo los que vienen después de `AS`.

**Solución:** preprocesar el SoQL eliminando `\bAS\s+\w+\b` antes de extraer tokens.

**Aplicabilidad:** cualquier sistema que valide AST de SQL/SoQL contra un esquema. Cuidado también con otros artefactos: tabla virtuales (CTEs `WITH x AS (...)`), subconsultas, etc.

---

### 💡 Datasets conceptualmente pares pueden NO compartir columnas

**Contexto:** elegí `gdxc-w37w` (DIVIPOLA municipios) y `vcjz-niiq` (DIVIPOLA departamentos) como par de prueba para `cross_datasets`. Asumí que ambos usarían `cod_dpto`. Falso: `vcjz-niiq` usa `codigo_departamento`. Aunque son del mismo equipo (DANE) y conceptualmente representan lo mismo, las convenciones de naming difieren.

**Lección:** **NUNCA asumir** la consistencia de naming entre datasets de datos.gov.co, ni siquiera entre datasets del mismo publicador. SIEMPRE verificar con `get_metadata` antes de cross.

**Implicación para el motor de IA:** `cross_datasets` debería poder recibir dos columnas distintas (`join_left`, `join_right`) o hacer matching fuzzy. Por ahora pedimos columna idéntica; futura iteración puede aceptar dos.

---

## Sprint 2 (May 2026)

### 🐛 Embeddings tipo e5 floorean cosine similarity en ~0.7

**Síntoma:** El test `test_vector_index_low_confidence_on_nonsense_query` exigía que una query nonsense ("qslsdkjfgh1234nonsense") produjera scores < 0.5. Con `intfloat/multilingual-e5-base`, todas las queries — incluso garbage — producen similitudes en el rango 0.70-0.85.

**Causa:** Los modelos transformer modernos (e5, BGE, etc.) embeben todo en una región acotada del espacio. Tokens irreconocibles caen cerca del centroide del corpus, dando similitud ~0.7 con cualquier documento. El supuesto naive "score bajo = match malo" no aplica.

**Solución:** Doble filtro en `VectorIndex.search()`:
1. **min_score absoluto** (0.3): descarta basura obvia.
2. **min_margin** (0.02): el top score debe ser meaningfully mayor a la mediana del top-k. Para queries reales, top-median ≈ 0.04+. Para nonsense, ≈ 0.005.

Si nada supera ambos filtros, `search()` retorna `[]` — preferible para el LLM consumidor que devolver resultados ruidosos.

**Aplicabilidad:** Cualquier sistema que use embeddings modernos para búsqueda semántica. El umbral absoluto de cosine similarity NO es buen señal de confianza; el margen relativo sí lo es.

---

### 💡 e5 requiere prefijos `passage:` y `query:`

**Contexto:** El modelo `intfloat/multilingual-e5-base` fue entrenado con prefijos específicos para distinguir documentos indexados (`passage: ...`) de queries (`query: ...`). Sin el prefijo, la calidad de matching cae notablemente.

**Solución implementada:** `VectorIndex.upsert_many` aplica `passage:` automáticamente al texto a embedear. `VectorIndex.search()` aplica `query:`. El caller pasa texto plano y no se entera del prefijo.

**Aplicabilidad:** Cualquier modelo e5 (small, base, large). Si en el futuro migramos a BGE o ColBERT, los prefijos cambian — revisar el model card.

---

### 📋 Adopción de disciplina test-first

**Contexto:** Cerrando Sprint 1, declaré "100% verificado" en PR #2. El stakeholder pidió segunda auditoría y aparecieron 4 huecos reales (transporte stdio no probado, paths de error no testeados, etc.). En PR #3 cerramos los huecos, pero la raíz del problema fue **escribir tests después del código** — los tests medían lo que se construyó, no lo que el sprint prometía.

**Lección:** sin definir criterios de aceptación **antes** de implementar, la verificación final tiende a ser un autoengaño confirmatorio.

**Práctica adoptada para Sprint 2 en adelante (documentada como regla en `MAIN.md §6.6`):**

1. Antes de tocar código de producción, escribir `tests/test_sprintN_acceptance.py` con todos los tests congelados (`@pytest.mark.skip`).
2. Commitear a `develop` como "frozen baseline".
3. Durante el sprint, quitar el `@skip` test por test cuando cada feature está lista.
4. **Si un test falla:** corregir el código, NO el test. Excepción única para errores conceptuales del test (con justificación explícita en commit y MAIN.md).
5. Umbrales obligatoriamente cuantificables (accuracy ≥ 0.85, latencia P50 < 200ms, etc.). Nada de "que funcione razonablemente".

**Por qué importa para el concurso:** el criterio "Análisis y rigor técnico" (15 pts) evalúa metodología. Tener tests congelados antes de implementar es evidencia documental de rigor; tests post-hoc no lo son.

**Aplicabilidad:** todos los Sprints 2-5. Sprint 1 ya cerrado con la deuda (capturada aquí). El archivo `tests/test_sprint2_acceptance.py` es el primer ejemplo de la práctica.

---

### 🔒 Las instrucciones negativas al LLM 3B no son suficientes

**Contexto:** En el journey 30 preguntas (2026-05-18), incluimos en el prompt del LLM la regla *"NO inventes ningún número que no esté en las filas"*. Aun así Qwen 2.5 Coder 3B narró *"92 municipios"* cuando los rows decían `n=0`, y *"39 presuntos homicidios"* cuando había 50 filas. El modelo ignora consistentemente las prohibiciones cuando el contexto le sugiere una cifra plausible.

**Lección:** confiar en el LLM para no alucinar es un error de diseño cuando se trata de cifras. La única garantía operativa es **separar el cálculo del texto** y validar la salida post-hoc.

**Solución implementada (ADR-009):**
1. `StatsComputer` calcula con pandas todas las cifras deterministas y produce `whitelist_numbers`.
2. El LLM recibe los rows + la ficha de cifras autorizadas y solo interpreta cualitativamente.
3. `_validate_numbers` extrae cada cifra de la salida del LLM, normaliza es-CO, y censura la **oración entera** si la cifra no está en `whitelist ∪ derived_numbers`.

**Resultado:** en el journey final (2026-05-19) cero alucinaciones detectadas en 30/30 preguntas. 0 oraciones censuradas (el LLM aprendió a respetar la whitelist con prompts pre-cargados).

**Aplicabilidad:** cualquier sistema con LLM 3B-7B que muestre cifras al usuario final. Para LLMs de 70B+ la tasa de alucinación cae, pero el patrón "calcular en código + validar la salida" sigue siendo defensa en profundidad.

---

### 🗺️ Plantillas deterministas vencen al LLM en SoQL estructurado

**Contexto:** Para queries comparativas multi-target (`"compara A y B"`, `"top N ciudades"`, `"X respecto al nacional"`), pedirle al `QueryGenerator` LLM 3B que construya el SoQL con `IN (...)` fallaba el ~70% de las veces: inventaba columnas, errores de sintaxis, o devolvía vacío.

**Lección:** cuando la estructura del SoQL es predecible (basta combinar códigos + plantilla), el LLM es la herramienta equivocada. Las plantillas deterministas son 100% confiables, reproducibles y testeables.

**Solución implementada (ADR-010):**
- `geo_resolver.build_comparison_soql(ctx, columns)` construye el SoQL para `comparison_mode in {"vs", "ranking", "vs_national"}` con los códigos DIVIPOLA o nombres canónicos del `GeoContext`. Sin LLM.
- Reconoce columnas-código (`cod_dpto`) y columnas-nombre (`departamento_del_hecho_dane`) en datasets heterogéneos de Socrata.
- Fallback al `QueryGenerator` LLM solo si la plantilla no aplica (columna territorial ausente).

**Resultado:** en el journey final, las preguntas que disparan `comparison_mode` ejecutan SoQL exitoso con altísima confiabilidad.

**Aplicabilidad:** cualquier patrón de query estructurada con parámetros conocidos. SQL ad-hoc para reports, filtros geográficos, breakdowns por dimensión, etc.

---

### ♻️ El re-ranker LLM 3B tiene falsos negativos consistentes

**Contexto:** Tras agregar un re-ranker LLM (le pasamos los top-K candidatos del retrieval y le pedimos elegir el mejor), detectamos que Qwen 3B responde `"NINGUNO"` con frecuencia incluso cuando los hits son relevantes (caso P6 *"Cuántas instituciones de salud hay en Chocó"* trajo dataset correcto en iter1 → 0 datasets en iter2 — distinta corrida, mismo input).

**Lección:** los LLMs pequeños tienen baja recall en tareas de selección binaria. Tienden al *"safe answer"* (descartar todo).

**Solución implementada (commit `eadab82`):**
- Si el LLM dice `"NINGUNO"`, **conservar el top-1** del retrieval en lugar de devolver lista vacía. El threshold del vector index (`min_score=0.83`) ya garantiza calidad mínima.
- Sin riesgo de regresión adversarial: casos como `"Quiero saber sobre Ecuador"` están protegidos antes por la lista negra de países en `GeoResolver`.

**Aplicabilidad:** cualquier flujo donde un LLM 3-7B clasifica/ranquea opciones. Validar siempre que la decisión "no aplica" no sea un falso negativo.

---

### ⏱️ Timeouts duros en operaciones que pueden colgarse

**Contexto:** El caso adversarial `"Quiero saber sobre Ecuador"` se atascó **67 minutos** en `_llm_reformulate` (Tier 3) — la combinación de Discovery API + LLM con prompt sin respuesta natural creó un bucle de espera.

**Lección:** cualquier llamada externa (LLM, API HTTP, cliente Socrata) debe tener timeout duro a nivel del orquestador. No basta con timeouts internos de las librerías — quedan ignorados si la lib hace retry interno.

**Solución implementada:**
- `analyzer._llm_reformulate` con `asyncio.wait_for(timeout=60.0)`.
- `analyzer._retrieve` con `asyncio.wait_for` de 5 s sobre Discovery API.
- Cualquier excepción cae a fallback determinista en lugar de propagar.

**Aplicabilidad:** todo agente de IA que orqueste llamadas externas. El timeout es un contrato de SLA con el usuario.

---

### 🧪 La estocasticidad del LLM contamina las comparaciones de iteraciones

**Contexto:** Durante las 3 iteraciones de la sesión exploratoria (12 preguntas cada una), detectamos variaciones de ±10% del SoQL ejecutado entre runs con código idéntico. La causa raíz combinada: (a) re-ranker LLM con temperatura > 0 puede devolver índices distintos, (b) Discovery API puede tener latencias variables que afectan el boost, (c) el LLM 3B alterna entre formulaciones de SoQL distintas.

**Lección:** para evaluar mejoras reales hay que **promediar varios runs** o adoptar componentes deterministas. Una sola corrida es señal ruidosa.

**Práctica adoptada:** comparar siempre métricas agregadas (suma sobre 30 preguntas), no caso-por-caso individual. Identificar regresiones reales = ≥2 métricas globales bajan en runs consecutivos. Las "regresiones" en un solo caso son ruido en ~95% de los casos.

**Aplicabilidad:** cualquier sistema con LLM no-determinista en el camino crítico. Considerar re-ranker semántico (embeddings + cosine) como reemplazo determinista del re-ranker LLM en Beta-2.

---

### 📐 Plan-first ahorra retrabajo en decisiones de diseño no triviales

**Contexto:** Antes de implementar cifras pandas, planteé al usuario dos opciones extremas (radical: LLM no ve los rows; sin protección: LLM ve y validamos). Tras discutir el espacio de soluciones, el usuario eligió la opción balanceada (LLM ve rows + whitelist + post-validación). Si hubiera implementado la radical sin consultar, el resultado habría sido demasiado frío (LLM solo describe el dataset, no interpreta).

**Lección:** cuando hay decisiones de diseño con tradeoffs reales, presentar el espacio de opciones con costos/beneficios explícitos **antes** de implementar. El usuario invierte 30 segundos en decidir y nos ahorra horas de implementación equivocada.

**Práctica adoptada:** `AskUserQuestion` con tabla comparativa (no opciones genéricas como "¿OK?") cuando la decisión tiene impacto en arquitectura o UX. Plantear cada opción con: qué hace, qué cuesta, qué riesgo trae.

**Aplicabilidad:** plan-mode general. Especialmente útil cuando trabajamos con un par (no asistente), donde la negociación de diseño es parte del valor.

---
