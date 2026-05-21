"use client";

import {
  geoMercator,
  geoPath,
  type GeoPath,
  type GeoPermissibleObjects,
} from "d3-geo";
import { useEffect, useMemo, useRef, useState } from "react";

import { useUserScale } from "@/lib/motion";
import { formatValue, type Row } from "@/lib/dashboard-data";
import type { MapBlock } from "@/lib/schemas/dashboard";

type Props = { block: MapBlock; rows: Row[] };

type GeoFeature = {
  type: "Feature";
  properties: {
    DPTO?: string;
    MPIO?: string;
    NOMBRE_DPT?: string;
    NOMBRE_MPI?: string;
    [k: string]: unknown;
  };
  geometry: GeoPermissibleObjects;
};

type FeatureCollection = {
  type: "FeatureCollection";
  features: GeoFeature[];
};

const BASE_WIDTH = 560;
const BASE_HEIGHT = 480;
const GEOJSON_URLS = {
  dpto: "/geo/co_dptos.geojson",
  mpio: "/geo/co_mpios.geojson",
} as const;

/**
 * ChoroplethMapBlock — silueta de Colombia + choropleth secuencial monocromo.
 *
 * Sin tiles externos: el render es SVG puro sobre GeoJSON DIVIPOLA cargado
 * desde `web/public/geo/co_dptos.geojson` (33 features, ~1.4 MB) o
 * `co_mpios.geojson` (1122 features, ~770 KB simplificado al 10% con
 * `topojson-simplify`). Cumple la promesa "Sin trackers" del footer y la
 * regla del BRAND.md §6.5 (sin dependencia externa de mapas).
 *
 * Choropleth: 5 buckets por cuantiles. Cada bucket = una opacidad creciente
 * sobre `var(--accent)` (paleta secuencial monocroma BRAND.md §8.9).
 *
 * Soporta `block.level = "dpto" | "mpio"`. El geojson se carga lazy via fetch
 * dentro de useEffect — el dynamic import del componente entero ya hace que
 * todo el bundle de Visx + d3-geo solo se descargue cuando hay choropleth
 * en el dashboard.
 */
export function ChoroplethMapBlock({ block, rows }: Props) {
  const [geo, setGeo] = useState<FeatureCollection | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const userScale = useUserScale();
  const height = Math.round(BASE_HEIGHT * userScale);

  useEffect(() => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setGeo(null);
    setLoadError(null);
    const url = GEOJSON_URLS[block.level];
    fetch(url, { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error(`Geojson HTTP ${r.status}`);
        return r.json() as Promise<FeatureCollection>;
      })
      .then((data) => setGeo(data))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setLoadError(err instanceof Error ? err.message : "Error cargando mapa");
      });
    return () => controller.abort();
  }, [block.level]);

  const aggregated = useMemo(() => aggregateByCode(rows, block), [rows, block]);
  const buckets = useMemo(
    () => computeBuckets(aggregated.map((a) => a.value)),
    [aggregated],
  );
  const valueByCode = useMemo(
    () => new Map(aggregated.map((a) => [a.code, a.value] as const)),
    [aggregated],
  );

  if (loadError) {
    return (
      <figure aria-label={block.title} className="surface-elev m-0">
        <figcaption className="text-kicker px-4 py-3 hairline-bottom">
          {block.title}
        </figcaption>
        <p className="m-0 px-4 py-6 font-sans text-body-sm text-ink-muted">
          Mapa no disponible — consulta los datos en la tabla cruda.
        </p>
      </figure>
    );
  }

  return (
    <figure aria-label={block.title} className="surface-elev m-0">
      <figcaption className="text-kicker px-4 py-3 hairline-bottom flex items-baseline justify-between">
        <span>{block.title}</span>
        <span className="text-ink-muted">
          {block.level === "mpio"
            ? "Agregado al departamento"
            : "Por departamento"}
        </span>
      </figcaption>
      <div style={{ width: "100%", aspectRatio: `${BASE_WIDTH} / ${height}` }}>
        {geo ? (
          <ChoroplethSVG
            geo={geo}
            level={block.level}
            valueByCode={valueByCode}
            buckets={buckets}
            title={block.title}
            legendFormat={block.legend_format}
          />
        ) : (
          <div className="h-full grid place-items-center font-mono text-caption text-ink-muted">
            Cargando mapa…
          </div>
        )}
      </div>
      <ChoroplethLegend buckets={buckets} legendFormat={block.legend_format} />
    </figure>
  );
}

// ---- subcomponentes / helpers -----------------------------------------

