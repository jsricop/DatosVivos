import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Servidor MCP",
  description:
    "Conecta cualquier agente de IA al catálogo de datos abiertos de Colombia: el motor de DatosVivos expuesto como servidor MCP (Model Context Protocol).",
  alternates: { canonical: "/mcp" },
};

/**
 * Las 4 herramientas con su llamada REAL (firma exacta de mcp_server/tools/)
 * y lo que devuelven. Los ejemplos usan el caso verificado de Boyacá.
 */
const TOOLS = [
  {
    name: "search_datasets",
    desc: "Busca datasets en el catálogo por palabras clave. Devuelve id, nombre, entidad, filas y enlace de los mejores matches.",
    pides: "«Busca datasets de establecimientos educativos en Boyacá»",
    llamada: `search_datasets(query="establecimientos educativos Boyacá", limit=5)`,
    devuelve: `[{ "id": "emd6-ef7x", "name": "Establecimientos Educativos del sector oficial y no oficial…",
   "entity": "Gobernación de Boyacá", "rows_count": 2184, … }]`,
  },
  {
    name: "get_metadata",
    desc: "El esquema completo de un dataset: columnas tipadas con descripción, filas, entidad y fechas de actualización.",
    pides: "«¿Qué columnas tiene ese dataset?»",
    llamada: `get_metadata(dataset_id="emd6-ef7x")`,
    devuelve: `{ "columns": [{ "field_name": "sector", "type": "text", … },
              { "field_name": "municipio", "type": "text", … }, … ],
  "rows_count": 2184, … }`,
  },
  {
    name: "query_data",
    desc: "Ejecuta una consulta SoQL sobre el dataset y devuelve las filas. El agente arma la consulta; los datos salen del portal oficial.",
    pides: "«¿Cuántos son del sector oficial?»",
    llamada: `query_data(dataset_id="emd6-ef7x", soql_query="SELECT count(*) AS n WHERE sector='OFICIAL'")`,
    devuelve: `[{ "n": "1721" }]`,
  },
  {
    name: "cross_datasets",
    desc: "Cruza de 2 a 5 datasets por una clave compartida (DIVIPOLA, código DANE, NIT) — verifica que la clave exista en cada uno antes del join.",
    pides: "«Cruza los establecimientos con la matrícula por municipio»",
    llamada: `cross_datasets(dataset_ids=["emd6-ef7x", "qpq9-e4ne"], join_keys="municipio",
               select_columns=["municipio", "sector", "total_ie"])`,
    devuelve: `[{ "municipio": "TUNJA", "sector": "OFICIAL", "total_ie": … }, …]`,
  },
];

function Code({ children }: { children: React.ReactNode }) {
  return (
    <pre className="m-0 overflow-x-auto rounded-[var(--radius-1)] border border-hairline bg-bg-elev p-4 font-mono text-caption text-ink leading-relaxed">
      {children}
    </pre>
  );
}

