"use client";

import dynamic from "next/dynamic";

import { BarChartBlock } from "@/components/charts/BarChartBlock";
import { KPICardBlock } from "@/components/charts/KPICardBlock";
import { LineChartBlock } from "@/components/charts/LineChartBlock";
import { TableBlock } from "@/components/charts/TableBlock";
import type { Row } from "@/lib/dashboard-data";
import type { Block } from "@/lib/schemas/dashboard";

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

function MapPlaceholder() {
  return (
    <div className="surface-elev p-6 text-center font-mono text-caption text-ink-muted">
      Cargando mapa…
    </div>
  );
}
