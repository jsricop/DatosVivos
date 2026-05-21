# ADR-013: FastAPI + SSE como contrato Next.js ↔ Python (no MCP HTTP)

**Estado:** Aceptada
**Fecha:** 2026-05-20

## Decisión

El frontend Next.js (`web/`) consume el motor IA a través de **FastAPI** expuesto en `api/` con endpoints versionados bajo `/api/v1/*`. Las respuestas del LLM se transmiten al cliente con **Server-Sent Events (SSE)**. El MCP server (`mcp_server/`) **no se reutiliza** como API HTTP de la SPA.

Endpoints nuevos (extender `api/main.py` y `api/routes/`):

| Método | Ruta | Función | Streaming |
|---|---|---|---|
| `POST` | `/api/v1/query` | Consulta NL principal; orquesta `ai_engine.Analyzer` | **SSE** con eventos `intent`, `dataset_hits`, `narrative_chunk`, `rows`, `citations`, `done` |
| `GET` | `/api/v1/datasets/{id}` | Metadata + preview de dataset | No |
| `GET` | `/api/v1/suggest?axis=tema\|tipo\|territorio\|entidad` | Pobla los ChipGroup | No |
| `GET` | `/api/v1/popular` | Top consultas de telemetría real | No |
| `GET` | `/api/v1/divipola` | Códigos DIVIPOLA para dropdowns de territorio | No |
| `GET` | `/api/v1/health` | Liveness (ya existe) | No |

## Razón

El MCP server hoy expone 4 tools (`search_datasets`, `get_metadata`, `query_data`, `cross_datasets`) sobre transporte stdio o SSE para que **clientes MCP** (Claude Desktop, Cursor, agentes Gemini, otros LLMs) lo consuman. Su contrato es JSON-RPC + MCP spec, no un contrato HTTP REST/SSE para una SPA. Reusarlo como API de Next.js significaría:

- **Confundir audiencias del contrato.** Cambios para mejorar la SPA podrían romper a clientes MCP externos (Claude Desktop). El capítulo `docs/crisp_mlq/07_mcp_integrations.md` declara MCP como diferencial — debe quedar intacto.
- **Forzar a Next.js a hablar JSON-RPC.** Adiciona complejidad y dependencias innecesarias (cliente MCP en TS) para una superficie HTTP que sería trivial con FastAPI.
- **Perder validación zod-compatible.** FastAPI genera schemas OpenAPI que se sincronizan con TS via `openapi-typescript`. MCP RPC no tiene ese pipeline en TS.
- **Perder control de CORS, rate-limit y CSRF.** Esos viven en HTTP standards, no en MCP.

Además, la latencia 30-90s del motor IA (Ollama + búsqueda 3-tier + pandas) exige **streaming visible** al usuario. SSE es:

- Soportado nativamente por navegadores (`EventSource`) y Next.js (Route Handlers con `ReadableStream`).
- Más simple que WebSocket — unidireccional, sin estado de conexión persistente, sin auth handshake.
- Compatible con HTTP/2 multiplexing.
- Reconectable automáticamente desde el cliente.

El `api/` scaffold ya existe (`main.py`, `models/`, `routes/health.py`, `routes/query.py`) — solo se extiende. Reusa `ai_engine.Analyzer` exactamente como hoy `app/agent_client.py`.

## Trade-off

- **Dos servicios Python en compose.** `mcp_server` (puerto 3000, transporte SSE/stdio) + `api` (puerto 8000, HTTP/SSE). Mitigación: ambos son `uvicorn`, livianos, comparten dependencias (`requirements.mcp.txt` ya cubre lo común). Compose ya gestiona ambos.
- **Duplicación lógica.** Ambos servicios pueden recibir "ejecuta búsqueda" — uno desde un LLM, otro desde la SPA. Mitigación: ambos llaman al mismo `ai_engine.Analyzer`; la lógica vive ahí, no en el transporte.
- **SSE en serverless.** En despliegues serverless tradicionales (Vercel default) SSE tiene timeouts agresivos. Mitigación: no usamos serverless; el deploy va a la VM del Estado con FastAPI en uvicorn detrás de Nginx (sin proxy buffering).
- **Versionado.** `/api/v1` queda comprometido a estabilidad de contrato. Futuras versiones requieren `/api/v2`. Aceptable; es la convención que el equipo ANI quiere mantener para integraciones externas.

## Eventos SSE del endpoint `/api/v1/query`

Cada evento es un objeto JSON serializado en una línea `data: {...}`, seguido por `\n\n`.

| Evento | Payload | Cuándo |
|---|---|---|
| `intent` | `{intent: "count\|compare\|ranking\|trend\|map", confidence: number}` | Tras clasificación de intención |
| `dataset_hits` | `{datasets: [{id, name, entity, score}]}` | Tras búsqueda 3-tier |
| `narrative_chunk` | `{text: string}` | Tokens del LLM en streaming Ollama |
| `rows` | `{count: number, columns: [...], preview: [row,...]}` | Tras ejecución SoQL + pandas |
| `citations` | `{citations: [{n, dataset_id, url, apiUrl}]}` | Tras validación whitelist y censura |
| `error` | `{code, message}` | En fallo recuperable (motor sigue) o irrecuperable |
| `done` | `{elapsed_s: number}` | Cierre del stream |

## Referencias

- [ADR-011](./011-migracion-streamlit-a-nextjs.md) — migración Streamlit → Next.js
- [ADR-007](./007-busqueda-3-tiers.md) — búsqueda multi-tier que el SSE expone como eventos
- [ADR-009](./009-cifras-pandas-whitelist.md) — validador post-LLM que emite `citations`
- [`api/`](../../api/) — scaffold FastAPI existente (a extender)
- [`mcp_server/server.py`](../../mcp_server/server.py) — server MCP (canal separado, no se toca)
- [`app/agent_client.py`](../../app/agent_client.py) — referencia de orquestación del Analyzer
- [`docs/crisp_mlq/07_mcp_integrations.md`](../crisp_mlq/07_mcp_integrations.md) — capítulo que motiva mantener MCP intacto
