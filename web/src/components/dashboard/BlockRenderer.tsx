"use client";

import dynamic from "next/dynamic";

import { KPICardBlock } from "@/components/charts/KPICardBlock";
import { TableBlock } from "@/components/charts/TableBlock";
import type { Row } from "@/lib/dashboard-data";
import type { Block } from "@/lib/schemas/dashboard";

/**
 * Charts pesados (`@visx/*` + `d3-geo`) cargan lazy desde el navegador.
 * KPI y Table son livianos (sin Visx) y se renderizan en server side.
 */

const BarChartBlock = dynamic(
  () =>
    import("@/components/charts/BarChartBlock").then(
      (mod) => mod.BarChartBlock,
    ),
  { ssr: false, loading: () => <ChartPlaceholder /> },
);

const LineChartBlock = dynamic(
  () =>
    import("@/components/charts/LineChartBlock").then(
      (mod) => mod.LineChartBlock,
    ),
  { ssr: false, loading: () => <ChartPlaceholder /> },
);

const ChoroplethMapBlock = dynamic(
  () =>
    import("@/components/charts/ChoroplethMapBlock").then(
      (mod) => mod.ChoroplethMapBlock,
    ),
  { ssr: false, loading: () => <MapPlaceholder /> },
);

type Props = {
  block: Block;
  rows: Row[];
  stats: Record<string, unknown> | null;
};

export function BlockRenderer({ block, rows, stats }: Props) {
  switch (block.type) {
    case "kpi":
      return <KPICardBlock block={block} rows={rows} stats={stats} />;
    case "bar":
    case "scatter":
    case "pie":
    case "donut":
      return <BarChartBlock block={block} rows={rows} />;
    case "line":
    case "area":
      return <LineChartBlock block={block} rows={rows} />;
    case "choropleth":
      return <ChoroplethMapBlock block={block} rows={rows} />;
    case "table":
      return <TableBlock block={block} rows={rows} />;
    default:
      return null;
  }
}

function ChartPlaceholder() {
  return (
    <div className="surface-elev p-6 text-center font-mono text-caption text-ink-muted">
      Cargando gráfico…
    </div>
  );
}

function MapPlaceholder() {
  return (
    <div className="surface-elev p-6 text-center font-mono text-caption text-ink-muted">
      Cargando mapa…
    </div>
  );
}
