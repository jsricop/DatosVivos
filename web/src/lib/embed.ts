/**
 * Helper para construir la URL del iframe Power BI publish-to-web.
 *
 * Filtra el reporte por el campo `Datasets/entity_abbrev` correspondiente al
 * usuario logueado. **Limitación documentada (ADR-014):** publish-to-web no
 * tiene RLS real — un usuario malicioso puede manipular la URL. Aceptable
 * porque los datos son agregados públicos de `datos.gov.co`.
 */

const BASE = process.env.NEXT_PUBLIC_PBI_EMBED_URL ?? "";

/**
 * Devuelve la URL completa del iframe.
 *
 * - Si no hay `NEXT_PUBLIC_PBI_EMBED_URL`, devuelve string vacío para que
 *   el caller muestre un placeholder ("ANI aún no ha publicado el dashboard").
 * - Si `entityAbbrev` es null, devuelve la URL base sin filtro (el usuario
 *   ve el dashboard global sin scope a su entidad).
 */
export function buildEmbedUrl(entityAbbrev: string | null): string {
  if (!BASE) return "";
  if (!entityAbbrev) return BASE;
  // OData filter syntax soportada por Power BI Service.
  const filter = `Datasets/entity_abbrev eq '${entityAbbrev.replace(/'/g, "''")}'`;
  const separator = BASE.includes("?") ? "&" : "?";
  return `${BASE}${separator}filter=${encodeURIComponent(filter)}`;
}

export function isEmbedConfigured(): boolean {
  return Boolean(BASE);
}
