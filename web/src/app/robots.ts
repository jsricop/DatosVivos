import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

/**
 * Reglas de indexación. /api/ y los proxies SSE no deben aparecer en
 * resultados de búsqueda. /buscar tampoco: cada consulta es dinámica y
 * podría producir basura SEO al indexar todas las combinaciones de query.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/buscar", "/_next/"],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
