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
    <article aria-label={block.title} className="surface-elev p-6 flex flex-col gap-2">
      <span className="text-kicker">{block.title}</span>
      <span
        className="font-mono [font-variant-numeric:tabular-nums] text-accent font-medium leading-none"
        style={{ fontSize: "clamp(2rem, 4vw, 3rem)" }}
      >
        {formatValue(value, block.format)}
      </span>
    </article>
  );
}
