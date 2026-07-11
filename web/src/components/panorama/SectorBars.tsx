"use client";

import { useRevealOnce } from "@/components/panorama/useRevealOnce";
import type { SectorCount } from "@/lib/types";

const fmt = (n: number) => n.toLocaleString("es-CO");

/**
 * Barras horizontales por sector (HTML/CSS, sin SVG). Cada barra crece con
 * `scaleX` al entrar al viewport (clases .reveal-bar de globals.css); el
 * ancho final está en el style inline ⇒ sin JS se ve completa.
 */
export function SectorBars({ sectores }: { sectores: SectorCount[] }) {
  const { ref, revealed } = useRevealOnce<HTMLUListElement>();
  if (sectores.length === 0) return null;
  const max = Math.max(...sectores.map((s) => s.n_datasets));

  return (
    <ul ref={ref} className="list-none m-0 p-0 flex flex-col gap-3">
      {sectores.map((s, i) => (
        <li key={s.sector} className="grid grid-cols-[minmax(9ch,14ch)_1fr_auto] items-center gap-3">
          <span
            className="font-sans text-body-sm text-ink-2 truncate"
            title={s.sector}
          >
            {s.sector}
          </span>
          <span className="block h-4 bg-bg-overlay rounded-[var(--radius-0)] overflow-hidden">
            <span
              className={`block h-full bg-accent reveal-bar${revealed ? "" : " is-pending"}`}
              style={{
                width: `${Math.max(2, (100 * s.n_datasets) / max)}%`,
                transitionDelay: revealed ? `${i * 60}ms` : undefined,
              }}
              aria-hidden="true"
            />
          </span>
          <span className="font-mono text-caption text-ink-2 [font-variant-numeric:tabular-nums] whitespace-nowrap">
            {fmt(s.n_datasets)}
            <span className="text-ink-muted"> · {fmt(s.n_entidades)} ent.</span>
          </span>
        </li>
      ))}
    </ul>
  );
}
