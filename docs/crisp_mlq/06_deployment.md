# 06 — Deployment

> CRISP-ML(Q) — Fase 6. Cómo se despliega el agente en producción, qué runbook tiene el operador y qué consideraciones de monitoreo proponemos.

## Resumen

DatosVivos se despliega como **3 servicios Docker** orquestados con `docker-compose.yml`: un servidor MCP, una app Streamlit, y opcionalmente Ollama (recomendado en el host para no duplicar RAM). El índice vectorial se monta como volumen. Una VPN FortiClient SSL protege el acceso administrativo. Logging persistente en PostgreSQL queda como hook para un sprint posterior.

---

## 🏛️ Para el jurado MinTIC

### Qué demuestra esta fase

- **Despliegue real, no demo:** la app corre en una VM Ubuntu del Estado, accesible vía VPN. No es un mockup de jurado.
- **Reproducible end-to-end:** `docker compose up` levanta el stack en cualquier máquina con Docker.
- **Soberanía operativa:** sin dependencias cloud obligatorias; opera 100% en infraestructura del estado si así se decide.
- **Runbook operativo claro:** el operador sabe qué pasa, cómo reindexar, cómo rotar modelos.

### Topología desplegada

```
┌────────────────────────────────────────────────────┐
│            Operador / Auditor                      │
│                    │                               │
│            ▼ (VPN FortiClient SSL)                 │
│      ┌──────────────────────┐                      │
│      │  VM Ubuntu 22.04/24  │  8 vCPU / 16 GB RAM  │
│      │                      │                      │
│      │  ┌────────────────┐  │                      │
│      │  │ docker compose │  │                      │
│      │  ├────────────────┤  │                      │
│      │  │ mcp-server :3K │  │ ← APIs Socrata       │
│      │  │ streamlit :8501│  │                      │
│      │  │ (Nginx 80/443) │  │ ← reverse proxy      │
│      │  └────────────────┘  │                      │
│      │  ┌────────────────┐  │                      │
│      │  │ Ollama :11434  │  │ ← host-level         │
│      │  │ Qwen 2.5 Coder │  │   (no duplica RAM)   │
│      │  └────────────────┘  │                      │
│      │  data/vector_index/  │ ← persistente        │
│      └──────────────────────┘                      │
└────────────────────────────────────────────────────┘
```

### Recursos mínimos verificados

- **Hardware:** 8 vCPU, 16 GB RAM. Qwen 3B usa ~2 GB; embeddings model ~2 GB; resto para el resto.
- **Almacenamiento:** ~30 GB (índice + modelos + sistema).
- **Red:** salida a internet para consumir `datos.gov.co`. Sin entradas públicas excepto vía Nginx 443.

---

## 🛠️ Para ciudadanos técnicos

### docker-compose.yml — estado al cierre del Sprint 4

```yaml
services:
  mcp-server:
    build: { context: ., dockerfile: Dockerfile.mcp }
    env_file: .env
    environment: { MCP_TRANSPORT: sse, MCP_PORT: 3000, MCP_HOST: 0.0.0.0 }
    ports: ["3000:3000"]

  streamlit:
    build: { context: ., dockerfile: Dockerfile.streamlit }
    env_file: .env
    environment:
      MCP_SERVER_URL: http://mcp-server:3000/sse
      LLM_BACKEND: ${LLM_BACKEND:-ollama}
      OLLAMA_BASE_URL: ${OLLAMA_BASE_URL:-http://host.docker.internal:11434}
    ports: ["8501:8501"]
    volumes: ["./data/vector_index:/app/data/vector_index:ro"]
    depends_on: [mcp-server]

  # ollama, postgres, nginx → contenedores opcionales
```

### Decisiones operativas

| Decisión | Justificación |
|---|---|
| **Ollama corre en el host, no en contenedor** | Evitar duplicar 2-4 GB de RAM por GPU/CPU offload. El contenedor `streamlit` apunta a `host.docker.internal:11434`. |
| **Índice vectorial como volumen `ro`** | Lectura-solo dentro del contenedor → la app no puede corromperlo. Se reconstruye fuera del contenedor con `scripts/build_index.py`. |
| **MCP server en su propio contenedor** | Permite que otros clientes MCP (Claude Desktop, Gemini, etc.) lo consuman aunque la UI Streamlit esté abajo. |
| **`.env` no se commitea** | Secretos (`SOCRATA_APP_TOKEN`, credenciales) viven en `.env` local. `.env.example` versionado. |
| **Nginx opcional** | En desarrollo / DEMO, exponer `:8501` directo. En producción real, Nginx con HTTPS + rate limit. |

### Runbook operativo

#### 1. Despliegue inicial

