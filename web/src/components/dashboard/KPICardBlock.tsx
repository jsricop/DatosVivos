import { formatValue, resolveKpiValue, type Row } from "@/lib/dashboard-data";
import type { KPIBlock } from "@/lib/schemas/dashboard";

type Props = {
  block: KPIBlock;
  rows: Row[];
  stats: Record<string, unknown> | null;
};

export function KPICardBlock({ block, rows, stats }: Props) {
  const value = resolveKpiValue(block.value_from, rows, stats);
  return (
    <article
      aria-label={block.title}
      style={{
        border: "1px solid var(--hairline)",
        background: "var(--bg-elev)",
        padding: "var(--space-5)",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <span className="kicker">{block.title}</span>
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontVariantNumeric: "tabular-nums",
          fontSize: "clamp(2rem, 4vw, 3rem)",
          color: "var(--accent)",
          fontWeight: 500,
          lineHeight: 1,
        }}
      >
        {formatValue(value, block.format)}
      </span>
    </article>
  );
}
