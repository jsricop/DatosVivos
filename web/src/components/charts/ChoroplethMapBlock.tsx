"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import maplibregl from "maplibre-gl";
import { useEffect, useMemo, useRef } from "react";

import { formatValue, type Row } from "@/lib/dashboard-data";
import { dptoCodeFromMpio, lookupDpto } from "@/lib/divipola-centroids";
import type { MapBlock } from "@/lib/schemas/dashboard";

type Props = { block: MapBlock; rows: Row[] };

/**
 * ChoroplethMapBlock (PLAN_DASHBOARD §6).
 *
 * Modo actual (sin GeoJSON cargado): renderiza marcadores graduados en los
 * centroides departamentales. Honesto: no dibuja polígonos que no tiene.
 *
 * Upgrade pendiente: cargar `/geo/co_dptos.geojson` y `/geo/co_mpios.geojson`
 * (instrucciones en `web/public/geo/README.md`) y dibujar fill-color con
 * paint expressions de MapLibre.
 */
export function ChoroplethMapBlock({ block, rows }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  const aggregated = useMemo(() => aggregateByDpto(rows, block), [rows, block]);

  useEffect(() => {
    if (!containerRef.current) return;
    if (mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASE_STYLE,
      center: [-74.08, 4.6],
      zoom: 4.5,
      attributionControl: false,
    });
    map.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "top-right",
    );
    map.addControl(
      new maplibregl.AttributionControl({ compact: true }),
      "bottom-left",
    );
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const localMap: maplibregl.Map = map;

    const markers: maplibregl.Marker[] = [];
    const maxValue = Math.max(0, ...aggregated.map((a) => a.value));

    const setupMarkers = () => {
      for (const entry of aggregated) {
        const dpto = lookupDpto(entry.dptoCode);
        if (!dpto) continue;
        const scaled = maxValue > 0 ? entry.value / maxValue : 0;
        const size = 12 + Math.round(scaled * 36);
        const el = document.createElement("div");
        el.setAttribute(
          "aria-label",
          `${dpto.name}: ${formatValue(entry.value, block.legend_format)}`,
        );
        el.style.width = `${size}px`;
        el.style.height = `${size}px`;
        el.style.borderRadius = "50%";
        el.style.background = "color-mix(in srgb, var(--accent) 75%, transparent)";
        el.style.border = "1.5px solid var(--ink)";
        el.style.boxShadow = "0 0 0 1px var(--bg)";
        const marker = new maplibregl.Marker({ element: el })
          .setLngLat([dpto.lon, dpto.lat])
          .setPopup(
            new maplibregl.Popup({ closeButton: false, offset: 12 }).setHTML(
              `<strong>${dpto.name}</strong><br/>${formatValue(entry.value, block.legend_format)}`,
            ),
          )
          .addTo(localMap);
        markers.push(marker);
      }
    };

    if (localMap.isStyleLoaded()) {
      setupMarkers();
    } else {
      localMap.once("load", () => setupMarkers());
    }

    return () => {
      for (const m of markers) m.remove();
    };
  }, [aggregated, block.legend_format]);

  return (
    <figure
      aria-label={block.title}
      style={{
        margin: 0,
        border: "1px solid var(--hairline)",
        background: "var(--bg-elev)",
      }}
    >
      <figcaption
        className="kicker"
        style={{
          padding: "var(--space-3) var(--space-4)",
          borderBlockEnd: "1px solid var(--hairline)",
        }}
      >
        {block.title}
      </figcaption>
      <div ref={containerRef} style={{ width: "100%", height: 360 }} />
      {aggregated.length === 0 ? (
        <p
          style={{
            margin: 0,
            padding: "var(--space-3) var(--space-4)",
            fontFamily: "var(--font-sans)",
            fontSize: "var(--type-caption)",
            color: "var(--ink-muted)",
            borderBlockStart: "1px solid var(--hairline)",
          }}
        >
          Sin códigos DIVIPOLA reconocidos en los datos.
        </p>
      ) : (
        <p
          style={{
            margin: 0,
            padding: "var(--space-3) var(--space-4)",
            fontFamily: "var(--font-mono)",
            fontSize: "var(--type-caption)",
            color: "var(--ink-2)",
            borderBlockStart: "1px solid var(--hairline)",
          }}
        >
          Mapa por {block.level === "mpio" ? "municipio (agregado al departamento)" : "departamento"} —
          tamaño del marcador proporcional al valor.
        </p>
      )}
    </figure>
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
    if (Number.isNaN(v)) continue;
    acc.set(code, (acc.get(code) ?? 0) + v);
  }
  return Array.from(acc.entries()).map(([dptoCode, value]) => ({ dptoCode, value }));
}

const BASE_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    carto: {
      type: "raster",
      tiles: [
        "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        "https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        "https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
      ],
      tileSize: 256,
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · © <a href="https://carto.com/attributions">CARTO</a>',
    },
  },
  layers: [{ id: "carto", type: "raster", source: "carto" }],
};
