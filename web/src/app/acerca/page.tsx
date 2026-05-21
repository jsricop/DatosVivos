import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Acerca",
  description:
    "Manifiesto y propuesta de valor de DatosVivos: agente civil de datos del Estado colombiano sobre datos.gov.co.",
};

export default function AcercaPage() {
  return (
    <div
      className="container-narrow"
      style={{ paddingBlock: "var(--space-7)" }}
    >
      <article
        className="measure-narrow"
        style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}
      >
        <header
          style={{
            paddingBlockEnd: "var(--space-4)",
            borderBlockEnd: "1px solid var(--hairline)",
          }}
        >
          <span className="kicker">Manifiesto</span>
          <h1
            style={{
              margin: "8px 0 0 0",
              fontFamily: "var(--font-serif)",
              fontSize: "var(--type-h1)",
            }}
          >
            Datos del Estado, en tus palabras.
          </h1>
        </header>

        <p style={pStyle}>
          DatosVivos es un agente civil de datos del Estado colombiano. Funciona
          sobre {" "}
          <a href="https://www.datos.gov.co" target="_blank" rel="noopener noreferrer">
            datos.gov.co
          </a>{" "}
          — el portal de datos abiertos operado por MinTIC con más de 8.000
          datasets publicados por entidades nacionales y territoriales.
        </p>
        <p style={pStyle}>
          Una persona pregunta en su idioma — el del barrio, el del trabajo, el
          del periódico — y el agente responde ejecutando consultas reales
          contra el catálogo. Cada cifra está calculada con{" "}
          <code className="mono">pandas</code> sobre las filas devueltas por el
          dataset citado. El modelo de lenguaje corre localmente en una máquina
          del Estado — no se exportan consultas a servicios externos.
        </p>

        <section style={{ marginBlockStart: "var(--space-5)" }}>
          <Pilar
            number="01"
            title="Soberanía"
            body="El modelo corre localmente. Ni Anthropic ni OpenAI ni nadie más leen las consultas ciudadanas. La VM productiva está bajo VPN del Estado."
          />
          <Pilar
            number="02"
            title="Verificabilidad"
            body="Cada respuesta enumera los datasets consultados con su ID, su página humana en datos.gov.co y su endpoint JSON SODA. Cero cifras inventadas: si el modelo intenta colar un número fuera de la lista calculada por pandas, esa oración se censura antes de mostrarse."
          />
          <Pilar
            number="03"
            title="Interoperabilidad"
            body="Las cuatro herramientas internas (search_datasets, get_metadata, query_data, cross_datasets) se exponen como MCP Server estándar. Cualquier cliente MCP (Claude Desktop, Cursor, agentes Gemini, otros) puede consumirlas sin pasar por esta interfaz."
          />
        </section>

        <section
          style={{
            marginBlockStart: "var(--space-5)",
            paddingBlockStart: "var(--space-5)",
            borderBlockStart: "1px solid var(--hairline)",
          }}
        >
          <span className="kicker">Equipo</span>
          <h2
            style={{
              margin: "8px 0 12px 0",
              fontFamily: "var(--font-serif)",
              fontSize: "var(--type-h3)",
              fontWeight: 600,
            }}
          >
            Oficina de Tecnología — Agencia Nacional de Infraestructura (ANI)
          </h2>
          <p style={pStyle}>
            Proyecto presentado al concurso{" "}
            <em>Datos al Ecosistema 2026: IA para Colombia</em>, Reto #07
            (Innovación y Tecnología) del Ministerio TIC.
          </p>
        </section>

        <section
          style={{
            marginBlockStart: "var(--space-5)",
            paddingBlockStart: "var(--space-5)",
            borderBlockStart: "1px solid var(--hairline)",
          }}
        >
          <span className="kicker">Documentación</span>
          <ul style={{ marginBlockStart: 12, display: "flex", flexDirection: "column", gap: 8 }}>
            <li>
              <Link href="/accesibilidad">Accesibilidad</Link>
            </li>
            <li>
              <a href="https://github.com/jsricop/DatosVivos" target="_blank" rel="noopener noreferrer">
                Repositorio de código en GitHub
              </a>
            </li>
            <li>
              <a href="https://www.datos.gov.co" target="_blank" rel="noopener noreferrer">
                Portal datos.gov.co
              </a>
            </li>
          </ul>
        </section>
      </article>
    </div>
  );
}

const pStyle: React.CSSProperties = {
  margin: 0,
  fontFamily: "var(--font-sans)",
  fontSize: "var(--type-body-lg)",
  lineHeight: 1.65,
  color: "var(--ink)",
};

function Pilar({
  number,
  title,
  body,
}: {
  number: string;
  title: string;
  body: string;
}) {
  return (
    <article
      style={{
        paddingBlock: "var(--space-4)",
        borderBlockEnd: "1px solid var(--hairline)",
      }}
    >
      <span className="kicker">{number} · Pilar</span>
      <h3
        style={{
          margin: "8px 0 8px 0",
          fontFamily: "var(--font-serif)",
          fontSize: "var(--type-h3)",
        }}
      >
        {title}
      </h3>
      <p style={{ ...pStyle, fontSize: "var(--type-body)" }}>{body}</p>
    </article>
  );
}
