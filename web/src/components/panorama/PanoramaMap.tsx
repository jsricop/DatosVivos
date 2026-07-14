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
 * Fade-in del SVG al entrar al viewport (.reveal-fade). El top-10 en lista
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
  const top10 = departamentos.slice(0, 10);

  return (
    <div ref={ref} className="grid gap-6 md:grid-cols-[5fr_2fr] items-center">
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
        <span className="text-kicker">Top 10 departamentos</span>
        <ol className="list-none m-0 p-0 flex flex-col gap-1.5">
          {top10.map((d, i) => (
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
  // San Andrés y Providencia ('88') está a ~700 km del continente: si el
  // fitSize los incluye, el continente se encoge y deja una franja vacía a
  // la izquierda (2026-07-13). Encuadre al continente + INSET para las
  // islas, como en la cartografía oficial del DANE.
  const continente = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: geo.features.filter(
        (f) => String(f.properties?.DPTO ?? "").padStart(2, "0") !== "88",
      ),
    }),
    [geo],
  );
  const sanAndres = useMemo(
    () =>
      geo.features.find(
        (f) => String(f.properties?.DPTO ?? "").padStart(2, "0") === "88",
      ) ?? null,
    [geo],
  );
  const projection = useMemo(
    () =>
      geoMercator().fitSize(
        [BASE_WIDTH, BASE_HEIGHT],
        continente as unknown as GeoPermissibleObjects,
      ),
    [continente],
  );
  const path: GeoPath = useMemo(() => geoPath(projection), [projection]);

  const INSET = { x: 6, y: 6, w: 88, h: 88, pad: 12 };
  const insetPath: GeoPath | null = useMemo(() => {
    if (!sanAndres) return null;
    const proj = geoMercator().fitExtent(
      [
        [INSET.x + INSET.pad, INSET.y + INSET.pad],
        [INSET.x + INSET.w - INSET.pad, INSET.y + INSET.h - INSET.pad],
      ],
      sanAndres as unknown as GeoPermissibleObjects,
    );
    return geoPath(proj);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sanAndres]);
  // Departamento bajo el cursor: crece un poco (feedback vivo) y muestra
  // su cifra en un tooltip propio — el <title> nativo tardaba (2026-07-13).
  const [hover, setHover] = useState<{
    code: string;
    name: string;
    value: number | undefined;
    x: number;
    y: number;
  } | null>(null);

  const renderPath = (
    feature: GeoFeature,
    i: number,
    elevated: boolean,
    pathFn: GeoPath = path,
    tooltipXY?: [number, number],
  ) => {
    const code = String(feature.properties?.DPTO ?? "").padStart(2, "0");
    const name = String(feature.properties?.NOMBRE_DPT ?? code);
    const value = valueByCode.get(code);
    const idx = value !== undefined ? bucketIndex(value, buckets) : -1;
    const fill =
      idx < 0
        ? "var(--bg-elev)"
        : `color-mix(in srgb, var(--accent) ${15 + idx * 20}%, var(--bg))`;
    const isHovered = hover?.code === code;
    return (
      <path
        key={`${elevated ? "top-" : ""}${code}-${i}`}
        d={pathFn(feature as unknown as GeoPermissibleObjects) ?? ""}
        fill={fill}
        stroke="var(--ink)"
        strokeWidth={isHovered ? 1.2 : 0.5}
        strokeLinejoin="miter"
        style={{
          transform: isHovered ? "scale(1.05)" : "scale(1)",
          transformOrigin: "center",
          transformBox: "fill-box",
          transition: "transform 160ms ease-out",
          cursor: value !== undefined ? "pointer" : "default",
        }}
        onMouseEnter={() => {
          const [cx, cy] =
            tooltipXY ??
            pathFn.centroid(feature as unknown as GeoPermissibleObjects);
          setHover({ code, name, value, x: cx, y: cy });
        }}
        onMouseLeave={() => setHover(null)}
      />
    );
  };

  const hoveredFeature = hover
    ? geo.features.find(
        (f) =>
          String(f.properties?.DPTO ?? "").padStart(2, "0") === hover.code,
      )
    : null;

  return (
    <svg
      viewBox={`0 0 ${BASE_WIDTH} ${BASE_HEIGHT}`}
      role="img"
      aria-label="Mapa de Colombia: datasets por departamento"
      preserveAspectRatio="xMidYMid meet"
      className="w-full h-full"
    >
      {continente.features.map((f, i) => renderPath(f, i, false))}
      {/* El departamento activo se re-dibuja ENCIMA: al crecer no queda
          tapado por los bordes de sus vecinos. */}
      {hoveredFeature && hover?.code !== "88"
        ? renderPath(hoveredFeature, -1, true)
        : null}

      {/* Inset San Andrés y Providencia (cartografía DANE). */}
      {sanAndres && insetPath ? (
        <g>
          <rect
            x={INSET.x}
            y={INSET.y}
            width={INSET.w}
            height={INSET.h}
            fill="var(--bg)"
            stroke="var(--hairline-strong)"
            strokeWidth={0.75}
          />
          {renderPath(sanAndres, -2, false, insetPath, [
            INSET.x + INSET.w / 2,
            INSET.y + INSET.h + 30,
          ])}
          <text
            x={INSET.x + INSET.w / 2}
            y={INSET.y + INSET.h - 5}
            textAnchor="middle"
            fontFamily="var(--font-mono)"
            fontSize={8}
            fill="var(--ink-muted)"
          >
            San Andrés y Prov.
          </text>
        </g>
      ) : null}
      {hover ? (
        (() => {
          const texto =
            hover.value !== undefined
              ? `${hover.name}: ${fmt(hover.value)} datasets`
              : `${hover.name} — sin datos`;
          const tw = texto.length * 6.6 + 14;
          const tx = Math.min(Math.max(hover.x - tw / 2, 2), BASE_WIDTH - tw - 2);
          const ty = Math.max(hover.y - 36, 2);
          return (
            <g pointerEvents="none" transform={`translate(${tx}, ${ty})`}>
              <rect width={tw} height={22} rx={3} fill="var(--ink)" opacity="0.92" />
              <text
                x={tw / 2}
                y={15}
                textAnchor="middle"
                fontFamily="var(--font-mono)"
                fontSize={11}
                fill="var(--bg)"
              >
                {texto}
              </text>
            </g>
          );
        })()
      ) : null}
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
