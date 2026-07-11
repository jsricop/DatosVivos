"use client";

import {
  geoMercator,
  geoPath,
  type GeoPath,
  type GeoPermissibleObjects,
} from "d3-geo";
import { useEffect, useMemo, useRef, useState } from "react";

import { useRevealOnce } from "@/components/panorama/useRevealOnce";
import type { DeptCount } from "@/lib/types";

type GeoFeature = {
  type: "Feature";
  properties: { DPTO?: string; NOMBRE_DPT?: string; [k: string]: unknown };
  geometry: GeoPermissibleObjects;
};
type FeatureCollection = { type: "FeatureCollection"; features: GeoFeature[] };

const BASE_WIDTH = 460;
const BASE_HEIGHT = 420;
const GEOJSON_URL = "/geo/co_dptos.geojson";

const fmt = (n: number) => n.toLocaleString("es-CO");

/**
 * Coropleta nacional por departamento para la home panorama (ADR-023).
 *
 * Variante propia — NO reutiliza ChoroplethMapBlock (ese está acoplado a
 * DashboardSpec y a la regla "sin animación en resultados"). Comparte el
 * mismo GeoJSON DIVIPOLA local (`/geo/co_dptos.geojson`) y la técnica de
 * buckets por cuantiles con opacidad creciente sobre --accent.
 *
 * Fade-in del SVG al entrar al viewport (.reveal-fade). El top-5 en lista
 * al lado es la lectura accesible primaria; el mapa es refuerzo visual.
 */
export function PanoramaMap({
  departamentos,
  nacionalSinGeo,
}: {
  departamentos: DeptCount[];
  nacionalSinGeo: number;
}) {
  const [geo, setGeo] = useState<FeatureCollection | null>(null);
  const [loadError, setLoadError] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const { ref, revealed } = useRevealOnce<HTMLDivElement>();

  useEffect(() => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    fetch(GEOJSON_URL, { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error(`Geojson HTTP ${r.status}`);
        return r.json() as Promise<FeatureCollection>;
      })
      .then(setGeo)
      .catch(() => {
        if (!controller.signal.aborted) setLoadError(true);
      });
    return () => controller.abort();
  }, []);

  const valueByCode = useMemo(
    () => new Map(departamentos.map((d) => [d.codigo, d.n_datasets] as const)),
    [departamentos],
  );
  const buckets = useMemo(
    () => computeBuckets(departamentos.map((d) => d.n_datasets)),
    [departamentos],
  );
  const top5 = departamentos.slice(0, 5);

  return (
    <div ref={ref} className="grid gap-4 md:grid-cols-[3fr_2fr] items-start">
      <div
        className={`reveal-fade${revealed ? "" : " is-pending"}`}
        style={{ aspectRatio: `${BASE_WIDTH} / ${BASE_HEIGHT}` }}
      >
        {loadError ? (
          <p className="m-0 font-sans text-body-sm text-ink-muted">
            Mapa no disponible — el ranking de departamentos está al lado.
          </p>
        ) : geo ? (
          <MapSVG geo={geo} valueByCode={valueByCode} buckets={buckets} />
        ) : (
          <div className="h-full grid place-items-center font-mono text-caption text-ink-muted">
            Cargando mapa…
          </div>
        )}
      </div>
      <div className="flex flex-col gap-2">
        <span className="text-kicker">Top 5 departamentos</span>
        <ol className="list-none m-0 p-0 flex flex-col gap-1.5">
          {top5.map((d, i) => (
            <li
              key={d.codigo}
              className="grid grid-cols-[2ch_1fr_auto] gap-2 items-baseline font-sans text-body-sm text-ink-2"
            >
              <span className="font-mono text-caption text-accent [font-variant-numeric:tabular-nums]">
                {i + 1}
              </span>
              <span className="truncate" title={d.nombre}>
                {d.nombre}
              </span>
              <span className="font-mono text-caption [font-variant-numeric:tabular-nums]">
                {fmt(d.n_datasets)}
              </span>
            </li>
          ))}
        </ol>
        <p className="m-0 mt-1 font-sans text-caption text-ink-muted leading-relaxed">
          El mapa muestra los datasets asociados a un departamento o municipio.
          Otros {fmt(nacionalSinGeo)} aplican a todo el país o no declaran
          territorio.
        </p>
      </div>
    </div>
  );
}

function MapSVG({
  geo,
  valueByCode,
  buckets,
}: {
  geo: FeatureCollection;
  valueByCode: Map<string, number>;
  buckets: number[];
}) {
  const projection = useMemo(
    () =>
      geoMercator().fitSize(
        [BASE_WIDTH, BASE_HEIGHT],
        geo as unknown as GeoPermissibleObjects,
      ),
    [geo],
  );
  const path: GeoPath = useMemo(() => geoPath(projection), [projection]);

  return (
    <svg
      viewBox={`0 0 ${BASE_WIDTH} ${BASE_HEIGHT}`}
      role="img"
      aria-label="Mapa de Colombia: datasets por departamento"
      preserveAspectRatio="xMidYMid meet"
      className="w-full h-full"
    >
      {geo.features.map((feature, i) => {
        const code = String(feature.properties?.DPTO ?? "").padStart(2, "0");
        const name = feature.properties?.NOMBRE_DPT ?? code;
        const value = valueByCode.get(code);
        const idx = value !== undefined ? bucketIndex(value, buckets) : -1;
        const fill =
          idx < 0
            ? "var(--bg-elev)"
            : `color-mix(in srgb, var(--accent) ${15 + idx * 20}%, var(--bg))`;
        return (
          <path
            key={`${code}-${i}`}
            d={path(feature as unknown as GeoPermissibleObjects) ?? ""}
            fill={fill}
            stroke="var(--ink)"
            strokeWidth={0.5}
            strokeLinejoin="miter"
          >
            <title>
              {String(name)}
              {value !== undefined ? `: ${fmt(value)} datasets` : " — sin datos"}
            </title>
          </path>
        );
      })}
    </svg>
  );
}

/** Umbrales de cuantil (misma técnica que ChoroplethMapBlock). */
function computeBuckets(values: number[]): number[] {
  if (values.length === 0) return [];
  const sorted = [...values].sort((a, b) => a - b);
  return [0.2, 0.4, 0.6, 0.8, 1].map((q) => {
    const idx = Math.min(sorted.length - 1, Math.floor(q * sorted.length));
    return sorted[idx] ?? 0;
  });
}

function bucketIndex(value: number, buckets: number[]): number {
  for (let i = 0; i < buckets.length; i++) {
    if (value <= (buckets[i] ?? 0)) return i;
  }
  return buckets.length - 1;
}
