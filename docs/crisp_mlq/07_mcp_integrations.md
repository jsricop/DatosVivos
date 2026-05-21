# 07 — Capítulo especial: MCP e integraciones

> **Para entender este capítulo no es necesario haber leído los anteriores.** Aquí explicamos qué es MCP, por qué DatosVivos lo usa, y cómo cualquier persona o entidad puede conectarlo a sus propios asistentes de IA (Claude, Gemini, Cursor, agentes propios).

## Resumen ejecutivo

**MCP** (Model Context Protocol) es un protocolo abierto creado por Anthropic en 2024, adoptado luego por Google, OpenAI y la comunidad, que permite que un asistente de IA (Claude, Gemini, etc.) consuma herramientas externas de forma estándar. DatosVivos publica sus 4 herramientas sobre `datos.gov.co` como un **MCP server**. Esto significa que **cualquier asistente de IA compatible con MCP puede usar DatosVivos sin que escribamos un conector especial para cada uno**.

Es el equivalente, en el mundo de los agentes de IA, a lo que un puerto USB es para los periféricos: un solo estándar, muchos clientes.

---

## 🏛️ Para el jurado MinTIC

### Por qué este capítulo es relevante

El reto pide *"asistentes virtuales que faciliten el acceso ciudadano a datos abiertos"*. DatosVivos cumple eso con su propia UI (Streamlit), **pero además abre la inteligencia a cualquier asistente que el ciudadano ya use**: Claude Desktop, ChatGPT Desktop, Cursor, Gemini, Continue, agentes corporativos propios.

**Implicaciones:**

- **Multiplicador de impacto:** una entidad pública puede ofrecer DatosVivos via su asistente interno corporativo sin desarrollar un conector.
- **Soberanía + interoperabilidad:** los datos siguen siendo locales (LLM Ollama), pero la *experiencia* del agente puede vivir en el cliente que el usuario prefiera.
- **Estándar abierto, no captura tecnológica:** MCP es spec pública con SDKs en Python y TypeScript, mantenida con governance abierto.

### Estado del soporte MCP en clientes principales (a la fecha de la entrega)

| Cliente | Soporte MCP | Transporte | Verificable |
|---|---|---|---|
| **Claude Desktop** (Anthropic) | ✅ Nativo | stdio + SSE | Sí, oficial |
| **Cursor** | ✅ Nativo | stdio | Sí, oficial |
| **Continue** (VS Code / JetBrains) | ✅ Nativo | stdio + SSE | Sí, oficial |
| **Google Gemini / AI Studio** | ✅ Vía adapter MCP-A2A | SSE | Sí, en `agent2agent.dev` |
| **ChatGPT Desktop** (OpenAI) | ✅ MCP en cliente | stdio + SSE | Sí, oficial |
| **Agentes propios** (Python / TS SDK) | ✅ Cualquier SDK MCP | Ambos | Sí |

---

## 🛠️ Para ciudadanos técnicos: instalación y uso

### Arquitectura del servidor MCP de DatosVivos

```
┌──────────────────────────────┐
│   Cliente MCP                │  (Claude Desktop, Cursor, Gemini, propio…)
└──────────────┬───────────────┘
               │ JSON-RPC 2.0
               │ (stdio o SSE)
               ▼
┌──────────────────────────────────────────────────────┐
│   DatosVivos MCP Server (mcp_server/server.py)       │
│                                                      │
│   Tools registradas:                                 │
│   ├── search_datasets(query, limit)                  │
│   ├── get_metadata(dataset_id)                       │
│   ├── query_data(dataset_id, soql_query, limit, ...) │
│   └── cross_datasets(dataset_ids, join_keys, ...)    │
└──────────────┬───────────────────────────────────────┘
               │ HTTPS
               ▼
       datos.gov.co (Socrata)
```

### Tools expuestas — contrato completo

#### `search_datasets`

```jsonc
{
  "name": "search_datasets",
  "input": {
    "query": "string",
    "limit": "integer (default 10, máx 25)"
  },
  "output": "lista de datasets con id, name, description, entity, updated_at, columns_count, rows_count, category, permalink"
}
```

Aplica búsqueda multi-tier (acrónimos → topic keywords → reformulación LLM en el caller).

#### `get_metadata`

```jsonc
{
  "name": "get_metadata",
  "input": { "dataset_id": "string (id Socrata, ej. 'gdxc-w37w')" },
  "output": "dict con id, name, description, columns (lista de {name, type, description})"
}
```

