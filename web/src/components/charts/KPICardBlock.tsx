import { formatValue, resolveKpiValue, type Row } from "@/lib/dashboard-data";
import type { KPIBlock } from "@/lib/schemas/dashboard";

type Props = {
  block: KPIBlock;
  rows: Row[];
  stats: Record<string, unknown> | null;
  /** Unidad de medida junto a la cifra ("estudiantes matriculados"):
   *  sin ella el número grande se leía como lo que no era (2026-07-13). */
  unit?: string | null;
};

export function KPICardBlock({ block, rows, stats, unit }: Props) {
  const value = resolveKpiValue(block.value_from, rows, stats);
  return (
    <article aria-label={block.title} className="surface-elev p-6 flex flex-col gap-2">
      <span className="text-kicker">{block.title}</span>
      <span className="flex flex-wrap items-baseline gap-3">
        <span
          className="font-mono [font-variant-numeric:tabular-nums] text-accent font-medium leading-none"
          style={{ fontSize: "clamp(2rem, 4vw, 3rem)" }}
        >
          {formatValue(value, block.format)}
        </span>
        {unit ? (
          <span className="font-sans text-h4 font-semibold text-ink-2">
            {unit}
          </span>
        ) : null}
      </span>
    </article>
  );
}
