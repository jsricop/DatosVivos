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

  // Cada isla AMPLIADA a su propia celda (patrón del mapa oficial): a
  // escala real las dos islas del inset seguían siendo puntos — están tan
  // separadas entre sí como anchas son (2026-07-13). Celda superior:
  // Providencia + Santa Catalina (contiguas); inferior: San Andrés.
  const INSET = { x: 6, y: 6, w: 92, hTop: 62, hBot: 84, label: 16, pad: 10 };
  const insetCells = useMemo(() => {
    if (!sanAndres || sanAndres.geometry == null) return null;
    const geom = sanAndres.geometry as {
      type: string;
      coordinates: unknown[];
    };
    if (geom.type !== "MultiPolygon" || geom.coordinates.length < 3) {
      return null;
    }
    const polyFeature = (coords: unknown[]) =>
      ({
        type: "Feature",
        properties: sanAndres.properties,
        geometry: { type: "MultiPolygon", coordinates: coords },
      }) as unknown as GeoFeature;
    // poly 0 = San Andrés; polys 1+2 = Providencia y Santa Catalina.
    const providencia = polyFeature(geom.coordinates.slice(1));
    const sanAndresIsla = polyFeature([geom.coordinates[0]]);
    const fitCell = (f: GeoFeature, y0: number, h: number): GeoPath =>
      geoPath(
        geoMercator().fitExtent(
          [
            [INSET.x + INSET.pad, y0 + INSET.pad],
            [INSET.x + INSET.w - INSET.pad, y0 + h - INSET.pad],
          ],
          f as unknown as GeoPermissibleObjects,
        ),
      );
    return [
      { f: providencia, path: fitCell(providencia, INSET.y, INSET.hTop) },
      {
        f: sanAndresIsla,
        path: fitCell(sanAndresIsla, INSET.y + INSET.hTop, INSET.hBot),
      },
    ];
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

      {/* Inset San Andrés y Providencia (cartografía oficial): cada isla
          ampliada a su celda. */}
      {sanAndres && insetCells ? (
        <g>
          <rect
            x={INSET.x}
            y={INSET.y}
            width={INSET.w}
            height={INSET.hTop + INSET.hBot + INSET.label}
            fill="var(--bg)"
            stroke="var(--hairline-strong)"
            strokeWidth={0.75}
          />
          <line
            x1={INSET.x}
            x2={INSET.x + INSET.w}
            y1={INSET.y + INSET.hTop}
            y2={INSET.y + INSET.hTop}
            stroke="var(--hairline)"
            strokeWidth={0.5}
          />
          {insetCells.map((cell, i) =>
            renderPath(cell.f, -2 - i, false, cell.path, [
              INSET.x + INSET.w / 2,
              INSET.y + INSET.hTop + INSET.hBot + INSET.label + 28,
            ]),
          )}
          <text
            x={INSET.x + INSET.w / 2}
            y={INSET.y + INSET.hTop + INSET.hBot + INSET.label - 5}
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
