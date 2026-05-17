# 01 — Business Understanding

> CRISP-ML(Q) — Fase 1. Define el problema, los stakeholders, los KPIs y por qué tiene sentido usar IA aquí.

## Resumen en una frase

DatosVivos quiere que **cualquier persona** pueda preguntarle a [datos.gov.co](https://www.datos.gov.co) en su idioma natural y obtener una respuesta **verificable**, sin tener que aprender SoQL, sin tener que adivinar qué entidad publicó qué, y **sin perder accesibilidad** para quien usa lector de pantalla o entrada por voz.

---

## 🏛️ Para el jurado MinTIC

### Alineación con el reto

El concurso *"Datos al Ecosistema 2026: IA para Colombia"* — **Reto #07: Innovación y Tecnología** — pide explícitamente: *"Diseñar asistentes virtuales que faciliten el acceso ciudadano a datos abiertos"*. DatosVivos no se limita a un chatbot decorativo: **ejecuta consultas reales sobre el portal de datos abiertos del Estado**, expone esa capacidad como herramienta interoperable (MCP) y respeta el marco normativo colombiano de accesibilidad.

### Criterios de evaluación cubiertos

| Criterio | Cómo lo abordamos | Evidencia |
|---|---|---|
| **Innovación** | Primer agente de datos abiertos colombiano que se publica como **MCP server** (Model Context Protocol), reutilizable por Claude Desktop, Gemini, Cursor y agentes propios. | [07_mcp_integrations.md](./07_mcp_integrations.md) |
| **Reproducibilidad** | Todo el stack es open source, dockerizado, con tests de aceptación frozen por sprint (80+ tests verdes). | `Dockerfile.mcp`, `Dockerfile.streamlit`, `tests/` |
| **Soberanía técnica** | LLM ejecutado **localmente** (Ollama + Qwen 2.5 Coder 3B/7B). Ninguna consulta ciudadana sale a proveedores cloud. | `ai_engine/llm_backend.py`, [04_modeling.md](./04_modeling.md) |
| **Accesibilidad** | Cumple **Ley 1618 de 2013** y **WCAG 2.1 AA**: STT/TTS en `es-CO`, alt-text auto, navegación por teclado, alto contraste. | [accessibility.md](../accessibility.md), `app/components/accessibility/` |
| **Verificabilidad** | Cada respuesta cita el `dataset_id` y la SoQL ejecutada; el usuario puede reproducir la consulta. | `ai_engine/analyzer.py` — `AnalysisResult` |
| **Cobertura del catálogo** | Índice vectorial cubre los **8 389 datasets** públicos de datos.gov.co al momento de la entrega. | `scripts/build_index.py`, [02_data_understanding.md](./02_data_understanding.md) |

### Restricciones normativas asumidas

- **Ley 1581 de 2012 / Decreto 1377 de 2013** (datos personales): el agente solo consulta datasets públicos publicados por entidades; **no recolecta** información personal del usuario.
- **Ley 1712 de 2014** (Ley de Transparencia y Acceso a la Información Pública): respaldo legal para que cualquier persona pueda consultar el catálogo; DatosVivos baja la barrera técnica de ejercer ese derecho.
- **Ley 1618 de 2013** (estatuto de discapacidad): la accesibilidad no es un *nice-to-have*, es requisito.

---

## 🛠️ Para ciudadanos técnicos

### Problema real, no problema imaginado

Antes de escribir código, observamos tres fricciones que existen hoy cuando un ciudadano intenta usar datos.gov.co:

1. **No sabe qué entidad publicó el dato.** Pregunta *"¿cuántos municipios hay en Antioquia?"* sin saber que ese dato es responsabilidad del DANE en el dataset `gdxc-w37w`. El portal pide búsquedas exactas o filtrado manual por entidad.
2. **No conoce SoQL.** El portal expone una API potente (Socrata), pero requiere conocer la sintaxis `SELECT cod_dpto, count(*) AS n GROUP BY cod_dpto`. Una persona promedio no escribe eso.
3. **No puede cruzar entidades fácilmente.** Combinar un dataset del INVÍAS con uno del DANE por código DIVIPOLA implica descarga + script ad-hoc + manejo de tipos. Inviable para no-técnicos.

### Por qué un agente con LLM (y no una UI tradicional)

Una UI con filtros y combos cubriría el caso simple, pero el ciudadano no piensa en filtros — piensa en *preguntas*. Un LLM bien orquestado:

- Traduce **lenguaje natural → SoQL** ejecutable.
- Decide **qué datasets** consultar contra el catálogo.
- Sabe **cuándo cruzar** datasets (vía `cross_datasets`).
- **Narra** los resultados en español comprensible.

La pieza diferencial es que **el LLM no inventa datos**: solo formula consultas. Los datos vienen siempre de las APIs reales de Socrata. Esto se respalda en el código por el patrón "el LLM genera SoQL, el cliente lo ejecuta contra `datos.gov.co`" (`ai_engine/query_generator.py` + `mcp_server/socrata/soda_client.py`).

### Stakeholders

| Stakeholder | Qué necesita | Cómo lo entrega DatosVivos |
|---|---|---|
| **Ciudadano sin conocimientos técnicos** | Una respuesta clara, en español, con la fuente. | UI Streamlit con chat, modo accesible, exportación CSV. |
| **Periodista / investigador** | Reproducibilidad: poder citar la consulta. | Cada respuesta muestra `dataset_id`, SoQL y permalink. |
| **Equipo de tecnología de una entidad** | Reutilizar la inteligencia del agente en sus propios sistemas. | MCP server publicado → cualquier cliente MCP puede consumirlo. |
| **Persona con discapacidad visual** | Interfaz con STT/TTS y alt-text. | Modo accesible activable desde sidebar. |
| **Auditor del concurso** | Verificar que no hay trucos. | Repo público, tests de aceptación, ADRs, lessons_learned. |

### KPIs cualitativos del MVP

No definimos KPIs cuantitativos arbitrarios (% precisión sobre golden set sintético), porque sesgarían el diseño hacia ese golden set. En su lugar usamos **criterios de aceptación verificables**:

- ✅ Una pregunta sobre DIVIPOLA devuelve el dataset `gdxc-w37w` y los 125 municipios de Antioquia exactos.
- ✅ Una pregunta temática sin nombre de entidad (*"datos sobre vacunación"*) encuentra resultados vía el fallback de topic keywords (Tier 2).
- ✅ Un cruce de dos datasets por DIVIPOLA produce filas correctas (no falsos positivos).
- ✅ El modo accesible activa STT/TTS en `es-CO`.
- ✅ Un usuario con Claude Desktop puede agregar este MCP en 5 minutos y consultar el catálogo (capítulo 07).

Todos esos criterios son tests automatizados que viven en `tests/test_sprint{1..4}_acceptance.py` y se pueden re-ejecutar.

---

## 👥 Para ciudadanía general

### ¿Qué problema resuelve esto?

El Estado colombiano publica miles de datasets en [datos.gov.co](https://www.datos.gov.co): información sobre municipios, salud, transporte, educación, infraestructura, ambiente, contratación pública. Pero **encontrar y usar esa información requiere saber buscar como técnico**: hay que saber cuál entidad publica qué, cuál es el nombre exacto del dataset, y a veces hay que escribir consultas en un lenguaje técnico llamado SoQL.

**DatosVivos elimina esa barrera.** Tú haces tu pregunta como hablas:

> *"¿Cuántos hospitales hay en Cundinamarca?"*  
> *"¿Cuáles departamentos tienen más vías terciarias?"*  
> *"Muéstrame los datos de calidad del aire de Bogotá."*

Y el agente:

1. Entiende tu pregunta.
2. Busca en el catálogo cuál o cuáles datasets responden.
3. Consulta esos datasets en tiempo real contra `datos.gov.co`.
4. Te responde en español, con un gráfico o un mapa cuando aplica.
5. Te muestra de dónde salió la información para que puedas verificar.

### ¿Qué NO hace?

Para que sepas a qué atenerte:

- **No inventa cifras.** Si un dato no existe en datos.gov.co, te lo dice; no se lo imagina.
- **No tiene opiniones políticas.** Solo te da los datos públicos.
- **No guarda tus preguntas en un servidor externo.** El modelo de IA corre en una máquina local del proyecto, así tus consultas no salen del país.
- **No reemplaza a un analista.** Es una herramienta de acceso, no de auditoría. Si vas a tomar una decisión importante, verifica los datos directamente con la entidad publicadora.

### ¿Quién lo puede usar?

- Cualquier persona con un navegador (interfaz Streamlit).
- Personas con discapacidad visual: el modo accesible se activa con un *click* en el sidebar y habilita entrada por voz y narración de las respuestas.
- Investigadores, periodistas, estudiantes, funcionarios.
- Desarrolladores que quieran integrar este agente en sus propias herramientas (ver [capítulo 07](./07_mcp_integrations.md)).

---

## Siguiente capítulo

[02 — Data Understanding](./02_data_understanding.md): cómo es el catálogo de datos.gov.co, qué encontramos al inspeccionarlo y qué decisiones tomamos a partir de eso.
