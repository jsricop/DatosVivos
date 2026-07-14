import type { MetadataRoute } from "next";

/**
 * Web App Manifest (PWA) — permite instalar DatosVivos en mobile/desktop como
 * app del Estado. Sin SW pendiente: solo metadata para "Añadir a inicio".
 *
 * Generado dinámicamente por Next.js como `/manifest.webmanifest`.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "DatosVivos — El panorama de los datos abiertos de Colombia",
    short_name: "DatosVivos",
    description:
      "El panorama de los datos abiertos de Colombia: cifras en vivo del catálogo que integra datos.gov.co y los portales territoriales, tablero interactivo por sector y entidad, y consultas en lenguaje natural con fuente verificable.",
    start_url: "/",
    display: "standalone",
    background_color: "#FFFFFF",
    theme_color: "#004884",
    orientation: "any",
    lang: "es-CO",
    dir: "ltr",
    categories: ["government", "education", "news", "productivity"],
    icons: [
      { src: "/favicon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
      {
        src: "/favicon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/favicon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
