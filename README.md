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

## Convenciones de desarrollo

Si vas a contribuir código, dos disciplinas obligatorias:

### Test-first para features de sprint
Los tests con criterios de aceptación se escriben **antes** del código de producción. Cada sprint con criterios medibles (accuracy, latencia, cobertura) tiene un archivo `tests/test_sprintN_acceptance.py` con todos los tests `@pytest.mark.skip`. Se va quitando el `@skip` a medida que cada feature se implementa. **Los tests no se modifican** durante el sprint; si fallan, se corrige el código. Ejemplo activo: [`tests/test_sprint2_acceptance.py`](tests/test_sprint2_acceptance.py).

### Doc-first para cambios visibles
Toda PR que afecte interfaz pública (comandos, contratos de tools, arquitectura, dependencias) debe actualizar la documentación en el mismo PR. Sin docs, no se mergea. Checklist específico por tipo de cambio: ver MAIN.md §6.5 (interno) o pregúntale a un maintainer.

### Convención de commits
Formato: `tipo(scope): descripción`. Tipos: `feat`, `fix`, `test`, `docs`, `chore`, `refactor`. Cada commit debe cerrar con `Co-Authored-By: ANI Team & Claude <noreply@anthropic.com>`. Ver historial reciente para ejemplos.

## Seguridad y privacidad

- DatosVivos opera **exclusivamente** sobre datos públicos de [datos.gov.co](https://www.datos.gov.co)
- No accede, procesa ni expone información interna de la ANI ni de ninguna entidad del Estado
- El modelo LLM corre **localmente** (Ollama) — ni consultas ciudadanas ni datos analizados salen del servidor
- La VM productiva está detrás de VPN (FortiClient SSL) — no expuesta a internet público
- Las credenciales viven en `.env` (`.gitignore`d) — nunca en código
- El repositorio público en GitHub solo contiene código, no datos ni credenciales

## Documentación

- [`docs/architecture.md`](docs/architecture.md) — arquitectura de tres capas, APIs externas, infraestructura objetivo
- [`docs/accessibility.md`](docs/accessibility.md) — modo accesible (voz in/out, WCAG 2.1, Ley 1618)
- [`docs/glossary.md`](docs/glossary.md) — términos del dominio (DIVIPOLA, SoQL, MCP, etc.)
- [`docs/lessons_learned.md`](docs/lessons_learned.md) — bugs no obvios y gotchas capturados durante desarrollo
- [`docs/01..06_*.md`](docs/) — fases CRISP-ML(Q) (Sprint 5)

## Referencias

- [datos.gov.co](https://www.datos.gov.co) — Portal de datos abiertos de Colombia
- [SODA API](https://dev.socrata.com/consumers/getting-started.html) — Documentación de la API de consulta
- [Discovery API](https://socratadiscovery.docs.apiary.io/) — Documentación de búsqueda de datasets
- [MCP Protocol](https://modelcontextprotocol.io/) — Especificación del Model Context Protocol
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) — SDK oficial
- [Ollama](https://ollama.ai) — Servidor de modelos LLM locales
- [CRISP-ML(Q)](https://arxiv.org/abs/2003.05155) — Paper del marco metodológico
- [Web Speech API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API) — STT/TTS del navegador
- [WCAG 2.1](https://www.w3.org/TR/WCAG21/) — Estándar de accesibilidad web
- [Ley 1618 de 2013](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=52081) — Accesibilidad TIC en Colombia

## Licencia

MIT — ver [LICENSE](LICENSE).
