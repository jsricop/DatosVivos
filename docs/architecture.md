# Arquitectura — DatosVivos

Documento de diseño técnico del sistema. Describe las **tres capas** y sus interacciones.

## Visión general — tres capas

```
┌─────────────────────────────────────────────────────┐
│           CAPA 3: INTERFACES DE USUARIO             │
│                                                     │
│  ┌─────────────────┐    ┌────────────────────────┐  │
│  │   Streamlit      │    │   Power BI             │  │
│  │   (ciudadano)    │    │   (analítica de uso)   │  │
│  │   - Chat NL      │    │   - KPIs               │  │
│  │   - Plotly/Folium│    │   - Tendencias         │  │
│  │   - Exportación  │    │   - Mapa departamental │  │
│  │   - ♿ Modo a11y  │    │                        │  │
│  └────────┬─────────┘    └───────────┬────────────┘  │
│           │                          │               │
│           ▼                          ▼               │
├─────────────────────────────────────────────────────┤
│              CAPA 2: MOTOR DE IA                    │
│                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐  │
│  │ Clasificador │ │   Índice     │ │  Generador  │  │
│  │ de Intención │ │  Vectorial   │ │  (Ollama)   │  │
│  │ (embeddings) │ │ (ChromaDB/   │ │  Qwen 2.5 7B│  │
│  │              │ │  FAISS)      │ │  Llama 3 8B │  │
│  └──────┬───────┘ └──────┬───────┘ └──────┬──────┘  │
│         │                │                │          │
│         ▼                ▼                ▼          │
├─────────────────────────────────────────────────────┤
│           CAPA 1: MCP SERVER                        │
│                                                     │
│  Tools expuestos vía protocolo MCP:                 │
│  - search_datasets    (Discovery API)               │
│  - get_metadata       (Metadata API)                │
│  - query_data         (SODA API / SoQL)             │
│  - cross_datasets     (cruce por DIVIPOLA/DANE)     │
│                                                     │
│  Fuente: datos.gov.co (Socrata)                     │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │    PostgreSQL 16    │
              │  - Logs consultas   │
              │  - Métricas de uso  │
              │  - Caché resultados │
              │  - Feed Power BI    │
              └─────────────────────┘
```

## Capa 1 — MCP Server

Expone **tools MCP** (Model Context Protocol) sobre las APIs públicas de Socrata de datos.gov.co. Cualquier cliente MCP (Ollama wrapper, Claude Desktop, etc.) puede conectarse y consumir los datos.

Ver [glosario](./glossary.md) para qué es MCP.

### Tools expuestas

| Tool | Input | Output | Fuente |
|---|---|---|---|
| `search_datasets` | `query: str, limit: int` | lista de datasets con id, name, entity, etc. | Discovery API |
| `get_metadata` | `dataset_id: str` | esquema (columnas, tipos, descripción) | Metadata API |
| `query_data` | `dataset_id, soql_query?, limit, offset` | filas como dicts | SODA API |
| `cross_datasets` | `dataset_ids: list[str], join_keys: str \| list[str], select_columns?, per_dataset_limit?` | filas merged | Descarga 1-5 datasets, encadena pandas merges |

### `cross_datasets` — el diferenciador

Cruza de **1 a 5 datasets** de entidades distintas por claves territoriales comunes (DIVIPOLA, código DANE, NIT, departamento, municipio).

**Cardinalidades:**
- `N=1` → devuelve filas del dataset sin merge.
- `N=2` → comportamiento pairwise canónico.
- `N=3..5` → cadena de merges, cada uno verificado.
- `N=0` o `N>5` → `ToolError` con mensaje explícito.

**Variantes de `join_keys`:**
- **String único:** la misma columna existe en todos los datasets (caso común con DIVIPOLA).
- **Lista de N-1 strings:** una key por cada paso de merge (cuando las columnas se llaman distinto entre datasets).
- **`None`:** solo válido si N=1. Para N≥2 es error explícito — NO auto-detectamos columnas comunes (causa típica de falsos positivos).

**Garantías anti-falsos-positivos:**
- Verificación previa: si la `join_key` falta en algún dataset, se aborta con error que identifica cuál.
- Short-circuit: si un merge intermedio queda vacío, no se descargan los datasets siguientes (ahorra red y memoria).
- Cap por dataset (5.000) + cap intermedio (5.000) + cap final (5.000) — defensa en profundidad contra joins runaway.
- NO se infiere "columna común" por nombre coincidente — el caller debe declarar explícitamente.

