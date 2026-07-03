import type { CatalogStats } from "@/lib/types";

const fmt = (n: number) => n.toLocaleString("es-CO");

/**
 * Tarjetas KPI del catálogo en vivo. Los valores vienen de
 * GET /api/v1/stats/catalog (misma vista que el tablero Power BI), así que
 * nunca se desfasan. Server component: si no hay datos, no renderiza nada.
 */
export function CatalogStatsBlock({ stats }: { stats: CatalogStats | null }) {
  if (!stats || stats.total <= 0) return null;

  const cards: Array<{ label: string; value: number; hint?: string }> = [
    { label: "Datasets en el catálogo", value: stats.total },
    {
      label: "Consultables como tabla",
      value: stats.consultable_tabla,
      hint: "directo + requiere herramienta",
    },
    { label: "Nativos (datos.gov.co)", value: stats.nativos },
    { label: "Federados (CKAN · DCAT · IGAC)", value: stats.federados },
  ];

  return (
    <section className="hairline-top pt-8">
      <div className="mb-4 flex items-baseline justify-between gap-2 flex-wrap">
        <h2 className="text-h3 m-0">El catálogo en números</h2>
        <span className="font-mono text-caption text-ink-muted">
          actualizado en vivo
        </span>
      </div>
      <ul className="grid grid-cols-2 md:grid-cols-4 gap-3 list-none m-0 p-0">
        {cards.map((c) => (
          <li
            key={c.label}
            className="surface-elev p-6 flex flex-col gap-2"
          >
            <span
              className="font-mono [font-variant-numeric:tabular-nums] text-accent font-medium leading-none"
              style={{ fontSize: "clamp(1.75rem, 4vw, 2.75rem)" }}
            >
              {fmt(c.value)}
            </span>
            <span className="text-kicker">{c.label}</span>
            {c.hint ? (
              <span className="font-sans text-caption text-ink-muted">
                {c.hint}
              </span>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
