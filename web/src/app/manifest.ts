import type { MetadataRoute } from "next";

/**
 * Web App Manifest (PWA) — permite instalar DatosVivos en mobile/desktop como
 * app del Estado. Sin SW pendiente: solo metadata para "Añadir a inicio".
 *
 * Generado dinámicamente por Next.js como `/manifest.webmanifest`.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "DatosVivos — Datos del Estado, en tus palabras",
    short_name: "DatosVivos",
    description:
      "Agente civil de datos abiertos del Estado colombiano. Pregunta en lenguaje natural sobre cualquier dato público y recibe la respuesta con la fuente original a un click.",
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
