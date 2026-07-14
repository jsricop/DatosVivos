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

/** Tamaño NATIVO del lienzo del reporte (para el escalado del embed).
 *  Defaults del lienzo estándar 16:9 de Power BI; la barra inferior de
 *  publish-to-web suma ~56px al alto. Ajustable por env sin rebuild. */
export function getReportNativeSize(): { width: number; height: number } {
  const w = Number(process.env.PBI_REPORT_WIDTH);
  const h = Number(process.env.PBI_REPORT_HEIGHT);
  return {
    width: Number.isFinite(w) && w > 0 ? w : 1280,
    height: (Number.isFinite(h) && h > 0 ? h : 720) + 56,
  };
}