### Transportes soportados

- **SSE** (HTTP) — para clientes remotos. Default puerto 3000.
- **stdio** — para hosts MCP locales que lanzan el server como proceso hijo.

Variable `MCP_TRANSPORT=sse|stdio` controla el modo.

## Capa 2 — Motor de IA

Tres subcapas que convierten lenguaje natural en llamadas a las tools de la Capa 1.

### 2.1 Clasificador de Intención

- **Input:** pregunta del usuario en lenguaje natural
- **Output:** uno de `search`, `descriptive`, `comparative`, `temporal`, `cross_source`
- **Técnica:** embeddings (sentence-transformers `multilingual-e5-base`) + similitud coseno contra intenciones prototipo
- **No requiere LLM** — es inferencia de embeddings pura, latencia <100ms

### 2.2 Índice Vectorial de Metadatos

- **Contenido:** embeddings de `name + description + tags` de los ~8.000 datasets de datos.gov.co
- **Store:** ChromaDB (persistido en disco) o FAISS — ver ADR-005
- **Actualización:** cron semanal que re-indexa el catálogo via Discovery API
- **Propósito:** matching semántico entre la pregunta del usuario y los datasets relevantes (RAG sobre metadatos)

### 2.3 Generador / Analizador

- **Modelo primario:** Qwen 2.5 Coder 7B (Q4_K_M) servido por Ollama
- **Fallback:** Llama 3 8B (Q4_K_M)
- **Tareas:** generar queries SoQL, decidir qué datasets cruzar, producir narrativa en español, interpretar resultados
- **Backend intercambiable:** variable `LLM_BACKEND=ollama|openai|anthropic` para cambiar sin modificar código (ver ADR-001)

## Capa 3 — Interfaces

### 3.1 Streamlit (ciudadanos)

- Chat en lenguaje natural
- Visualizaciones: Plotly (gráficos), Folium (mapas georreferenciados de Colombia)
- Modo accesibilidad: ver [accessibility.md](./accessibility.md)
- Exportación de resultados

### 3.2 Power BI (analítica interna)

- Dashboard de métricas de uso del agente
- Conectado a las tablas de PostgreSQL (`queries`, `dataset_usage`, `cross_operations`)
- No es interfaz ciudadana — es para monitoreo del equipo

## Base de Datos (PostgreSQL 16)

Schema en [`db/init.sql`](../db/init.sql). Tres tablas principales:

- `queries` — logs de cada consulta ciudadana (intent_type, datasets_used, response_text, execution_ms)
- `dataset_usage` — qué datasets se usan cuánto, por entidad publicadora
- `cross_operations` — operaciones de cruce ejecutadas (join_key, rows_result)

Power BI consume estas tablas vía conector nativo de PostgreSQL.

## APIs externas consumidas

### datos.gov.co (Socrata)

| API | Base URL | Propósito | Auth |
|-----|----------|-----------|------|
| SODA | `https://www.datos.gov.co/resource/{dataset_id}.json` | Consultar datos (SoQL) | Pública |
| Discovery | `https://api.us.socrata.com/api/catalog/v1?domains=datos.gov.co` | Buscar datasets | Pública |
| Metadata | `https://www.datos.gov.co/api/views/{dataset_id}.json` | Esquema de un dataset | Pública |

Sin API key requerida. App Token opcional para mayor rate limit (registro en datos.gov.co).

### Ollama (local)

| Endpoint | URL | Propósito |
|----------|-----|-----------|
| Generate | `http://localhost:11434/api/generate` | Inferencia del modelo |
| Chat | `http://localhost:11434/api/chat` | Conversación multi-turno |
| Embeddings | `http://localhost:11434/api/embeddings` | Alternativa a sentence-transformers |

## Infraestructura objetivo

- 6 servicios Docker Compose (ollama, mcp-server, api, streamlit, postgres, nginx)
- VM Ubuntu 22.04/24.04 con 8 vCPU / 16 GB RAM
- VPN FortiClient SSL para acceso administrativo (no expone a internet)
- Nginx como reverse proxy HTTPS

Detalle de despliegue: [`06_deployment.md`](./06_deployment.md).
