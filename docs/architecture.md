# Arquitectura — DatosVivos

Documento de diseño técnico del sistema. Describe las **tres capas** y sus interacciones.

## Visión general — tres capas

```
┌─────────────────────────────────────────────────────┐
│           CAPA 3: INTERFAZ DE USUARIO               │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │   Streamlit (ciudadano)                      │   │
│  │   - Chat NL (st.chat_message/st.chat_input)  │   │
│  │   - Páginas: chat · explorer · about         │   │
│  │   - Plotly / Folium / st.dataframe           │   │
│  │   - Exportación CSV                          │   │
│  │   - ♿ Modo accesible (Web Speech API)       │   │
│  └────────────────────────┬─────────────────────┘   │
│                           │                          │
│                           ▼                          │
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
              │  (Sprint posterior) │
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

### Búsqueda con fallback en 3 tiers (`search_datasets`)

La búsqueda contra `datos.gov.co` enfrenta un problema real: los ciudadanos NO suelen mencionar entidades por nombre. Dicen *"datos sobre tierras"*, no *"datos de la ANT"*. Para mitigar esto, `DiscoveryClient.search()` aplica tres niveles de expansión en cascada:

```
Tier 1 — Acrónimos (precisión alta)
    Si la query menciona una entidad por sigla/nombre/alias conocido
    (MinTIC, MEN, ICBF, "Ministerio de las TIC", "Cancillería"…), expande
    al nombre canónico (`mcp_server/socrata/acronyms.py`).
    → Siempre rápido. Cero LLM. Cero latencia agregada.
                    │
                    ▼ si Socrata devuelve resultados, retornar
                    │
                    ▼ si vacío:

Tier 2 — Topic keywords iterativo (recuperación amplia)
    Cuando la query NO menciona entidad por nombre, intentamos detectar
    el tema. Cada entidad tiene 3-6 `keywords` temáticos extraídos del
    contenido real de sus datasets en datos.gov.co.

    Estrategia iterativa para evitar inundar la query:
        a. Calcular ranking de entidades por overlap query↔keywords.
        b. Agrupar de a 2 entidades por rank.
        c. Buscar con top-2 expandido → si hay resultados, retornar.
        d. Si vacío, buscar con next-2 (rank 3-4) → si hay, retornar.
        e. Continuar hasta agotar grupos o encontrar resultados.

    → Latencia: hasta N llamadas HTTP secuenciales (típico 1-3).
    → Cero LLM. Mantiene determinismo.
                    │
                    ▼ si todos los grupos exhaustos sin resultados:

Tier 3 — LLM reformulación (último recurso)
    El `Analyzer` invoca el LLM con un prompt que le pide reformular la
    pregunta usando keywords alternativos. Se reintenta la búsqueda con
    el query reformulado. Marca en `AnalysisResult` que se reformuló
    (transparencia al usuario).

    → Latencia agregada: +1-2 s.
    → Solo se ejecuta cuando ambos tiers anteriores fallan.
```

**Por qué cap de 2 entidades por grupo:** evitar inundar Socrata con ~5 nombres canónicos completos en una sola query (cada uno tiene 6-8 palabras). Eso genera mucho ruido en el matching. Iterar grupos de 2 mantiene calidad por intento, a costa de hasta N llamadas HTTP secuenciales en el peor caso.

**Trade-off documentado:** la latencia del Tier 2 crece linealmente con el número de grupos intentados. En la práctica, las queries con tema claro encuentran resultados en 1-2 iteraciones. Queries muy vagas pueden hacer 5+ intentos antes de caer al LLM (Tier 3).

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

## Capa 3 — Interfaz Streamlit

La interfaz ciudadana es una app **Streamlit** multipágina. Power BI **no** forma parte del entregable: queda como integración opcional que un usuario externo podría conectar a su propia base si decide montar logging persistente.

### 3.1 Estructura de la app

```
app/
├── main.py                            # entrypoint, st.navigation multipage
├── agent_client.py                    # wrapper de ai_engine.Analyzer
├── components/
│   ├── chart_renderer.py              # auto-detección Plotly (línea/barra/scatter)
│   ├── map_renderer.py                # Folium + join con dataset DIVIPOLA
│   └── accessibility/
│       ├── speech_input.py            # Web Speech API STT (entrada por voz)
│       ├── speech_output.py           # Web Speech API TTS (respuesta hablada)
│       ├── chart_narrator.py          # alt-text auto-generado por gráfico
│       └── a11y_toggle.py             # toggle global accesibilidad en sidebar
└── pages/
    ├── chat.py                        # chat conversacional
    ├── explorer.py                    # buscador de datasets + ficha + preview
    └── about.py                       # qué es y cómo funciona
