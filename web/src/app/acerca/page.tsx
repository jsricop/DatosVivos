import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Acerca",
  description:
    "Manifiesto y propuesta de valor de DatosVivos: agente civil de datos del Estado colombiano sobre datos.gov.co. Soberanía, verificabilidad, interoperabilidad.",
  alternates: { canonical: "/acerca" },
  openGraph: {
    type: "article",
    url: "/acerca",
    title: "Acerca · DatosVivos",
    description:
      "Manifiesto y propuesta de valor: soberanía del modelo, verificabilidad por fuente, interoperabilidad MCP.",
  },
};

export default function AcercaPage() {
  return (
    <div className="container-narrow py-12">
      <article className="measure-narrow flex flex-col gap-6">
        <header className="pb-4 hairline-bottom">
          <span className="text-kicker">Manifiesto</span>
          <h1 className="m-0 mt-2 font-sans text-h1">
            Datos del Estado, en tus palabras.
          </h1>
        </header>

        <P>
          DatosVivos es un agente civil de datos del Estado colombiano.
          Funciona sobre{" "}
          <a
            href="https://www.datos.gov.co"
            target="_blank"
            rel="noopener noreferrer"
            className="focus-ring"
          >
            datos.gov.co
          </a>
          {" "}— el portal de datos abiertos operado por MinTIC con más de
          8.000 datasets publicados por entidades nacionales y territoriales.
        </P>
        <P>
          Una persona pregunta en su idioma — el del barrio, el del trabajo,
          el del periódico — y el agente responde ejecutando consultas reales
          contra el catálogo. Cada cifra está calculada con{" "}
          <code className="font-mono">pandas</code> sobre las filas devueltas
          por el dataset citado. El modelo de lenguaje corre localmente en una
          máquina del Estado — no se exportan consultas a servicios externos.
        </P>

        <section className="mt-6">
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

        <section className="mt-6 pt-6 hairline-top">
          <span className="text-kicker">Equipo</span>
          <h2 className="m-0 mt-2 mb-3 font-sans text-h3 font-semibold">
            Oficina de Tecnología — Agencia Nacional de Infraestructura (ANI)
          </h2>
          <P>
            Proyecto presentado al concurso{" "}
            <em>Datos al Ecosistema 2026: IA para Colombia</em>, Reto #07
            (Innovación y Tecnología) del Ministerio TIC.
          </P>
        </section>

        <section className="mt-6 pt-6 hairline-top">
          <span className="text-kicker">Documentación</span>
          <ul className="mt-3 flex flex-col gap-2">
            <li>
              <Link href="/accesibilidad" className="focus-ring">
                Accesibilidad
              </Link>
            </li>
            <li>
              <a
                href="https://github.com/jsricop/DatosVivos"
                target="_blank"
                rel="noopener noreferrer"
                className="focus-ring"
              >
                Repositorio de código en GitHub
              </a>
            </li>
            <li>
              <a
                href="https://www.datos.gov.co"
                target="_blank"
                rel="noopener noreferrer"
                className="focus-ring"
              >
                Portal datos.gov.co
              </a>
            </li>
          </ul>
        </section>
      </article>
    </div>
  );
}

function P({ children }: { children: React.ReactNode }) {
  return (
    <p className="m-0 font-sans text-body-lg leading-relaxed text-ink">{children}</p>
  );
}

function Pilar({ number, title, body }: { number: string; title: string; body: string }) {
  return (
    <article className="py-4 hairline-bottom">
      <span className="text-kicker">{number} · Pilar</span>
      <h3 className="m-0 mt-2 mb-2 font-sans text-h3">{title}</h3>
      <p className="m-0 font-sans text-body text-ink leading-relaxed">{body}</p>
    </article>
  );
}
