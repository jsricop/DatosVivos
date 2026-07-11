"use client";

import { useRevealOnce } from "@/components/panorama/useRevealOnce";

export type BarItem = {
  label: string;
  value: number;
  /** Texto adicional junto a la cifra, p.ej. "325 entidades". */
  detail?: string;
};

const fmt = (n: number) => n.toLocaleString("es-CO");

/**
 * Lista de barras horizontales (HTML/CSS, sin SVG). Cada barra crece con
 * `scaleX` al entrar al viewport (clases .reveal-bar de globals.css); el
 * ancho final está en el style inline ⇒ sin JS se ve completa.
 * Usos en la home: datasets por sector, datasets por portal de origen.
 */
export function BarList({ items }: { items: BarItem[] }) {
  const { ref, revealed } = useRevealOnce<HTMLUListElement>();
  if (items.length === 0) return null;
  const max = Math.max(...items.map((s) => s.value));

  return (
    <ul ref={ref} className="list-none m-0 p-0 flex flex-col gap-3">
      {items.map((s, i) => (
        <li
          key={s.label}
          className="grid grid-cols-[minmax(9ch,14ch)_1fr_auto] items-center gap-3"
        >
          <span
            className="font-sans text-body-sm text-ink-2 truncate"
            title={s.label}
          >
            {s.label}
          </span>
          <span className="block h-4 bg-bg-overlay rounded-[var(--radius-0)] overflow-hidden">
            <span
              className={`block h-full bg-accent reveal-bar${revealed ? "" : " is-pending"}`}
              style={{
                width: `${Math.max(2, (100 * s.value) / max)}%`,
                transitionDelay: revealed ? `${i * 60}ms` : undefined,
              }}
              aria-hidden="true"
            />
          </span>
          <span className="font-mono text-caption text-ink-2 [font-variant-numeric:tabular-nums] whitespace-nowrap">
            {fmt(s.value)}
            {s.detail ? (
              <span className="text-ink-muted"> · {s.detail}</span>
            ) : null}
          </span>
        </li>
      ))}
    </ul>
  );
}