```

### 3.2 Páginas

| Página | Propósito | Tools MCP usadas |
|---|---|---|
| **Chat** | Pregunta libre en NL → respuesta narrada + visualización inline. Historial en `st.session_state`. | Todas vía `Analyzer` |
| **Explorer** | Buscar datasets por keyword, ver metadata, preview de filas. | `search_datasets`, `get_metadata`, `query_data` |
| **About** | Descripción del proyecto, cómo funciona, créditos. | — |

### 3.3 Componentes

- **Plotly** (`chart_renderer.py`) — clasifica columnas por tipo (datetime/numérica/categórica) y elige automáticamente serie temporal, barra agrupada o scatter. El alt-text descriptivo lo aporta `accessibility/chart_narrator.py`.
- **Folium** (`map_renderer.py`) — cuando hay `lat/lon` o `cod_dpto/cod_mpio`, hace join con `gdxc-w37w` y dibuja capa coroplética.
- **`st.dataframe`** — tabla filtrable + botón descarga CSV.

### 3.4 Accesibilidad

Ver [accessibility.md](./accessibility.md). Implementación en `app/components/accessibility/`:

- `speech_input.py` — STT vía Web Speech API embebida con `streamlit.components.v1.html`. Fallback a `st.chat_input` cuando el navegador no soporta `SpeechRecognition`.
- `speech_output.py` — TTS opcional: lee la respuesta del agente en voz alta. Se activa con el toggle del sidebar.
- `chart_narrator.py` — alt-text auto-generado por gráfico (resumen estadístico narrado en español).
- `a11y_toggle.py` — toggle global del sidebar que habilita STT/TTS por sesión.
- WCAG 2.1 AA: contraste tema dark, navegación por teclado, foco visible.

### 3.5 Backend del agente

`app/agent_client.py` instancia un `ai_engine.Analyzer` único por sesión, parametrizado por `.env`:

- `LLM_BACKEND=ollama` (default local) o `anthropic` (cloud).
- Cliente MCP apunta a `http://mcp-server:8000/sse` (Docker Compose) o `http://localhost:8000/sse` (dev local).

### 3.6 Fuera de scope del Sprint 4

- PostgreSQL logging de consultas
- Power BI / cualquier dashboard analítico
- Autenticación de usuarios

## Base de Datos (PostgreSQL 16)

Schema en [`db/init.sql`](../db/init.sql). Tres tablas principales:

- `queries` — logs de cada consulta ciudadana (intent_type, datasets_used, response_text, execution_ms)
- `dataset_usage` — qué datasets se usan cuánto, por entidad publicadora
- `cross_operations` — operaciones de cruce ejecutadas (join_key, rows_result)

> **Nota Sprint 4:** la activación de logging en PostgreSQL queda fuera del scope del Sprint 4. El schema existe como referencia para un sprint posterior si se decide instrumentar el agente. Cualquier integración externa (Power BI, Metabase, Superset) puede conectarse a estas tablas vía conector nativo de PostgreSQL.

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

- Servicios Docker Compose objetivo: `ollama`, `mcp-server`, `streamlit` (Sprint 4), `postgres` (referencia, sin activar aún), `nginx` (reverse proxy HTTPS)
- VM Ubuntu 22.04/24.04 con 8 vCPU / 16 GB RAM
- VPN FortiClient SSL para acceso administrativo (no expone a internet)
- Nginx como reverse proxy HTTPS

Detalle de despliegue: [`06_deployment.md`](./06_deployment.md).
