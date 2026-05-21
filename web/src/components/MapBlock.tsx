"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";

type MapBlockProps = {
  title?: string;
  caption?: string;
  altText?: string;
  /** Lista de marcadores opcionales `[lng, lat, label]` para overlay. */
  markers?: Array<{ lng: number; lat: number; label?: string }>;
  /** Si se proveen, hace fit-bounds. */
  bounds?: [[number, number], [number, number]];
};

/**
 * MapBlock (BRAND.md §8.8) — MapLibre GL JS.
 *
 * Estilo: vector minimal de OSM raster (Carto Voyager para legibilidad).
 * Choropleth y DIVIPOLA quedan para una iteración posterior; en MVP del
 * rebrand mostramos un mapa de Colombia centrado y permite acercar.
 */
export function MapBlock({
  title,
  caption,
  altText,
  markers = [],
  bounds,
}: MapBlockProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    if (mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
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
              "© <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> · © <a href=\"https://carto.com/attributions\">CARTO</a>",
          },
        },
        layers: [{ id: "carto", type: "raster", source: "carto" }],
      },
      center: [-74.08, 4.6],
      zoom: 4.5,
      attributionControl: false,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(
      new maplibregl.AttributionControl({ compact: true }),
      "bottom-left",
    );

    if (bounds) {
      map.fitBounds(bounds, { padding: 24, duration: 0 });
    }
    for (const m of markers) {
      new maplibregl.Marker({ color: "#A52A2A" })
        .setLngLat([m.lng, m.lat])
        .setPopup(m.label ? new maplibregl.Popup().setText(m.label) : undefined)
        .addTo(map);
    }

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [bounds, markers]);

  return (
    <figure
      aria-label={altText ?? caption ?? title ?? "Mapa de Colombia"}
      style={{
        margin: 0,
        border: "1px solid var(--hairline)",
        background: "var(--bg-elev)",
      }}
    >
      {title ? (
        <figcaption
          style={{
            padding: "var(--space-4)",
            fontFamily: "var(--font-serif)",
            fontSize: "var(--type-h4)",
            fontWeight: 600,
            borderBlockEnd: "1px solid var(--hairline)",
          }}
        >
          {title}
        </figcaption>
      ) : null}
      <div ref={containerRef} style={{ width: "100%", height: 360 }} />
      {caption ? (
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
          {caption}
        </p>
      ) : null}
    </figure>
  );
}