function ChoroplethSVG({
  geo,
  level,
  valueByCode,
  buckets,
  title,
  legendFormat,
}: {
  geo: FeatureCollection;
  level: MapBlock["level"];
  valueByCode: Map<string, number>;
  buckets: number[];
  title: string;
  legendFormat: MapBlock["legend_format"];
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
      aria-label={title}
      preserveAspectRatio="xMidYMid meet"
      className="w-full h-full"
    >
      {geo.features.map((feature, i) => {
        const code = featureCode(feature, level);
        const rawName = featureName(feature, level) || code;
        const name = toTitleCase(rawName);
        const value = valueByCode.get(code);
        const idx = value !== undefined ? bucketIndex(value, buckets) : -1;
        const fill =
          idx < 0
            ? "var(--bg-elev)"
            : `color-mix(in srgb, var(--accent) ${15 + idx * 20}%, var(--bg))`;
        const d = path(feature as unknown as GeoPermissibleObjects) ?? "";
        return (
          <path
            key={`${code}-${i}`}
            d={d}
            fill={fill}
            stroke="var(--ink)"
            strokeWidth={level === "mpio" ? 0.25 : 0.5}
            strokeLinejoin="miter"
          >
            <title>
              {name}
              {value !== undefined
                ? `: ${formatValue(value, legendFormat)}`
                : " — sin datos"}
            </title>
          </path>
        );
      })}
    </svg>
  );
}

function ChoroplethLegend({
  buckets,
  legendFormat,
}: {
  buckets: number[];
  legendFormat: MapBlock["legend_format"];
}) {
  if (buckets.length === 0) {
    return (
      <p className="m-0 px-4 py-3 font-mono text-caption text-ink-muted hairline-top">
        Sin códigos DIVIPOLA reconocidos en los datos.
      </p>
    );
  }
  return (
    <div className="px-4 py-3 hairline-top flex flex-wrap items-center gap-x-4 gap-y-2">
      <span className="text-kicker">Leyenda</span>
      {buckets.map((max, i) => {
        const min = i === 0 ? 0 : (buckets[i - 1] ?? 0);
        return (
          <span
            key={i}
            className="inline-flex items-center gap-1.5 font-mono text-caption text-ink-2"
          >
            <span
              aria-hidden
              className="inline-block w-3 h-3"
              style={{
                background: `color-mix(in srgb, var(--accent) ${15 + i * 20}%, var(--bg))`,
                border: "1px solid var(--ink)",
              }}
            />
            <span className="[font-variant-numeric:tabular-nums]">
              {formatValue(min, legendFormat)} – {formatValue(max, legendFormat)}
            </span>
          </span>
        );
      })}
    </div>
  );
}

function aggregateByCode(
  rows: Row[],
  block: MapBlock,
): Array<{ code: string; value: number }> {
  const padTo = block.level === "mpio" ? 5 : 2;
  const acc = new Map<string, number>();
  for (const r of rows) {
    const rawCode = r[block.code_column];
    if (rawCode === null || rawCode === undefined) continue;
    const code = String(rawCode).padStart(padTo, "0");
    if (!code) continue;
    const v = Number(r[block.metric_column] ?? 0);
    if (!Number.isFinite(v)) continue;
    acc.set(code, (acc.get(code) ?? 0) + v);
  }
  return Array.from(acc.entries()).map(([code, value]) => ({ code, value }));
}

function featureCode(feature: GeoFeature, level: MapBlock["level"]): string {
  if (level === "mpio") {
    const m = feature.properties?.MPIO;
    if (m) return String(m).padStart(5, "0");
  }
  const d = feature.properties?.DPTO;
  return String(d ?? "").padStart(2, "0");
}

function featureName(feature: GeoFeature, level: MapBlock["level"]): string {
  if (level === "mpio") {
    const n = feature.properties?.NOMBRE_MPI;
    if (typeof n === "string") return n;
  }
  const n = feature.properties?.NOMBRE_DPT;
  return typeof n === "string" ? n : "";
}

/** Devuelve los 5 umbrales de cuantil (q20, q40, q60, q80, max). */
function computeBuckets(values: number[]): number[] {
  if (values.length === 0) return [];
  const sorted = [...values].sort((a, b) => a - b);
  const quantiles = [0.2, 0.4, 0.6, 0.8, 1];
  return quantiles.map((q) => {
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

function toTitleCase(s: string): string {
  return s
    .toLowerCase()
    .split(" ")
    .map((w) => (w.length === 0 ? w : (w[0] ?? "").toUpperCase() + w.slice(1)))
    .join(" ");
}