export default function McpPage() {
  return (
    <div className="container-narrow flex flex-col gap-8 py-12">
      <header className="pb-4 hairline-bottom">
        <span className="text-kicker">Para desarrolladores y agentes de IA</span>
        <h1 className="m-0 mt-2 font-sans text-h1">El MCP de DatosVivos</h1>
        <p className="m-0 mt-3 max-w-[70ch] font-sans text-body-lg text-ink-2 leading-relaxed">
          El mismo motor que responde en el{" "}
          <Link href="/buscar" className="focus-ring">
            buscador
          </Link>{" "}
          está expuesto como servidor <strong>MCP</strong> (Model Context
          Protocol): cualquier agente de IA — Claude, o cualquier cliente
          compatible — puede buscar, consultar y cruzar los datos abiertos de
          Colombia como herramientas nativas.
        </p>
      </header>

      <section className="flex flex-col gap-3">
        <h2 className="m-0 text-h3">Cómo conectarse</h2>
        <p className="m-0 max-w-[70ch] font-sans text-body-sm text-ink-2 leading-relaxed">
          El servidor es de código abierto y corre junto al resto del stack.
          Clona el repositorio y levanta el servicio:
        </p>
        <Code>
          {`git clone https://github.com/jsricop/DatosVivos.git
cd DatosVivos
docker compose up -d mcp-server
# SSE endpoint: http://localhost:3000/sse`}
        </Code>
        <p className="m-0 max-w-[70ch] font-sans text-body-sm text-ink-2 leading-relaxed">
          MCP es un protocolo abierto: el servidor funciona con{" "}
          <strong>cualquier cliente que lo soporte</strong>. Configuración por
          cliente:
        </p>

        <h3 className="m-0 mt-1 text-h4">Claude (Code / Desktop)</h3>
        <Code>{`# Claude Code — un comando:
claude mcp add --transport sse datosvivos http://localhost:3000/sse

# Claude Desktop — claude_desktop_config.json:
{ "mcpServers": { "datosvivos": { "url": "http://localhost:3000/sse" } } }`}</Code>

        <h3 className="m-0 mt-1 text-h4">OpenAI (Agents SDK / Responses API)</h3>
        <Code>{`# Agents SDK (pip install openai-agents):
from agents import Agent, Runner
from agents.mcp import MCPServerSse

async with MCPServerSse(params={"url": "http://localhost:3000/sse"}) as mcp:
    agent = Agent(name="datos-colombia", mcp_servers=[mcp])
    out = await Runner.run(agent, "¿Cuántos colegios oficiales hay en Boyacá?")

# Responses API (exige URL pública — expón el servidor o usa un túnel):
client.responses.create(
    model="gpt-4.1",
    tools=[{"type": "mcp", "server_label": "datosvivos",
            "server_url": "https://<tu-host>/sse"}],
    input="¿Cuántos colegios oficiales hay en Boyacá?")`}</Code>

        <h3 className="m-0 mt-1 text-h4">Cursor · VS Code (GitHub Copilot) · Gemini CLI</h3>
        <Code>{`# Cursor — ~/.cursor/mcp.json:
{ "mcpServers": { "datosvivos": { "url": "http://localhost:3000/sse" } } }

# VS Code (Copilot agent mode) — .vscode/mcp.json:
{ "servers": { "datosvivos": { "type": "sse", "url": "http://localhost:3000/sse" } } }

# Gemini CLI — ~/.gemini/settings.json:
{ "mcpServers": { "datosvivos": { "url": "http://localhost:3000/sse" } } }`}</Code>

        <h3 className="m-0 mt-1 text-h4">Grok, DeepSeek, Llama u otro modelo</h3>
        <p className="m-0 max-w-[70ch] font-sans text-body-sm text-ink-2 leading-relaxed">
          Esos modelos no traen cliente MCP propio: se conectan a través de un
          cliente que sí lo soporte eligiendo el modelo ahí (Cursor, Cline,
          Continue aceptan Grok/DeepSeek como backend), o programáticamente con
          el SDK oficial de MCP — útil para cualquier stack:
        </p>
        <Code>{`# pip install mcp — cliente universal en Python:
from mcp import ClientSession
from mcp.client.sse import sse_client

async with sse_client("http://localhost:3000/sse") as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        r = await session.call_tool("query_data", {
            "dataset_id": "emd6-ef7x",
            "soql_query": "SELECT count(*) AS n WHERE sector='OFICIAL'"})
        # → [{ "n": "1721" }] — desde aquí, cualquier LLM consume el resultado`}</Code>

        <p className="m-0 max-w-[70ch] font-sans text-body-sm text-ink-2 leading-relaxed">
          Las herramientas consultan la API pública de datos.gov.co — no
          necesitan credenciales; un App Token de Socrata (opcional, variable{" "}
          <code className="font-mono">SOCRATA_APP_TOKEN</code>) sube los límites
          de tasa.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="m-0 text-h3">Qué puede hacer un agente conectado</h2>
        <p className="m-0 max-w-[70ch] font-sans text-body-sm text-ink-2 leading-relaxed">
          Importante: <strong>estas herramientas no se llaman a mano.</strong>{" "}
          Al conectarse, el cliente las descubre automáticamente y desde ahí{" "}
          <strong>el propio modelo decide</strong> cuál usar, con qué argumentos
          y en qué orden, según lo que le pidas en lenguaje natural. Una sola
          pregunta puede disparar la cadena completa:
        </p>
        <Code>{`Tú:        "¿Cuántos colegios oficiales hay en Boyacá?"

El agente decide y encadena, solo:
  1. search_datasets("establecimientos educativos Boyacá")  → encuentra emd6-ef7x
  2. get_metadata("emd6-ef7x")                              → descubre la columna sector
  3. query_data("emd6-ef7x", "SELECT count(*) WHERE sector='OFICIAL'")  → 1721

Agente:    "Hay 1.721 establecimientos oficiales en Boyacá,
            según la Gobernación de Boyacá (dataset emd6-ef7x)."`}</Code>
        <p className="m-0 max-w-[70ch] font-sans text-body-sm text-ink-2 leading-relaxed">
          Las 4 herramientas que el agente tiene disponibles — cada tarjeta
          muestra un ejemplo real de petición, llamada y respuesta:
        </p>
        <ul className="m-0 flex list-none flex-col gap-4 p-0">
          {TOOLS.map((t) => (
            <li key={t.name} className="surface-card flex flex-col gap-2 p-5">
              <code className="font-mono text-body-sm font-bold text-accent">
                {t.name}
              </code>
              <p className="m-0 font-sans text-body-sm text-ink-2 leading-relaxed">
                {t.desc}
              </p>
              <p className="m-0 font-sans text-caption text-ink-2">
                <span className="font-mono uppercase text-ink-muted">Pides </span>
                {t.pides}
              </p>
              <div className="flex flex-col gap-1">
                <span className="font-mono text-[length:var(--type-kicker)] uppercase tracking-wide text-ink-muted">
                  El agente llama
                </span>
                <Code>{t.llamada}</Code>
              </div>
              <div className="flex flex-col gap-1">
                <span className="font-mono text-[length:var(--type-kicker)] uppercase tracking-wide text-ink-muted">
                  La herramienta devuelve
                </span>
                <Code>{t.devuelve}</Code>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {/* Nota de transparencia: una línea, sin sección — es la garantía del
          proyecto, pero aquí el tono es técnico. */}
      <p className="m-0 hairline-top pt-4 font-mono text-caption text-ink-muted">
        Las herramientas devuelven filas y metadatos reales del portal oficial:
        el agente razona, los datos salen de la fuente. Código en{" "}
        <code>mcp_server/</code>, licencia abierta.
      </p>
    </div>
  );
}
