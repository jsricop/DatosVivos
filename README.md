# DatosVivos

Agente de IA con modelo local que permite a cualquier ciudadano hacer preguntas en lenguaje natural sobre los datos públicos de Colombia, ejecutando consultas reales sobre [datos.gov.co](https://www.datos.gov.co), cruzando datasets de múltiples entidades y entregando análisis verificables con visualizaciones.

Incluye un **modo de accesibilidad** para personas con discapacidad visual: entrada por voz y respuestas narradas.

> **Concurso "Datos al Ecosistema 2026: IA para Colombia"** — Reto #07 (Innovación y Tecnología). Equipo: Oficina de Tecnología de la **ANI** (Agencia Nacional de Infraestructura).

## Arquitectura

Tres capas:

1. **MCP Server** — expone 4 tools (`search_datasets`, `get_metadata`, `query_data`, `cross_datasets`) sobre las APIs de Socrata de datos.gov.co
2. **Motor de IA** — clasificador de intención (embeddings) + índice vectorial de metadatos + generador local (Ollama / Qwen 2.5 7B)
3. **Interfaces** — Streamlit para ciudadanos (chat + Plotly + Folium + voz), Power BI para analítica de uso

## Stack

Python 3.11+ · FastAPI · MCP SDK · Ollama (Qwen 2.5 Coder 7B) · sentence-transformers · ChromaDB · PostgreSQL 16 · Streamlit · Plotly · Folium · Docker Compose · Nginx

## Estructura

```
mcp_server/   Capa 1 — MCP Server + clientes Socrata
ai_engine/    Capa 2 — Clasificador, índice vectorial, LLM backend
app/          Capa 3 — Interfaz Streamlit + accesibilidad
api/          FastAPI backend (endpoints internos)
db/           Schema PostgreSQL + migraciones
scripts/      Indexación, mantenimiento
docs/         Documentación CRISP-ML(Q)
tests/        Pruebas pytest
```

## Setup

Requiere VM con Docker, Docker Compose y Ollama. Ver `docs/06_deployment.md` para el detalle.

```bash
cp .env.example .env
# editar .env
docker compose up -d
docker compose exec api python scripts/build_index.py
```

## Licencia

MIT — ver [LICENSE](LICENSE).
