"use client";

import { useRevealOnce } from "@/components/panorama/useRevealOnce";

export type StackedSegment = {
  label: string;
  value: number;
  /** Token CSS de color, p.ej. "var(--ok)" o "var(--chart-1)". */
  color: string;
};

const fmt = (n: number) => n.toLocaleString("es-CO");

/**
 * Barra apilada horizontal 100% con leyenda numérica. Dos usos en la home:
 * semáforo de frescura (--ok/--warn/--bad + gris) y acceso a los datos.
 * Crecimiento escalonado por segmento (transition-delay); fail-safe sin JS.
 */
export function StackedBar({
  segments: rawSegments,
  ariaLabel,
}: {
  segments: StackedSegment[];
  ariaLabel: string;
}) {
  const { ref, revealed } = useRevealOnce<HTMLDivElement>();
  // Segmentos en cero no aportan (y "Sin fecha 0" en la leyenda es ruido).
  const segments = rawSegments.filter((s) => s.value > 0);
  const total = segments.reduce((acc, s) => acc + s.value, 0);
  if (total <= 0) return null;

  return (
    <div ref={ref} className="flex flex-col gap-3">
      <div
        role="img"
        aria-label={`${ariaLabel}: ${segments
          .map((s) => `${s.label} ${fmt(s.value)}`)
          .join(", ")}`}
        className="flex h-5 rounded-[var(--radius-0)] overflow-hidden bg-bg-overlay"
      >
        {segments.map((s, i) => (
          <span
            key={s.label}
            className={`block h-full reveal-bar${revealed ? "" : " is-pending"}`}
            style={{
              width: `${(100 * s.value) / total}%`,
              background: s.color,
              transitionDelay: revealed ? `${i * 90}ms` : undefined,
            }}
            aria-hidden="true"
          />
        ))}
      </div>
      <ul className="list-none m-0 p-0 flex flex-wrap gap-x-4 gap-y-1">
        {segments.map((s) => (
          <li
            key={s.label}
            className="inline-flex items-center gap-1.5 font-mono text-caption text-ink-2"
          >
            <span
              aria-hidden="true"
              className="inline-block w-3 h-3"
              style={{ background: s.color, border: "1px solid var(--hairline-strong)" }}
            />
            {s.label}{" "}
            <span className="[font-variant-numeric:tabular-nums]">
              {fmt(s.value)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
