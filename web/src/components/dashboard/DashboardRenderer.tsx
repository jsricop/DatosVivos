"use client";

import { BlockRenderer } from "@/components/dashboard/BlockRenderer";
import { Caveats } from "@/components/dashboard/Caveats";
import type { Row } from "@/lib/dashboard-data";
import type { DashboardSpec } from "@/lib/schemas/dashboard";

type Props = {
  spec: DashboardSpec;
  rows: Row[];
  stats?: Record<string, unknown> | null;
};

/**
 * Renderer raíz del Dashboard Spec (PLAN_DASHBOARD §5.2).
 *
 * No decide colores ni dimensiones — todo viene de los tokens del BRAND.md
 * via CSS variables [data-theme]. El LLM solo decidió `qué` mostrar.
 *
 * Auditabilidad MinTIC (§11.8): incluye `<details>` con el spec JSON crudo.
 */
export function DashboardRenderer({ spec, rows, stats = null }: Props) {
  if (!spec.blocks.length) return null;

  const layoutClass =
    spec.layout === "grid"
      ? "grid grid-cols-[repeat(auto-fit,minmax(280px,1fr))] gap-4"
      : "flex flex-col gap-4";

  return (
    <section
      aria-label={`Dashboard: ${spec.title}`}
      className="flex flex-col gap-6 pt-6 hairline-top"
    >
      <header className="flex flex-col gap-1.5">
        <span className="text-kicker">Dashboard generado</span>
        <h2 className="m-0 font-serif text-h2">{spec.title}</h2>
        {spec.subtitle ? (
          <p className="m-0 font-sans text-body-sm text-ink-2">
            {spec.subtitle}
          </p>
        ) : null}
      </header>

      <div className={layoutClass}>
        {spec.blocks.map((block, i) => (
          <BlockRenderer key={i} block={block} rows={rows} stats={stats} />
        ))}
      </div>

      {spec.caveats?.length ? <Caveats items={spec.caveats} /> : null}

      <details className="surface-elev p-4">
        <summary className="text-kicker cursor-pointer">
          Ver spec JSON (auditabilidad)
        </summary>
        <pre className="font-mono text-caption mt-3 overflow-auto whitespace-pre-wrap text-ink-2">
          {JSON.stringify(spec, null, 2)}
        </pre>
      </details>
    </section>
  );
}
