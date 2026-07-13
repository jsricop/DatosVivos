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
    devuelve: `[{ "id": "emd6-ef7x",
   "name": "Establecimientos Educativos del sector oficial y no oficial…",
   "entity": "Gobernación de Boyacá", "rows_count": 2184, … }]`,
  },
  {
    name: "get_metadata",
    desc: "El esquema completo de un dataset: columnas tipadas con descripción, filas, entidad y fechas de actualización.",
    pides: "«¿Qué columnas tiene ese dataset?»",
    llamada: `get_metadata(dataset_id="emd6-ef7x")`,
    devuelve: `{ "columns": [
    { "field_name": "sector",    "type": "text", … },
    { "field_name": "municipio", "type": "text", … }, … ],
  "rows_count": 2184, … }`,
  },
  {
    name: "query_data",
    desc: "Ejecuta una consulta SoQL sobre el dataset y devuelve las filas. El agente arma la consulta; los datos salen del portal oficial.",
    pides: "«¿Cuántos son del sector oficial?»",
    llamada: `query_data(dataset_id="emd6-ef7x",
  soql_query="SELECT count(*) AS n WHERE sector='OFICIAL'")`,
    devuelve: `[{ "n": "1721" }]`,
  },
  {
    name: "cross_datasets",
    desc: "Cruza de 2 a 5 datasets por una clave compartida (DIVIPOLA, código DANE, NIT) — verifica que la clave exista en cada uno antes del join.",
    pides: "«Cruza los establecimientos con la matrícula por código de municipio»",
    llamada: `cross_datasets(
  dataset_ids=["emd6-ef7x", "qpq9-e4ne"],
  join_keys="municipio",
  select_columns=["municipio", "sector", "total_ie"])`,
    devuelve: `[{ "municipio": "TUNJA", "sector": "OFICIAL", "total_ie": … }, …]`,
  },
];

const CASOS = [
  {
    quien: "Periodista / ciudadanía",
    pregunta: "«¿Cuántos colegios oficiales hay en Boyacá y cómo se reparten por municipio?»",
    flujo:
      "El agente encadena search_datasets → get_metadata → query_data y responde 1.721 oficiales de 2.184, con el desglose municipal y el enlace a la fuente.",
  },
  {
    quien: "Analista de datos",
    pregunta: "«Cruza la matrícula escolar con los establecimientos por municipio y dame los 10 con más matrícula por colegio»",
    flujo:
      "cross_datasets une las dos fuentes por la clave territorial; el agente calcula el indicador sobre las filas reales — un análisis que ningún portal ofrece por sí solo.",
  },
  {
    quien: "Entidad publicadora",
    pregunta: "«Lista mis datasets publicados y dime cuáles no se actualizan hace más de un año»",
    flujo:
      "search_datasets por nombre de la entidad + get_metadata de cada resultado: la fecha de actualización sale de la metadata oficial, dataset por dataset.",
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
          <p className="m-0 font-sans text-body-sm text-ink-2 leading-relaxed">
            Cada tarjeta muestra el ciclo completo: lo que TÚ pides en lenguaje
            natural, la llamada que el agente construye, y lo que la herramienta
            devuelve (ejemplos reales del caso &quot;colegios oficiales en
            Boyacá&quot;).
          </p>
          <ul className="m-0 flex list-none flex-col gap-4 p-0">
            {TOOLS.map((t) => (
              <li key={t.name} className="surface-card flex flex-col gap-2 p-4">
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
                <div className="grid gap-2 md:grid-cols-2">
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
                </div>
              </li>
            ))}
          </ul>
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
            En <strong>Claude Code</strong> basta un comando:
          </p>
          <Code>{`claude mcp add --transport sse datosvivos http://localhost:3000/sse`}</Code>
          <p className="m-0 font-sans text-body-sm text-ink-2 leading-relaxed">
            En <strong>Claude Desktop</strong> (u otro cliente MCP), se registra
            en la configuración:
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
            necesitan credenciales; un App Token de Socrata (opcional, variable{" "}
            <code className="font-mono">SOCRATA_APP_TOKEN</code>) sube los
            límites de tasa.
          </p>

          <h3 className="m-0 mt-2 text-h4">Casos de uso, ya conectado</h3>
          <ul className="m-0 flex list-none flex-col gap-3 p-0">
            {CASOS.map((c) => (
              <li key={c.quien} className="surface-card p-4">
                <span className="font-mono text-[length:var(--type-kicker)] uppercase tracking-wide text-accent">
                  {c.quien}
                </span>
                <p className="m-0 mt-1 font-sans text-body-sm font-semibold text-ink">
                  {c.pregunta}
                </p>
                <p className="m-0 mt-1 font-sans text-caption text-ink-2 leading-relaxed">
                  {c.flujo}
                </p>
              </li>
            ))}
          </ul>
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
