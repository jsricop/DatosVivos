"use client";

import dynamic from "next/dynamic";

/**
 * Carga diferida del mapa (d3-geo + fetch del GeoJSON solo en el cliente),
 * mismo patrón que BlockRenderer usa para los charts pesados. El placeholder
 * reserva el alto para no saltar el layout.
 */
export const PanoramaMapLazy = dynamic(
  () => import("@/components/panorama/PanoramaMap").then((m) => m.PanoramaMap),
  {
    ssr: false,
    loading: () => (
      <div className="grid place-items-center min-h-[280px] font-mono text-caption text-ink-muted">
        Cargando mapa…
      </div>
    ),
  },
);