#### `query_data`

```jsonc
{
  "name": "query_data",
  "input": {
    "dataset_id": "string",
    "soql_query": "string (SoQL, opcional — default 'SELECT *')",
    "limit": "integer (default 1000)",
    "offset": "integer (default 0)"
  },
  "output": "lista de filas como dicts"
}
```

#### `cross_datasets`

```jsonc
{
  "name": "cross_datasets",
  "input": {
    "dataset_ids": "list[string] (1..5 datasets)",
    "join_keys": "string | list[string] (clave de join, ej. 'cod_dpto')",
    "select_columns": "list[string] (opcional, filtra columnas finales)",
    "per_dataset_limit": "integer (opcional, cap por dataset)"
  },
  "output": "lista de filas merged via pandas.merge"
}
```

### Cómo levantar el server localmente

#### Vía Docker (recomendado para uso por terceros)

```bash
docker run -d --name datosvivos-mcp \
  -p 3000:3000 \
  -e MCP_TRANSPORT=sse \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=3000 \
  ghcr.io/anibogota/datosvivos-mcp:latest

# Verificar
curl http://localhost:3000/sse
```

#### Vía source (para integraciones stdio locales como Claude Desktop)

```bash
git clone https://github.com/jsricop/DatosVivos
cd DatosVivos
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.mcp.txt

# stdio (típico para clientes locales)
MCP_TRANSPORT=stdio python -m mcp_server.server
# o SSE
MCP_TRANSPORT=sse MCP_PORT=3000 python -m mcp_server.server
```

### Integración 1: Claude Desktop (Anthropic)

**Pre-requisito:** Claude Desktop instalado (macOS, Windows, Linux).

1. Abre el archivo de configuración:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. Agrega bajo `mcpServers`:

```json
{
  "mcpServers": {
    "datosvivos": {
      "command": "/ruta/absoluta/a/DatosVivos/.venv/bin/python",
      "args": ["-m", "mcp_server.server"],
      "env": {
        "MCP_TRANSPORT": "stdio",
        "PYTHONPATH": "/ruta/absoluta/a/DatosVivos"
      }
    }
  }
}
```

3. Reinicia Claude Desktop. En la conversación verás un ícono de tools 🔧 que confirma que las 4 tools están disponibles.

4. Prueba:
   > *"Usa DatosVivos para encontrar datasets sobre vivienda en Bogotá y dime cuántos hay."*

   Claude llamará `search_datasets(query="vivienda Bogotá")` y narrará el resultado.

### Integración 2: Google Gemini / AI Studio

