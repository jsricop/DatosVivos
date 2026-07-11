/**
 * Constantes del sitio público. Cambiar `SITE_URL` aquí actualiza
 * canonical URLs, sitemap, OG image absolute URL y robots.
 *
 * En desarrollo local apunta a localhost; en producción se sobrescribe
 * con la env var `NEXT_PUBLIC_SITE_URL`.
 */

const FALLBACK = "https://datosvivos.co";

export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL ?? FALLBACK
).replace(/\/$/, "");

export const SITE_NAME = "DatosVivos";
export const SITE_TAGLINE = "Datos del Estado, en tus palabras.";
export const SITE_DESCRIPTION =
  "El panorama de los datos abiertos de Colombia: cifras en vivo del catálogo de datos.gov.co, tablero interactivo por sector y entidad, y consultas en lenguaje natural con fuente verificable.";
export const SITE_LOCALE = "es_CO";
