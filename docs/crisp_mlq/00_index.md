# DatosVivos — Documentación CRISP-ML(Q)

Esta carpeta es la entrega documental del proyecto **DatosVivos** para el concurso *"Datos al Ecosistema 2026: IA para Colombia"* del Ministerio TIC (Reto #07 — Innovación y Tecnología). Equipo: **ANI** (Agencia Nacional de Infraestructura).

DatosVivos es un agente de IA con **modelo local** (Ollama / Qwen 2.5 Coder) que permite a cualquier persona consultar [datos.gov.co](https://www.datos.gov.co) en **lenguaje natural**, cruzar datasets de múltiples entidades y obtener análisis verificables con visualizaciones y modo accesible.

## Cómo navegar esta documentación

Cada capítulo tiene **tres lentes** explícitos para que cada audiencia entre por la suya:

| Lente | Para quién | Qué encuentra |
|---|---|---|
| 🏛️ **Para el jurado MinTIC** | Evaluadores del concurso | Alineación con las bases, criterios cumplidos, evidencia. |
| 🛠️ **Para ciudadanos técnicos** | Equipos de TI de entidades, devs, analistas | Decisiones técnicas, código, ADRs, reproducibilidad. |
| 👥 **Para ciudadanía general** | Cualquier persona | Qué pueden hacer con el agente, ejemplos, limitaciones honestas. |

## Mapa de capítulos

Seguimos la metodología **CRISP-ML(Q)** — *CRoss-Industry Standard Process for Machine Learning with Quality assurance* — adaptada a un agente conversacional sobre datos abiertos.

| # | Capítulo | Pregunta que responde |
|---|---|---|
| [01](./01_business_understanding.md) | Business Understanding | ¿Qué problema resuelve y para quién? |
| [02](./02_data_understanding.md) | Data Understanding | ¿Cómo es el catálogo de datos.gov.co? |
| [03](./03_data_preparation.md) | Data Preparation | ¿Qué hicimos con esos datos para que la IA los entendiera? |
| [04](./04_modeling.md) | Modeling | ¿Qué modelos usamos y por qué? |
| [05](./05_evaluation.md) | Evaluation | ¿Cómo sabemos que funciona y qué limitaciones tiene? |
| [06](./06_deployment.md) | Deployment | ¿Cómo se despliega y opera en producción? |
| [07](./07_mcp_integrations.md) | **Capítulo especial: MCP e integraciones** | ¿Cómo conectar este agente con Claude, Gemini u otros LLMs? |

## Cómo verificar lo que afirmamos

Cada decisión y resultado en estos documentos está respaldado por código real en este repositorio:

- 📂 **Código fuente:** `mcp_server/`, `ai_engine/`, `app/`, `scripts/`
- 🧪 **Tests:** `tests/` (más de 80 tests, incluyendo aceptación por sprint)
- 📜 **Documentación viva:** [architecture.md](../architecture.md), [accessibility.md](../accessibility.md), [glossary.md](../glossary.md), [lessons_learned.md](../lessons_learned.md)
- 🏷️ **ADRs:** decisiones de arquitectura registradas en `MAIN.md §9` (privado del equipo)

## Resumen de la propuesta en una página

- **Local-first:** el LLM corre en una máquina del estado (Ollama + Qwen 2.5 Coder). No depende de proveedores cloud para responder. Sin filtración de consultas ciudadanas a terceros.
- **Sobre las APIs públicas:** todo lo que ve el agente sale de las APIs Socrata de `datos.gov.co` (SODA, Discovery, Metadata). No hay datos sintéticos.
- **MCP nativo:** las 4 herramientas (`search_datasets`, `get_metadata`, `query_data`, `cross_datasets`) se exponen como **MCP server**, así que cualquier cliente MCP (Claude Desktop, Cursor, agentes de Google, clientes propios) puede consumirlo. Ver [capítulo 07](./07_mcp_integrations.md).
- **Búsqueda con 3 tiers:** acrónimos del sector público → topic keywords iterativos → reformulación por LLM. Cubre el caso real de que el ciudadano no diga el nombre de la entidad.
- **Cruces verificados:** `cross_datasets` integra 1–5 datasets via `pandas.merge` con guardias contra falsos positivos.
- **Accesible por diseño:** modo accesible con entrada/salida por voz (Web Speech API `es-CO`) y alt-text auto-generado. Cumple Ley 1618 de 2013 y WCAG 2.1 AA.

— Para cualquier ruta de lectura, **el capítulo 01 es el mejor punto de entrada**.
