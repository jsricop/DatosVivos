# DatosVivos

Agente de IA con modelo local que permite a cualquier ciudadano hacer preguntas en lenguaje natural sobre los datos públicos de Colombia, ejecutando consultas reales sobre [datos.gov.co](https://www.datos.gov.co), cruzando datasets de múltiples entidades y entregando análisis verificables con visualizaciones.

Incluye un **modo de accesibilidad** para personas con discapacidad visual: entrada por voz y respuestas narradas.

> **Concurso "Datos al Ecosistema 2026: IA para Colombia"** — Reto #07 (Innovación y Tecnología). Equipo: Oficina de Tecnología de la **ANI** (Agencia Nacional de Infraestructura).

## Arquitectura

Tres capas:

1. **MCP Server** — expone 4 tools sobre las APIs de Socrata de datos.gov.co (`search_datasets`, `get_metadata`, `query_data`, `cross_datasets`).
2. **Motor de IA** — clasificador de intención (embeddings `multilingual-e5-large`) + índice vectorial de metadatos (ChromaDB, 8 389 datasets) + generador local (Ollama / Qwen 2.5 Coder 3B default, 7B opcional). Búsqueda 3-tier (acrónimos + topic keywords + reformulación LLM), GeoResolver con DIVIPOLA, plantillas SoQL deterministas para comparativas, validador whitelist anti-alucinación de cifras. **Sprints 2-3 + Sprint 6 endurecimiento Beta-1.**
3. **Interfaz** — Streamlit para ciudadanos (chat + Plotly + Folium + Web Speech API + enlaces verificables a cada dataset citado + telemetría CSV). **Sprint 4 + Sprint 6.** (Power BI / logging persistente quedan como integraciones externas opcionales, fuera del entregable.)

## Stack

Python 3.11+ · MCP SDK · Ollama (Qwen 2.5 Coder 3B default · 7B opcional) · sentence-transformers `multilingual-e5-large` · ChromaDB · pandas 3.0 (auto-cast + estadísticas deterministas) · Streamlit · Plotly · Folium · `streamlit-folium` · Web Speech API · Docker Compose · Nginx (producción)

## Estado actual (2026-05-19)

| Capa | Sprint | Estado |
|---|---|---|
| MCP Server (4 tools sobre datos.gov.co) | 1 + 3 | ✅ Funcional, tests verdes |
| Motor de IA (índice vectorial + clasificador) | 2 | ✅ Funcional |
| `cross_datasets` (1-5 datasets) + Ollama + analyzer end-to-end | 3 + ext | ✅ Funcional |
| Acrónimos + topic keywords (3-tier search) | ext | ✅ Funcional |
| Streamlit + accesibilidad (sin Power BI) | 4 | ✅ Funcional, 16 tests verdes |
| Docs CRISP-ML(Q) + capítulo MCP + checklist MinTIC | 5 | ✅ Redactados |
| **Cifras pandas + whitelist anti-alucinación** | **6** | **✅ 55 tests verdes; 30/30 sin alucinaciones en journey** |
| **GeoResolver DIVIPOLA + comparativa multi-target** | **6** | **✅ plantillas SoQL deterministas; tests congelados** |
| **Telemetría CSV + disclaimer beta + enlaces verificables** | **6** | **✅ activa por defecto** |

## Garantías para el ciudadano (Beta-1)

- **Cero cifras inventadas**: toda cuantificación que aparece en una respuesta se calcula con pandas sobre los rows reales devueltos por Socrata. Si el LLM intenta colar un número fuera de la lista blanca, esa oración se censura antes de mostrarse.
- **Trazabilidad por enlace**: cada respuesta incluye los IDs de los datasets consultados + un link clicable a `https://www.datos.gov.co/d/{id}` (página humana) y al endpoint JSON SODA (para reusar los datos).
- **Honestidad sobre límites**: si no encontramos datasets relevantes, lo decimos con un mensaje fijo. No inventamos datasets ficticios ni datos de otros países.
- **Geolocalización estricta**: cuando preguntás sobre un departamento o municipio, usamos códigos DIVIPOLA oficiales y plantillas SoQL deterministas (no le pedimos al LLM que "adivine" el filtro).

## Estructura

```
mcp_server/   Capa 1 — MCP Server + clientes Socrata    (Sprint 1: ✅)
ai_engine/    Capa 2 — Clasificador, vector index, LLM   (Sprints 2-3: ✅)
app/          Capa 3 — Streamlit + accesibilidad         (Sprint 4: ✅)
db/           Schema PostgreSQL (referencia)             (sprint posterior)
scripts/      Indexación, mantenimiento                  (Sprint 2)
tests/        Pruebas pytest                             (continuo)
```

## Lo que funciona hoy

```bash
# 1. Clonar y preparar entorno
git clone https://github.com/jsricop/DatosVivos.git
cd DatosVivos
python3.11 -m venv .venv && source .venv/bin/activate

# Para el MCP Server (Sprint 1)
pip install -r requirements.mcp.txt -r requirements-dev.txt

# Adicionalmente, para el motor de IA (Sprint 2: índice vectorial + clasificador, Sprint 3: orquestación)
pip install -r requirements.ai.txt

# Sprint 3 requiere Ollama corriendo local para tests con LLM real:
#   brew install ollama && ollama serve &
#   ollama pull qwen2.5-coder:3b
# (Sin Ollama, los tests dependientes se saltan con skipif. Suite no-LLM corre normal.)

# 2. Configurar entorno (opcional para el MCP Server — funciona con defaults)
cp .env.example .env
# editar .env si necesitas un SOCRATA_APP_TOKEN para mayor rate limit

# 3. Correr los tests
pytest                              # toda la suite
pytest tests/test_mcp_tools.py      # solo Sprint 1
pytest tests/test_sprint2_acceptance.py  # solo Sprint 2 (requiere índice)

# 4. Levantar el MCP Server (elige un transporte)
MCP_TRANSPORT=stdio python -m mcp_server.server     # para hosts MCP locales
MCP_TRANSPORT=sse   python -m mcp_server.server     # HTTP/SSE en :3000

# 5. Build y run del MCP Server vía Docker
docker build -f Dockerfile.mcp -t datosvivos-mcp:dev .
docker run --rm -p 3000:3000 -e MCP_TRANSPORT=sse datosvivos-mcp:dev

# 6. Construir el índice vectorial del catálogo (Sprint 2, ~10 min para ~8k datasets)
python -m scripts.build_index                       # build completo
python -m scripts.build_index --limit 500           # build parcial (dev/test)
python -m scripts.build_index --output ./custom     # output custom
```

## Pendientes / fuera de scope

- **Demo público con TLS** — la VM corre tras VPN; falta dominio público con Nginx + Let's Encrypt antes de sustentación.
- **Publicación en `datos.gov.co` y `herramientas.datos.gov.co/usos`** — coordinación con MinTIC, FASE 8 del Sprint 5.
- **PostgreSQL logging persistente** — schema definido en `db/init.sql` como referencia, no activado.
- **Power BI / dashboards analíticos** — fuera del entregable, integraciones externas opcionales.

## Convenciones de desarrollo

Si vas a contribuir código, dos disciplinas obligatorias:

### Test-first para features de sprint
Los tests con criterios de aceptación se escriben **antes** del código de producción. Cada sprint con criterios medibles (accuracy, latencia, cobertura) tiene un archivo `tests/test_sprintN_acceptance.py` con todos los tests `@pytest.mark.skip`. Se va quitando el `@skip` a medida que cada feature se implementa. **Los tests no se modifican** durante el sprint; si fallan, se corrige el código. Ejemplo activo: [`tests/test_sprint2_acceptance.py`](tests/test_sprint2_acceptance.py).

### Doc-first para cambios visibles
Toda PR que afecte interfaz pública (comandos, contratos de tools, arquitectura, dependencias) debe actualizar la documentación en el mismo PR. Sin docs, no se mergea. Para el checklist específico por tipo de cambio, pregúntale a un maintainer.

### Convención de commits
Formato: `tipo(scope): descripción`. Tipos: `feat`, `fix`, `test`, `docs`, `chore`, `refactor`. Cada commit debe cerrar con `Co-Authored-By: ANI Team & Claude <noreply@anthropic.com>`. Ver historial reciente para ejemplos.

## Seguridad y privacidad

- DatosVivos opera **exclusivamente** sobre datos públicos de [datos.gov.co](https://www.datos.gov.co)
- No accede, procesa ni expone información interna de la ANI ni de ninguna entidad del Estado
- El modelo LLM corre **localmente** (Ollama) — ni consultas ciudadanas ni datos analizados salen del servidor
- La VM productiva está detrás de VPN (FortiClient SSL) — no expuesta a internet público
- Las credenciales viven en `.env` (`.gitignore`d) — nunca en código
- El repositorio público en GitHub solo contiene código, no datos ni credenciales

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
