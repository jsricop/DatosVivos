"use client";

import dynamic from "next/dynamic";

import { BarChartBlock } from "@/components/dashboard/BarChartBlock";
import { KPICardBlock } from "@/components/dashboard/KPICardBlock";
import { LineChartBlock } from "@/components/dashboard/LineChartBlock";
import { TableBlock } from "@/components/dashboard/TableBlock";
import type { Row } from "@/lib/dashboard-data";
import type { Block } from "@/lib/schemas/dashboard";

const ChoroplethMapBlock = dynamic(
  () =>
    import("@/components/dashboard/ChoroplethMapBlock").then(
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
    <div
      style={{
        border: "1px solid var(--hairline)",
        background: "var(--bg-elev)",
        padding: "var(--space-5)",
        textAlign: "center",
        fontFamily: "var(--font-mono)",
        fontSize: "var(--type-caption)",
        color: "var(--ink-muted)",
      }}
    >
      Cargando mapa…
    </div>
  );
}
