/**
 * Cliente API hacia FastAPI (api/). Usado por server components y route handlers.
 *
 * Modelo: el frontend Next.js NUNCA habla MCP directamente (ADR-013). Habla
 * HTTP REST + SSE contra `/api/v1/*` expuesto por uvicorn en :8000.
 *
 * Auditoría 2026-05-23: eliminadas `fetchSuggest`, `fetchDivipola*` y
 * `SUGGEST_FALLBACK` por estar huérfanas tras el pivote a chips
 * (`fetchChipsLists`). El endpoint `/api/v1/suggest` queda DEPRECADO en
 * backend; los tests legacy lo siguen verificando como contract test.
 */

import type {
  CatalogStats,
  DatasetMetadata,
  PopularQuery,
  SuggestOption,
} from "@/lib/types";

const BASE = process.env.API_BASE_URL ?? "http://localhost:8000";

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}/api/v1${path}`, {
    ...init,
    headers: { Accept: "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API ${path} → ${res.status}`);
  }
  return (await res.json()) as T;
}

/**
 * Fuente PRIMARIA de chips (Fase 1.1 audit top-down).
 *
 * Devuelve TEMA/TIPO/TERRITORIO/ENTIDAD desde GET /api/v1/chips, cuyo
 * `value` por axis es el formato que espera POST /api/v1/query/chips:
 *   - tema: category literal de Socrata ("Salud y Protección Social")
 *   - tipo: label literal ("Cuántos", "Comparar", ...)
 *   - territorio: código DIVIPOLA ("11", "05") o "macro:caribe" o "nacional"
 *   - entidad: entity_id como string
 *
 * Si el backend no responde, devuelve listas vacías. La UI mostrará los
 * fieldsets sin chips y el botón Buscar quedará deshabilitado.
 */
type ChipsListsResponse = {
  tema: SuggestOption[];
  tipo: SuggestOption[];
  territorio: SuggestOption[];
  entidad: SuggestOption[];
};

const EMPTY_CHIPS: ChipsListsResponse = {
  tema: [],
  tipo: [],
  territorio: [],
  entidad: [],
};

export async function fetchChipsLists(): Promise<ChipsListsResponse> {
  try {
    return await getJson<ChipsListsResponse>("/chips");
  } catch {
    return EMPTY_CHIPS;
  }
}

export async function fetchPopular(limit = 5): Promise<PopularQuery[]> {
  try {
    const data = await getJson<{ popular: PopularQuery[] }>(
      `/popular?limit=${limit}`,
    );
    return data.popular ?? [];
  } catch {
    return [];
  }
}

/**
 * Conteos del catálogo en vivo (total, origen, acceso, calidad) desde
 * GET /api/v1/stats/catalog, que agrega la misma vista que el tablero. Si el
 * backend no responde, devuelve null y la UI degrada a una frase sin cifra dura.
 */
export async function fetchCatalogStats(): Promise<CatalogStats | null> {
  try {
    return await getJson<CatalogStats>("/stats/catalog");
  } catch {
    return null;
  }
}

export async function fetchDatasetMetadata(
  id: string,
): Promise<DatasetMetadata | null> {
  try {
    const data = await getJson<DatasetMetadata>(
      `/datasets/${encodeURIComponent(id)}`,
    );
    return data;
  } catch {
    return null;
  }
}
