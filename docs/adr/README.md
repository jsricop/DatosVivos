# Architecture Decision Records (ADRs)

Decisiones de arquitectura del proyecto **DatosVivos**, extraídas como archivos individuales para que sean auditables sin depender del documento operativo interno `MAIN.md`.

Formato: cada ADR documenta **decisión + razón + trade-off** en formato breve. Adoptamos el espíritu del registro de decisiones — no buscamos prosa larga, sino constancia de por qué se eligió cada camino.

## Índice

| ADR | Título | Estado |
|---|---|---|
| [001](./001-ollama-local.md) | Ollama local en vez de API externa | Aceptada (modelo único superado por [ADR-015](./015-tiered-llm-models.md)) |
| [002](./002-streamlit-vs-react.md) | Streamlit en vez de React | Superada por [ADR-011](./011-migracion-streamlit-a-nextjs.md) |
| [003](./003-powerbi-analitica.md) | Power BI para analítica, no para interfaz principal | Superada por [ADR-008](./008-scope-sin-powerbi.md) |
| [004](./004-postgresql-vs-sqlite.md) | PostgreSQL en vez de SQLite | Aceptada (no activada en MVP) |
| [005](./005-chromadb-vs-pgvector.md) | ChromaDB en vez de pgvector | Aceptada |
| [006](./006-web-speech-api.md) | Web Speech API del navegador para accesibilidad | Aceptada |
| [007](./007-busqueda-3-tiers.md) | Búsqueda con fallback en 3 tiers (acrónimos + topic keywords + LLM) | Aceptada |
| [008](./008-scope-sin-powerbi.md) | Sprint 4 sin Power BI: scope solo Streamlit + accesibilidad | Superada por [ADR-014](./014-reabrir-powerbi-con-login.md) |
| [009](./009-cifras-pandas-whitelist.md) | Cifras solo desde pandas; LLM interpreta pero no inventa números | Aceptada |
| [010](./010-geo-resolver.md) | GeoResolver con DIVIPOLA + plantillas SoQL deterministas para comparativa | Aceptada |
| [011](./011-migracion-streamlit-a-nextjs.md) | Migración de Streamlit a Next.js para Beta-2 | Aceptada |
| [012](./012-civic-editorial-design-system.md) | Sistema de diseño Civic Editorial (papel & tinta) | Aceptada |
| [013](./013-fastapi-sse-vs-mcp-http.md) | FastAPI + SSE como contrato Next.js ↔ Python (no MCP HTTP) | Aceptada |
| [014](./014-reabrir-powerbi-con-login.md) | Reabrir Power BI con login institucional embebido (PostgreSQL activo) | Aceptada |
| [015](./015-tiered-llm-models.md) | Tiered LLM models por task (Qwen 3B fast + Qwen 7B narrative) | Aceptada |
| [016](./016-narrative-corta-expandible.md) | Narrativa corta+expandible con streaming real (TTFB ≤ 1s) | Aceptada |

## Sobre los estados

- **Aceptada:** la decisión está vigente y reflejada en el código.
- **Superada:** la decisión original existió, pero una posterior la modifica. Conservamos el ADR original para trazabilidad histórica.
- **Rechazada:** considerada pero descartada. Útil para que no se vuelva a discutir.

## Cómo agregar un ADR nuevo

1. Crear `NNN-titulo-corto.md` con el mismo formato que los existentes.
2. Agregarlo al índice de esta página.
3. Si supera a uno previo, marcar el previo como "Superada por [ADR-NNN]".
