"use client";

import { useRevealOnce } from "@/components/panorama/useRevealOnce";

export type BarItem = {
  label: string;
  value: number;
  /** Texto adicional junto a la cifra, p.ej. "325 entidades". */
  detail?: string;
  /** Si está presente, el label es un enlace externo (p.ej. al portal de origen). */
  href?: string;
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
          {/* group/relative: al pasar el mouse por una etiqueta truncada
              aparece el nombre COMPLETO al instante (el title nativo tarda
              ~1 s y el usuario no lo descubre, 2026-07-13). */}
          <span className="relative group min-w-0">
            {s.href ? (
              <a
                href={s.href}
                target="_blank"
                rel="noopener noreferrer"
                className="block font-sans text-body-sm text-ink-2 truncate focus-ring"
                title={s.href}
              >
                {s.label}
              </a>
            ) : (
              <span
                className="block font-sans text-body-sm text-ink-2 truncate"
                title={s.label}
              >
                {s.label}
              </span>
            )}
            <span
              role="tooltip"
              className="pointer-events-none absolute left-0 bottom-full z-10 mb-1 hidden max-w-[40ch] whitespace-normal rounded-[var(--radius-1)] bg-ink px-2 py-1 font-sans text-caption text-bg shadow group-hover:block"
            >
              {s.label}
            </span>
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
