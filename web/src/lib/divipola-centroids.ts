/**
 * Centroides aproximados de los 33 departamentos colombianos.
 * Usado por ChoroplethMapBlock cuando aún no hay GeoJSON cargado (degraded mode).
 * Coordenadas: lat / lon de la capital o centro geográfico aproximado.
 */

export type DptoCentroid = {
  code: string;
  name: string;
  lat: number;
  lon: number;
};

export const DPTO_CENTROIDS: Record<string, DptoCentroid> = {
  "05": { code: "05", name: "Antioquia", lat: 6.25, lon: -75.57 },
  "08": { code: "08", name: "Atlántico", lat: 10.96, lon: -74.78 },
  "11": { code: "11", name: "Bogotá D.C.", lat: 4.71, lon: -74.07 },
  "13": { code: "13", name: "Bolívar", lat: 9.0, lon: -75.0 },
  "15": { code: "15", name: "Boyacá", lat: 5.55, lon: -73.36 },
  "17": { code: "17", name: "Caldas", lat: 5.07, lon: -75.52 },
  "18": { code: "18", name: "Caquetá", lat: 1.6, lon: -75.6 },
  "19": { code: "19", name: "Cauca", lat: 2.45, lon: -76.62 },
  "20": { code: "20", name: "Cesar", lat: 10.46, lon: -73.25 },
  "23": { code: "23", name: "Córdoba", lat: 8.75, lon: -75.88 },
  "25": { code: "25", name: "Cundinamarca", lat: 5.0, lon: -74.0 },
  "27": { code: "27", name: "Chocó", lat: 6.2, lon: -77.0 },
  "41": { code: "41", name: "Huila", lat: 2.93, lon: -75.28 },
  "44": { code: "44", name: "La Guajira", lat: 11.55, lon: -72.95 },
  "47": { code: "47", name: "Magdalena", lat: 10.4, lon: -74.2 },
  "50": { code: "50", name: "Meta", lat: 3.5, lon: -73.0 },
  "52": { code: "52", name: "Nariño", lat: 1.2, lon: -77.28 },
  "54": { code: "54", name: "Norte de Santander", lat: 7.9, lon: -72.5 },
  "63": { code: "63", name: "Quindío", lat: 4.53, lon: -75.68 },
  "66": { code: "66", name: "Risaralda", lat: 4.81, lon: -75.7 },
  "68": { code: "68", name: "Santander", lat: 7.13, lon: -73.13 },
  "70": { code: "70", name: "Sucre", lat: 9.3, lon: -75.4 },
  "73": { code: "73", name: "Tolima", lat: 4.43, lon: -75.23 },
  "76": { code: "76", name: "Valle del Cauca", lat: 3.45, lon: -76.53 },
  "81": { code: "81", name: "Arauca", lat: 7.08, lon: -70.76 },
  "85": { code: "85", name: "Casanare", lat: 5.34, lon: -72.39 },
  "86": { code: "86", name: "Putumayo", lat: 0.43, lon: -76.53 },
  "88": { code: "88", name: "San Andrés y Providencia", lat: 12.58, lon: -81.71 },
  "91": { code: "91", name: "Amazonas", lat: -1.5, lon: -71.5 },
  "94": { code: "94", name: "Guainía", lat: 2.58, lon: -68.51 },
  "95": { code: "95", name: "Guaviare", lat: 2.57, lon: -72.64 },
  "97": { code: "97", name: "Vaupés", lat: 0.85, lon: -70.81 },
  "99": { code: "99", name: "Vichada", lat: 4.45, lon: -69.28 },
};

export function lookupDpto(code: string): DptoCentroid | undefined {
  // Soporta tanto "05" como "5".
  const padded = code.padStart(2, "0");
  return DPTO_CENTROIDS[padded];
}

export function dptoCodeFromMpio(mpioCode: string): string | undefined {
  if (!mpioCode || mpioCode.length < 2) return undefined;
  return mpioCode.padStart(5, "0").slice(0, 2);
}
