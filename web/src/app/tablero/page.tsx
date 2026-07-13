import type { Metadata } from "next";
import Link from "next/link";

import { getEmbedHeight, getEmbedUrl, isEmbedConfigured } from "@/lib/embed";

export const metadata: Metadata = {
  title: "Tablero del catálogo",
  description:
    "El detalle del panorama de datos abiertos de Colombia: explora el catálogo por sector, entidad y territorio con filtros interactivos. Fuente: datos.gov.co.",
  alternates: { canonical: "/tablero" },
  openGraph: {
    type: "website",
    url: "/tablero",
    title: "Tablero del catálogo · DatosVivos",
    description:
      "Explora el catálogo de datos abiertos de Colombia por sector, entidad y territorio con filtros interactivos.",
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
    <div className="flex flex-col gap-6 py-8">
      <header className="container-narrow w-full pb-4 hairline-bottom">
        <span className="text-kicker">Tablero</span>
        <h1 className="m-0 mt-2 font-sans text-h1">
          El detalle, por sector y entidad
        </h1>
        <p className="m-0 mt-2 max-w-[62ch] font-sans text-body text-ink-2 leading-relaxed">
          Explora el catálogo de datos abiertos con filtros interactivos:
          salud y frescura, uso, y cobertura territorial — por sector, entidad,
          tipo de acceso y territorio. La visión nacional resumida está en la{" "}
          <Link href="/" className="focus-ring">
            página principal
          </Link>
          ; la fuente es el catálogo público de{" "}
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
          className="mx-auto w-full max-w-[1440px] px-[clamp(8px,2vw,32px)]"
        >
          {/* El alto sigue al ancho con la proporción del reporte Power BI
              (página 16:9 + 56px de barra inferior): así "Ajustar a la
              página" llena el marco a ~100% en cualquier resolución, sin
              verse gigante ni al 83% (2026-07-13). */}
          <div
            className="surface-elev relative w-full overflow-hidden p-0"
            style={{ paddingBottom: "calc(56.25% + 56px)", minHeight: embedHeight }}
          >
            <iframe
              src={embedUrl}
              title="Tablero del catálogo — DatosVivos"
              allowFullScreen
              loading="lazy"
              referrerPolicy="strict-origin-when-cross-origin"
              className="absolute inset-0 block h-full w-full border-0 bg-bg-elev"
            />
          </div>
        </section>
      ) : (
        <section className="container-narrow w-full surface-elev p-6 flex flex-col gap-3">
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
