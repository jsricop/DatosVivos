import type { Metadata } from "next";
import Link from "next/link";

import { fetchCatalogStats } from "@/lib/api";

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

export default async function AcercaPage() {
  // Conteo en vivo desde la misma vista que el tablero (nunca quemado). Se
  // redondea hacia abajo al millar para que el "más de N" siga siendo cierto
  // conforme el catálogo crece. Si el backend no responde, degrada a "miles de".
  const stats = await fetchCatalogStats();
  const totalDatasets =
    stats && stats.total > 0
      ? `más de ${(Math.floor(stats.total / 1000) * 1000).toLocaleString("es-CO")}`
      : "miles de";

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
          DatosVivos muestra el estado de los datos abiertos del Estado
          colombiano. Integra en un solo catálogo el portal nacional{" "}
          <a
            href="https://www.datos.gov.co"
            target="_blank"
            rel="noopener noreferrer"
            className="focus-ring"
          >
            datos.gov.co
          </a>
          {" "}(operado por MinTIC), el geoportal del IGAC y los portales
          territoriales de Bogotá, Cali, Medellín y Valle del Cauca —{" "}
          {totalDatasets} datasets de entidades nacionales y territoriales —
          y lo presenta en tres niveles: el{" "}
          <Link href="/" className="focus-ring">
            panorama nacional
          </Link>{" "}
          con cifras en vivo, el{" "}
          <Link href="/tablero" className="focus-ring">
            tablero interactivo
          </Link>{" "}
          para explorar por sector y entidad, y el{" "}
          <Link href="/buscar" className="focus-ring">
            buscador
          </Link>{" "}
          para preguntar en lenguaje natural.
        </P>
        <P>
          Sin registro y sin rastreadores. Cada cifra del buscador se calcula
          sobre las filas reales del dataset citado — nunca se estima.
        </P>

        <section className="mt-6">
          <Pilar
            number="01"
            title="Soberanía"
            body="El servicio corre sobre infraestructura del Estado colombiano y las estadísticas de uso son anónimas. Los datos que se consultan son públicos."
          />
          <Pilar
            number="02"
            title="Verificabilidad"
            body="Cada respuesta enumera los datasets consultados, con enlace a su página oficial en el portal de origen. Cero cifras inventadas: cada número sale de las filas reales del dataset; si un número no se puede calcular a partir de ellas, no se muestra."
          />
          <Pilar
            number="03"
            title="Interoperabilidad"
            body="Las herramientas internas del agente se publican con el estándar abierto MCP, de modo que otros sistemas y asistentes de IA pueden consultar el catálogo directamente, sin pasar por esta página."
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
