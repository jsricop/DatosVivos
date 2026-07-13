import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Servidor MCP",
  description:
    "Conecta cualquier agente de IA al catálogo de datos abiertos de Colombia: el motor de DatosVivos expuesto como servidor MCP (Model Context Protocol).",
  alternates: { canonical: "/mcp" },
};

const TOOLS = [
  {
    name: "search_datasets",
    desc: "Busca datasets en el catálogo por texto libre. Devuelve id, nombre, entidad y metadatos de los mejores matches.",
    ejemplo: "«Busca datasets sobre matrícula escolar en Boyacá»",
  },
  {
    name: "get_metadata",
    desc: "Metadata completa de un dataset: columnas tipadas, filas, entidad publicadora, fechas de actualización.",
    ejemplo: "«¿Qué columnas tiene el dataset emd6-ef7x?»",
  },
  {
    name: "query_data",
    desc: "Ejecuta una consulta SoQL sobre un dataset nativo de datos.gov.co y devuelve las filas. El agente arma la consulta; los datos salen del portal oficial.",
    ejemplo: "«Cuenta los establecimientos con sector OFICIAL»",
  },
  {
    name: "cross_datasets",
    desc: "Cruza dos o más datasets por columnas llave (join) y devuelve el resultado combinado — análisis que ningún portal ofrece por sí solo.",
    ejemplo: "«Cruza matrícula con población municipal por código DANE»",
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
    <div className="container-narrow py-12">
      <article className="measure flex flex-col gap-8">
        <header className="pb-4 hairline-bottom">
          <span className="text-kicker">Para desarrolladores y agentes de IA</span>
          <h1 className="m-0 mt-2 font-sans text-h1">El MCP de DatosVivos</h1>
          <p className="m-0 mt-3 max-w-[62ch] font-sans text-body-lg text-ink-2 leading-relaxed">
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
          <h2 className="m-0 text-h3">Qué puede hacer un agente conectado</h2>
          <ul className="m-0 flex list-none flex-col gap-3 p-0">
            {TOOLS.map((t) => (
              <li key={t.name} className="surface-card p-4">
                <code className="font-mono text-body-sm font-bold text-accent">
                  {t.name}
                </code>
                <p className="m-0 mt-1 font-sans text-body-sm text-ink-2 leading-relaxed">
                  {t.desc}
                </p>
                <p className="m-0 mt-1 font-mono text-caption text-ink-muted">
                  {t.ejemplo}
                </p>
              </li>
            ))}
          </ul>
          <p className="m-0 font-sans text-body-sm text-ink-2 leading-relaxed">
            Combinadas, permiten flujos completos: <em>descubrir</em> el dataset
            correcto, <em>entender</em> sus columnas, <em>consultar</em> la
            cifra exacta y <em>cruzar</em> fuentes — siempre contra los datos
            oficiales, nunca inventando.
          </p>
        </section>

        <section className="flex flex-col gap-3">
          <h2 className="m-0 text-h3">Cómo conectarse</h2>
          <p className="m-0 font-sans text-body-sm text-ink-2 leading-relaxed">
            El servidor es de código abierto y corre junto al resto del stack.
            Clona el repositorio y levanta el servicio:
          </p>
          <Code>
            {`git clone https://github.com/jsricop/DatosVivos.git
cd DatosVivos
docker compose up -d mcp-server
# SSE endpoint: http://localhost:3000/sse`}
          </Code>
          <p className="m-0 font-sans text-body-sm text-ink-2 leading-relaxed">
            En un cliente MCP (por ejemplo Claude Desktop o Claude Code), se
            registra como servidor de transporte SSE:
          </p>
          <Code>
            {`{
  "mcpServers": {
    "datosvivos": {
      "url": "http://localhost:3000/sse"
    }
  }
}`}
          </Code>
          <p className="m-0 font-sans text-body-sm text-ink-2 leading-relaxed">
            Las herramientas consultan la API pública de datos.gov.co — no
            necesitan credenciales; un App Token de Socrata (opcional) sube los
            límites de tasa.
          </p>
        </section>

        <section className="flex flex-col gap-2">
          <h2 className="m-0 text-h3">Transparencia</h2>
          <p className="m-0 font-sans text-body-sm text-ink-2 leading-relaxed">
            El MCP entrega filas y metadatos reales del portal oficial: la misma
            garantía del buscador — el agente razona, los datos salen de la
            fuente. El código está en el repositorio del proyecto
            (`mcp_server/`), con la misma licencia abierta.
          </p>
        </section>
      </article>
    </div>
  );
}
