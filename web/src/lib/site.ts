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
  "Agente civil de datos abiertos del Estado colombiano. Pregunta en lenguaje natural sobre cualquier dato público y recibe la respuesta con la fuente original a un click.";
export const SITE_LOCALE = "es_CO";