```bash
# En la VM
git clone https://github.com/jsricop/DatosVivos
cd DatosVivos
cp .env.example .env
# editar .env: SOCRATA_APP_TOKEN, OLLAMA_BASE_URL si custom

# Levantar Ollama en host (no en contenedor)
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull qwen2.5-coder:3b

# Construir índice (primera vez, ~10 min)
python -m scripts.build_index

# Levantar servicios
docker compose up -d mcp-server streamlit

# Verificar
curl http://localhost:3000/sse              # MCP server alive
curl http://localhost:8501/                 # Streamlit alive
```

#### 2. Reindexación del catálogo

Recomendado cada 1-2 semanas, o cuando datos.gov.co publique entidades nuevas significativas.

```bash
# El índice es reconstruido fuera del contenedor
python -m scripts.build_index
# La app Streamlit no necesita restart: el volumen montado se actualiza atómicamente.
# Sin embargo, ChromaDB en caché de la app puede necesitar reload — restart del contenedor:
docker compose restart streamlit
```

#### 3. Rotación de modelo LLM

Si el hardware lo permite, upgrade a Qwen 7B:

```bash
ollama pull qwen2.5-coder:7b
# Editar .env:
echo "OLLAMA_MODEL=qwen2.5-coder:7b" >> .env
docker compose restart streamlit
```

#### 4. Switch a backend cloud (Claude / Gemini)

```bash
# En .env:
LLM_BACKEND=anthropic
ANTHROPIC_API_KEY=sk-...
docker compose restart streamlit
```

(Requiere completar `AnthropicBackend` actual que es stub.)

#### 5. Verificación de salud

```bash
# Suite de tests
pytest -m "not integration" -q          # ~30 segundos
pytest tests/test_sprint4_acceptance.py -q   # solo UI

# Logs
docker compose logs -f streamlit
docker compose logs -f mcp-server
```

### Monitoreo propuesto (fuera de scope MVP)

Para un sprint posterior, sugerencias concretas:

| Métrica | Por qué | Implementación sugerida |
|---|---|---|
| Latencia `Analyzer.analyze()` p50/p95 | Detectar degradación de Ollama | Middleware en `agent_client.py` que logguee a stdout o PostgreSQL |
| Tasa de queries con `datasets_used=[]` | Visibilizar fallos de retrieval | Misma instrumentación |
| Tasa de queries que activan Tier 3 (LLM reformulación) | Si sube, el catálogo cambió o el clasificador necesita re-tuning | Flag en `AnalysisResult` |
| Uso de cada tool MCP | Saber si `cross_datasets` se usa o si es overkill | Log por tool en `mcp_server/tools/_errors.py` |
| Errores 5xx de Socrata | El portal se cae a veces | Reintentos exponenciales + alarmaje |

Stack sugerido: PostgreSQL (schema ya definido en `db/init.sql`) + Grafana o Metabase. No incluido en el entregable del Sprint 4 por scope.

### Seguridad operativa

- **Sin secretos en el repo:** todo via `.env`. `.gitignore` lo cubre.
- **Acceso administrativo solo por VPN.** El portal público (cuando se publique) puede ir sin VPN, pero la administración sí.
- **Sin datos personales del usuario:** la app no requiere login (al menos en MVP); no recolecta PII. Si en el futuro se loguean queries, requerirá consentimiento explícito.
- **Rate limit en Nginx** (cuando se active): proteger Socrata de abuso desde nuestro lado.

---

## 👥 Para ciudadanía general

### ¿Dónde corre el agente?

En una computadora del Estado, no en una "nube" privada extranjera. Esto significa:

- Tus preguntas nunca salen a servidores fuera del país (por defecto).
- Si la institución que opera DatosVivos quiere migrar a otro proveedor, lo puede hacer sin perder los datos ni el código.

### ¿Y si el agente está caído?

Como con cualquier servicio web, puede haber momentos de mantenimiento. El operador tiene un *runbook* (manual de operación) con los comandos exactos para:

- Reiniciar el servicio.
- Reconstruir el catálogo si se agregan datasets nuevos importantes.
- Cambiar el "cerebro" de IA si quiere uno más potente.

### ¿Cómo se actualiza?

El proyecto es open source. Mejoras se publican en el repositorio público de GitHub. Cuando una nueva versión está lista, el operador hace `git pull` y un comando para reconstruir los contenedores. Sin tiempo de caída largo.

### ¿Tiene un costo para la ciudadanía?

**Cero** desde el lado de la persona que lo usa. Para la entidad que lo aloja, el costo es:

- Una VM modesta (8 vCPU, 16 GB RAM) o equivalente.
- Sin licencias de software (todo es open source).
- Sin tarifas por uso (no llama APIs pagas si se queda con Ollama local).

---

## Siguiente capítulo

[07 — Capítulo especial: MCP e integraciones](./07_mcp_integrations.md): cómo cualquier persona o entidad puede conectar este agente a Claude Desktop, Gemini u otros clientes MCP.
