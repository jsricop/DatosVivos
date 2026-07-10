/**
 * Config del iframe del tablero Power BI (público, sin login).
 *
 * La URL viene de `PBI_EMBED_URL` en RUNTIME (no `NEXT_PUBLIC_`): el tablero
 * se renderiza server-side en `/tablero` (server component `force-dynamic`),
 * así que la URL aparece en el HTML renderizado en el servidor — no es
 * secreto — y basta REINICIAR el contenedor web para cambiarla, sin rebuild.
 *
 * IMPORTANTE: debe ser una URL de «Publicar en la web»
 * (`https://app.powerbi.com/view?r=…`), que es anónima. Un embed seguro
 * (`reportEmbed?…autoAuth=true&ctid=…`) NO renderiza para visitantes sin
 * sesión del tenant Microsoft y por tanto no sirve en una página pública.
 */

const DEFAULT_HEIGHT = 541;

/** URL del iframe, o "" si no está configurada (el caller muestra placeholder). */
export function getEmbedUrl(): string {
  return (process.env.PBI_EMBED_URL ?? "").trim();
}

/** Alto del iframe en px (`PBI_EMBED_HEIGHT`), con fallback razonable. */
export function getEmbedHeight(): number {
  const raw = Number(process.env.PBI_EMBED_HEIGHT);
  return Number.isFinite(raw) && raw > 0 ? raw : DEFAULT_HEIGHT;
}

export function isEmbedConfigured(): boolean {
  return getEmbedUrl().length > 0;
}
