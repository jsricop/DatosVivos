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
import { dptoCodeFromMpio } from "@/lib/divipola-centroids";
import type { MapBlock } from "@/lib/schemas/dashboard";

type Props = { block: MapBlock; rows: Row[] };

type DptoFeature = {
  type: "Feature";
  properties: { DPTO?: string; NOMBRE_DPT?: string; [k: string]: unknown };
  geometry: GeoPermissibleObjects;
};

type FeatureCollection = {
  type: "FeatureCollection";
  features: DptoFeature[];
};

const BASE_WIDTH = 560;
const BASE_HEIGHT = 480;
const GEOJSON_URL = "/geo/co_dptos.geojson";

/**
 * ChoroplethMapBlock — silueta de Colombia + choropleth secuencial monocromo.
 *
 * Sin tiles externos: el render es SVG puro sobre GeoJSON DIVIPOLA cargado
 * desde `web/public/geo/co_dptos.geojson`. Cumple la promesa "Sin trackers"
 * del footer y la regla del BRAND.md §6.5 (sin dependencia externa de mapas).
 *
 * Choropleth: 5 buckets por cuantiles. Cada bucket = una opacidad creciente
 * sobre `var(--accent)` (paleta secuencial monocroma BRAND.md §8.9).
 *
 * Soporta `block.level = "dpto" | "mpio"`. Para `mpio` agrupamos al
 * departamento que pertenece (el GeoJSON de 1122 mpios queda pendiente).
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
    fetch(GEOJSON_URL, { signal: controller.signal })
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
  }, []);

  const aggregated = useMemo(() => aggregateByDpto(rows, block), [rows, block]);
  const buckets = useMemo(
    () => computeBuckets(aggregated.map((a) => a.value)),
    [aggregated],
  );
  const valueByDpto = useMemo(
    () => new Map(aggregated.map((a) => [a.dptoCode, a.value] as const)),
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
            valueByDpto={valueByDpto}
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
  valueByDpto,
  buckets,
  title,
  legendFormat,
}: {
  geo: FeatureCollection;
  valueByDpto: Map<string, number>;
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
      {geo.features.map((feature) => {
        const dptoCode = String(feature.properties?.DPTO ?? "").padStart(2, "0");
        const rawName =
          typeof feature.properties?.NOMBRE_DPT === "string"
            ? feature.properties.NOMBRE_DPT
            : dptoCode;
        const name = toTitleCase(rawName);
        const value = valueByDpto.get(dptoCode);
        const idx = value !== undefined ? bucketIndex(value, buckets) : -1;
        const fill =
          idx < 0
            ? "var(--bg-elev)"
            : `color-mix(in srgb, var(--accent) ${15 + idx * 20}%, var(--bg))`;
        const d = path(feature as unknown as GeoPermissibleObjects) ?? "";
        return (
          <path
            key={dptoCode}
            d={d}
            fill={fill}
            stroke="var(--ink)"
            strokeWidth={0.5}
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

function aggregateByDpto(
  rows: Row[],
  block: MapBlock,
): Array<{ dptoCode: string; value: number }> {
  const acc = new Map<string, number>();
  for (const r of rows) {
    const rawCode = r[block.code_column];
    if (rawCode === null || rawCode === undefined) continue;
    const code =
      block.level === "mpio"
        ? dptoCodeFromMpio(String(rawCode))
        : String(rawCode).padStart(2, "0");
    if (!code) continue;
    const v = Number(r[block.metric_column] ?? 0);
    if (!Number.isFinite(v)) continue;
    acc.set(code, (acc.get(code) ?? 0) + v);
  }
  return Array.from(acc.entries()).map(([dptoCode, value]) => ({
    dptoCode,
    value,
  }));
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
