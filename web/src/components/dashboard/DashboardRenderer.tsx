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
 */
export function DashboardRenderer({ spec, rows, stats = null }: Props) {
  if (!spec.blocks.length) return null;

  const isGrid = spec.layout === "grid";
  return (
    <section
      aria-label={`Dashboard: ${spec.title}`}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-5)",
        paddingBlockStart: "var(--space-5)",
        borderBlockStart: "1px solid var(--hairline)",
      }}
    >
      <header
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 6,
        }}
      >
        <span className="kicker">Dashboard generado</span>
        <h2
          style={{
            margin: 0,
            fontFamily: "var(--font-serif)",
            fontSize: "var(--type-h2)",
          }}
        >
          {spec.title}
        </h2>
        {spec.subtitle ? (
          <p
            style={{
              margin: 0,
              fontFamily: "var(--font-sans)",
              fontSize: "var(--type-body-sm)",
              color: "var(--ink-2)",
            }}
          >
            {spec.subtitle}
          </p>
        ) : null}
      </header>

      <div
        style={{
          display: isGrid ? "grid" : "flex",
          flexDirection: isGrid ? undefined : "column",
          gridTemplateColumns: isGrid
            ? "repeat(auto-fit, minmax(280px, 1fr))"
            : undefined,
          gap: "var(--space-4)",
        }}
      >
        {spec.blocks.map((block, i) => (
          <BlockRenderer key={i} block={block} rows={rows} stats={stats} />
        ))}
      </div>

      {spec.caveats?.length ? <Caveats items={spec.caveats} /> : null}
    </section>
  );
}
