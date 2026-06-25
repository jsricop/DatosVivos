"use client";

import type { KeyboardEvent } from "react";

type ChipProps = {
  label: string;
  value: string;
  kicker?: string;
  count?: number;
  active?: boolean;
  disabled?: boolean;
  onToggle?: (value: string) => void;
  as?: "button" | "link";
  href?: string;
};

/**
 * Chip individual (BRAND.md §8.2).
 *
 * Estados: default · hover · focus-visible · active · disabled.
 * Borde 1px hairline default, 2px accent cuando active.
 * Tipografía Plex Sans 500. Kicker mono uppercase si presente.
 *
 * Invariante: el tamaño NO cambia entre estados — solo el borde se vuelve
 * más grueso. Padding compensa para evitar saltos visuales.
 */
export function Chip({
  label,
  value,
  kicker,
  count,
  active = false,
  disabled = false,
  onToggle,
  as = "button",
  href,
}: ChipProps) {
  const base =
    "inline-flex items-center gap-2 font-sans text-body-sm font-semibold transition-colors focus-ring rounded-[var(--radius-3)]";
  const padding = active ? "py-[7px] px-[15px]" : "py-2 px-4";
  const borderState = active
    ? "border-2 border-accent bg-[color:var(--selection-bg)]"
    : "border border-hairline bg-bg hover:border-accent";
  const colorState = disabled
    ? "text-ink-muted cursor-not-allowed"
    : active
      ? "text-accent cursor-pointer"
      : "text-ink cursor-pointer";

  const className = `${base} ${padding} ${borderState} ${colorState}`;

  function handleKey(event: KeyboardEvent) {
    if (disabled) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onToggle?.(value);
    }
  }

  const content = (
    <>
      {kicker ? (
        <span className="font-mono text-[10px] font-medium uppercase tracking-[0.08em] text-ink-2">
          {kicker}
        </span>
      ) : null}
      <span>{label}</span>
      {typeof count === "number" ? (
        <span className="font-mono text-[length:var(--type-kicker)] text-ink-muted [font-variant-numeric:tabular-nums]">
          {count}
        </span>
      ) : null}
    </>
  );

  if (as === "link" && href) {
    return (
      <a href={href} className={`${className} no-underline`} aria-disabled={disabled || undefined}>
        {content}
      </a>
    );
  }
  return (
    <button
      type="button"
      onClick={() => !disabled && onToggle?.(value)}
      onKeyDown={handleKey}
      disabled={disabled}
      aria-pressed={active}
      className={className}
    >
      {content}
    </button>
  );
}
