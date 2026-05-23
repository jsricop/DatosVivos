/**
 * Cliente API hacia FastAPI (api/). Usado por server components y route handlers.
 *
 * Modelo: el frontend Next.js NUNCA habla MCP directamente (ADR-013). Habla
 * HTTP REST + SSE contra `/api/v1/*` expuesto por uvicorn en :8000.
 */

import type {
  DatasetMetadata,
  DivipolaItem,
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

export async function fetchSuggest(axis: string): Promise<SuggestOption[]> {
  try {
    const data = await getJson<{ options: SuggestOption[] }>(
      `/suggest?axis=${encodeURIComponent(axis)}`,
    );
    return data.options ?? [];
  } catch {
    return SUGGEST_FALLBACK[axis] ?? [];
  }
}

/**
 * Nueva fuente PRIMARIA de chips (Fase 1.1 audit top-down).
 *
 * Devuelve TEMA/TIPO/TERRITORIO/ENTIDAD desde GET /api/v1/chips, cuyo
 * `value` por axis es el formato que espera POST /api/v1/query/chips:
 *   - tema: category literal de Socrata ("Salud y Protección Social")
 *   - tipo: label literal ("Cuántos", "Comparar", ...)
 *   - territorio: código DIVIPOLA ("11", "05") o "macro:caribe" o "nacional"
 *   - entidad: entity_id como string
 *
 * Si falla, cae a los fallbacks legacy (slugs como "salud"/"count") que
 * NO van a funcionar contra el endpoint chips. En ese caso la UI muestra
 * los chips pero el botón Buscar devolverá 422 — comportamiento esperado
 * cuando el backend está caído.
 */
type ChipsListsResponse = {
  tema: SuggestOption[];
  tipo: SuggestOption[];
  territorio: SuggestOption[];
  entidad: SuggestOption[];
};

export async function fetchChipsLists(): Promise<ChipsListsResponse> {
  try {
    return await getJson<ChipsListsResponse>("/chips");
  } catch {
    return {
      tema: SUGGEST_FALLBACK.tema ?? [],
      tipo: SUGGEST_FALLBACK.tipo ?? [],
      territorio: SUGGEST_FALLBACK.territorio ?? [],
      entidad: SUGGEST_FALLBACK.entidad ?? [],
    };
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

export async function fetchDivipolaDepartments(): Promise<DivipolaItem[]> {
  try {
    const data = await getJson<{ departments: DivipolaItem[] }>("/divipola");
    return data.departments ?? [];
  } catch {
    return [];
  }
}

export async function fetchDivipolaMunicipios(
  dptoCode: string,
): Promise<DivipolaItem[]> {
  try {
    const data = await getJson<{ municipios: DivipolaItem[] }>(
      `/divipola?dpto=${encodeURIComponent(dptoCode)}`,
    );
    return data.municipios ?? [];
  } catch {
    return [];
  }
}

export async function fetchDatasetMetadata(
  id: string,
): Promise<DatasetMetadata | null> {
  try {
    const data = await getJson<DatasetMetadata>(`/datasets/${encodeURIComponent(id)}`);
    return data;
  } catch {
    return null;
  }
}

/**
 * Fallback estático si la API no responde (red caída, dev sin backend).
 * Garantiza que el sitio nunca se ve vacío. Los chips son los del MVP del plan.
 */
const SUGGEST_FALLBACK: Record<string, SuggestOption[]> = {
  tema: [
    { value: "salud", label: "Salud" },
    { value: "educacion", label: "Educación" },
    { value: "seguridad", label: "Seguridad" },
    { value: "movilidad", label: "Movilidad" },
    { value: "justicia", label: "Justicia" },
    { value: "economia", label: "Economía" },
    { value: "medio-ambiente", label: "Medio Ambiente" },
    { value: "vivienda", label: "Vivienda" },
    { value: "trabajo", label: "Trabajo" },
  ],
  tipo: [
    { value: "count", label: "Cuántos" },
    { value: "compare", label: "Comparar" },
    { value: "ranking", label: "Ranking" },
    { value: "trend", label: "Tendencia" },
    { value: "map", label: "Mapa" },
  ],
  territorio: [
    { value: "nacional", label: "Nacional" },
  ],
  entidad: [
    { value: "minsalud", label: "MinSalud" },
    { value: "mineducacion", label: "MinEducación" },
    { value: "policia", label: "Policía Nacional" },
    { value: "dane", label: "DANE" },
    { value: "dnp", label: "DNP" },
    { value: "ani", label: "ANI" },
  ],
};