Gemini consume MCP servers a través del proyecto **Agent-to-Agent / MCP Adapter** ([agent2agent.dev](https://agent2agent.dev)):

1. Levanta el server en modo SSE expuesto a internet (vía túnel ngrok o despliegue en VM con TLS):

```bash
docker run -d -p 3000:3000 \
  -e MCP_TRANSPORT=sse \
  ghcr.io/anibogota/datosvivos-mcp:latest
ngrok http 3000  # → https://abc123.ngrok.app
```

2. En AI Studio, agregar un **Function Tool** apuntando al adapter MCP con la URL pública (`https://abc123.ngrok.app/sse`).

3. Gemini descubrirá las 4 tools automáticamente.

> ⚠️ Para producción, NO uses ngrok: levanta el server detrás de un dominio con TLS válido (Nginx + certbot). Ngrok es solo para pruebas.

### Integración 3: Cursor

Cursor configura MCP via Settings → MCP Servers:

```json
{
  "name": "datosvivos",
  "command": "python",
  "args": ["-m", "mcp_server.server"],
  "env": {
    "MCP_TRANSPORT": "stdio",
    "PYTHONPATH": "/ruta/a/DatosVivos"
  }
}
```

Útil para que un developer pueda preguntarle a Cursor *"explora qué datasets de transporte hay en el catálogo"* mientras desarrolla.

### Integración 4: Cliente propio en Python

Si una entidad tiene su propio agente y quiere agregar DatosVivos:

```python
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async with sse_client("https://datosvivos.tu-entidad.gov.co/sse") as (r, w):
    async with ClientSession(r, w) as session:
        await session.initialize()
        # Listar tools disponibles
        tools = await session.list_tools()
        # Llamar una
        result = await session.call_tool(
            "search_datasets",
            {"query": "calidad del aire", "limit": 5},
        )
        for block in result.content:
            print(block.text)
```

Ejemplos completos están en nuestros tests: [`tests/test_mcp_server_sse.py`](../../tests/test_mcp_server_sse.py) y [`tests/test_mcp_server_stdio.py`](../../tests/test_mcp_server_stdio.py).

### Integración 5: Cliente propio en TypeScript

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

const transport = new SSEClientTransport(
  new URL("https://datosvivos.tu-entidad.gov.co/sse"),
);
const client = new Client({ name: "my-app", version: "0.1" }, { capabilities: {} });
await client.connect(transport);
const result = await client.callTool({
  name: "search_datasets",
  arguments: { query: "vivienda", limit: 5 },
});
```

### Consideraciones de seguridad para exposición pública

Si una entidad va a publicar este MCP server expuesto a internet, recomendamos:

1. **TLS obligatorio**: Nginx + Let's Encrypt. Nunca HTTP en producción.
2. **Rate limiting** por IP: las APIs Socrata tienen sus propios límites; protegerlas del nuestro lado.
3. **Auth opcional**: MCP soporta autenticación; para uso ciudadano libre se puede dejar público, para uso interno entidad-a-entidad recomendamos token.
4. **CORS estrictamente cerrado**: el server no debe ser invocable desde browsers de terceros sin control.
5. **Healthcheck endpoint**: `GET /sse` ya responde HEAD; útil para load balancers.

### Verificación end-to-end de tu integración

Para confirmar que tu cliente realmente está hablando con DatosVivos:

```bash
# Pregunta de "golden assertion" — Antioquia tiene 125 municipios
# Si tu cliente puede ejecutar:
#   query_data(dataset_id="gdxc-w37w",
#              soql_query="SELECT cod_dpto, count(*) AS n GROUP BY cod_dpto
#                          ORDER BY n DESC LIMIT 1")
# y obtener cod_dpto="05", n=125, todo está bien.
```

---

## 👥 Para ciudadanía general

### ¿Qué es eso de MCP?

Imagina un **enchufe universal para asistentes de IA**. Hasta hace poco, si querías que Claude o Gemini pudieran consultar `datos.gov.co`, cada asistente necesitaba un programa especial hecho a su medida. Era como tener un cargador distinto para cada marca de teléfono.

**MCP** es un acuerdo entre las grandes empresas de IA (Anthropic, Google, OpenAI y otros) para usar todos el mismo "enchufe". Nosotros construimos DatosVivos como un enchufe estándar; cualquier asistente que sepa usar ese enchufe ya tiene acceso al catálogo de datos abiertos.

### ¿Eso para qué te sirve a ti?

Hoy puedes usar DatosVivos en su página web (interfaz Streamlit). Pero si mañana tienes Claude Desktop, ChatGPT, Cursor o cualquier otro asistente, puedes pedirle que **use DatosVivos directamente**, sin abrir otra ventana:

> *"Claude, búscame en DatosVivos cuántos hospitales hay en Cundinamarca y hazme un cuadro comparativo con Bogotá."*

Y el asistente lo hará, llamando a DatosVivos detrás de bambalinas.

### ¿Esto está disponible ya?

Sí, en el código del proyecto, y documentado en este capítulo. Cualquier entidad o desarrollador puede:

- Conectar DatosVivos a Claude Desktop en 5 minutos siguiendo la guía paso a paso de arriba.
- Conectarlo a su propio asistente corporativo si tiene uno.
- Reutilizar las 4 "herramientas" del agente en sus propios procesos.

### ¿Quién lo controla?

El código es público y abierto en GitHub. Anyone puede revisar qué hace exactamente cada herramienta, qué datos toca, y cómo responde. **No hay cajas negras**: si una entidad quiere su propia copia con su propia política, puede instalarla en sus servidores en una tarde.

---

## Recursos y referencias

- **Spec MCP oficial:** [modelcontextprotocol.io](https://modelcontextprotocol.io)
- **SDK Python:** [`mcp`](https://pypi.org/project/mcp/)
- **SDK TypeScript:** [`@modelcontextprotocol/sdk`](https://www.npmjs.com/package/@modelcontextprotocol/sdk)
- **DatosVivos en GitHub:** [github.com/jsricop/DatosVivos](https://github.com/jsricop/DatosVivos)
- **Tests de referencia para integración:** `tests/test_mcp_server_{sse,stdio}.py`

---

## Fin de la documentación CRISP-ML(Q)

Volver al [índice](./00_index.md).
