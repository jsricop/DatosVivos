import type { Metadata } from "next";

import { getEmbedHeight, getEmbedUrl, isEmbedConfigured } from "@/lib/embed";

export const metadata: Metadata = {
  title: "Tablero del catálogo",
  description:
    "Estado y salud del catálogo de datos abiertos del Estado colombiano: orígenes, acceso, actualización y cobertura. Fuente: datos.gov.co.",
  alternates: { canonical: "/tablero" },
  openGraph: {
    type: "website",
    url: "/tablero",
    title: "Tablero del catálogo · DatosVivos",
    description:
      "Analítica en vivo del catálogo de datos abiertos de Colombia: orígenes, acceso, actualización y cobertura.",
  },
};

// force-dynamic → la URL del embed se lee de `PBI_EMBED_URL` en cada request
// (runtime), no en build. Cambiarla solo requiere reiniciar el contenedor web.
export const dynamic = "force-dynamic";

export default function TableroPage() {
  const embedUrl = getEmbedUrl();
  const embedHeight = getEmbedHeight();
  const ready = isEmbedConfigured();

  return (
    <div className="container-narrow flex flex-col gap-6 py-8">
      <header className="pb-4 hairline-bottom">
        <span className="text-kicker">Tablero</span>
        <h1 className="m-0 mt-2 font-sans text-h1">Analítica del catálogo</h1>
        <p className="m-0 mt-2 max-w-[62ch] font-sans text-body text-ink-2 leading-relaxed">
          Estado y salud del catálogo de datos abiertos del Estado colombiano —
          orígenes, acceso, frescura y cobertura. Datos agregados del catálogo
          público de{" "}
          <a
            href="https://www.datos.gov.co"
            target="_blank"
            rel="noopener noreferrer"
            className="focus-ring"
          >
            datos.gov.co
          </a>
          .
        </p>
      </header>

      {ready ? (
        <section
          aria-label="Tablero del catálogo"
          className="surface-elev p-0 overflow-hidden"
        >
          <iframe
            src={embedUrl}
            title="Tablero del catálogo — DatosVivos"
            allowFullScreen
            loading="lazy"
            referrerPolicy="strict-origin-when-cross-origin"
            className="w-full border-0 block bg-bg-elev"
            style={{ height: `${embedHeight}px` }}
          />
        </section>
      ) : (
        <section className="surface-elev p-6 flex flex-col gap-3">
          <span className="text-kicker">Tablero no disponible aún</span>
          <p className="m-0 font-sans text-body text-ink-2 leading-relaxed">
            El dashboard todavía no está publicado. Cuando ANI lo publique con
            «Publicar en la web» desde Power BI Service y se configure la
            variable <code className="font-mono">PBI_EMBED_URL</code>, el tablero
            aparecerá aquí.
          </p>
        </section>
      )}
    </div>
  );
}
