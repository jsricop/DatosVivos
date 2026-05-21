import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

/**
 * Sitemap estático. Incluye solo páginas estables y útiles SEO:
 * - / : landing.
 * - /acerca : manifiesto y equipo (alta importancia institucional).
 * - /accesibilidad : Ley 1618 + WCAG.
 *
 * /buscar y /dataset/[id] quedan fuera por ser dinámicas y de poco valor
 * de descubrimiento — cada uno se sirve bajo demanda.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  return [
    {
      url: `${SITE_URL}/`,
      lastModified,
      changeFrequency: "weekly",
      priority: 1.0,
    },
    {
      url: `${SITE_URL}/acerca`,
      lastModified,
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      url: `${SITE_URL}/accesibilidad`,
      lastModified,
      changeFrequency: "monthly",
      priority: 0.5,
    },
  ];
}
