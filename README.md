# DatosVivos

Agente de IA con modelo local que permite a cualquier ciudadano hacer preguntas en lenguaje natural sobre los datos públicos de Colombia, ejecutando consultas reales sobre [datos.gov.co](https://www.datos.gov.co), cruzando datasets de múltiples entidades y entregando análisis verificables con visualizaciones.

Incluye un **modo de accesibilidad** para personas con discapacidad visual: entrada por voz y respuestas narradas.

> **Concurso "Datos al Ecosistema 2026: IA para Colombia"** — Reto #07 (Innovación y Tecnología). Equipo: Oficina de Tecnología de la **ANI** (Agencia Nacional de Infraestructura).

## Arquitectura objetivo

Tres capas:

1. **MCP Server** — expone tools sobre las APIs de Socrata de datos.gov.co. Sprint 1 entrega 3 tools (`search_datasets`, `get_metadata`, `query_data`); `cross_datasets` se agrega en Sprint 3.
2. **Motor de IA** — clasificador de intención (embeddings) + índice vectorial de metadatos + generador local (Ollama / Qwen 2.5 7B). **Sprints 2-3.**
3. **Interfaces** — Streamlit para ciudadanos (chat + Plotly + Folium + voz), Power BI para analítica de uso. **Sprint 4.**

## Stack objetivo

Python 3.11+ · FastAPI · MCP SDK · Ollama (Qwen 2.5 Coder 7B) · sentence-transformers · ChromaDB · PostgreSQL 16 · Streamlit · Plotly · Folium · Docker Compose · Nginx

## Estado actual (2026-05-15)

| Capa | Sprint | Estado |
|---|---|---|
| MCP Server (3 tools sobre datos.gov.co) | 1 | ✅ Funcional, 16 tests verdes |
| Motor de IA (índice vectorial + clasificador) | 2 | 🔜 Por iniciar |
| `cross_datasets` (cruce por DIVIPOLA/DANE) | 3 | 🔜 |
| Ollama integration | 3 | 🔜 |
| Streamlit + Power BI + accesibilidad | 4 | 🔜 |
| Docs CRISP-ML(Q) | 5 | 🔜 |

## Estructura

```
mcp_server/   Capa 1 — MCP Server + clientes Socrata    (Sprint 1: ✅)
ai_engine/    Capa 2 — Clasificador, vector index, LLM   (Sprints 2-3)
app/          Capa 3 — Streamlit + accesibilidad         (Sprint 4)
api/          FastAPI backend                            (Sprint 4)
db/           Schema PostgreSQL + migraciones            (Sprint 4)
scripts/      Indexación, mantenimiento                  (Sprint 2)
docs/         Documentación CRISP-ML(Q)                  (Sprint 5)
tests/        Pruebas pytest                             (continuo)
```

## Lo que funciona hoy

```bash
# 1. Clonar y preparar entorno
git clone https://github.com/jsricop/DatosVivos.git
cd DatosVivos
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.mcp.txt -r requirements-dev.txt

# 2. Configurar entorno (opcional para el MCP Server — funciona con defaults)
cp .env.example .env
# editar .env si necesitas un SOCRATA_APP_TOKEN para mayor rate limit

# 3. Correr los tests (16 tests, ~8s, requieren internet)
pytest

# 4. Levantar el MCP Server (elige un transporte)
MCP_TRANSPORT=stdio python -m mcp_server.server     # para hosts MCP locales
MCP_TRANSPORT=sse   python -m mcp_server.server     # HTTP/SSE en :3000

# 5. Build y run vía Docker
docker build -f Dockerfile.mcp -t datosvivos-mcp:dev .
docker run --rm -p 3000:3000 -e MCP_TRANSPORT=sse datosvivos-mcp:dev
```

## Lo que NO funciona aún

- `docker compose up` — los servicios `api`, `streamlit`, `nginx` son placeholders hasta Sprint 4
- `scripts/build_index.py` — stub vacío, se implementa en Sprint 2
- Integración con Ollama, vector index, Streamlit — pendientes según cronograma

## Licencia

MIT — ver [LICENSE](LICENSE).
