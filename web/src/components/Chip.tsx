"use client";

import type { CSSProperties, KeyboardEvent } from "react";

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
 * Forma: radius 2px, borde 1px hairline default, 2px accent cuando active.
 * Tipografía: Plex Sans 500. Kicker mono uppercase si presente.
 *
 * Invariante: el tamaño NO cambia entre estados — solo el borde se vuelve
 * más grueso. Esto evita saltos visuales en el ChipGroup.
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
  const baseStyle: CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    padding: active ? "7px 13px" : "8px 14px", // compensa border 2px vs 1px
    border: `${active ? "2px" : "1px"} solid ${active ? "var(--accent)" : "var(--hairline)"}`,
    borderRadius: "var(--radius-1)",
    background: active ? "var(--bg-elev)" : "var(--bg)",
    color: disabled ? "var(--ink-muted)" : "var(--ink)",
    fontFamily: "var(--font-sans)",
    fontSize: "var(--type-body-sm)",
    fontWeight: 500,
    cursor: disabled ? "not-allowed" : "pointer",
    transition:
      "border-color var(--duration-fast) var(--easing-standard), background var(--duration-fast) var(--easing-standard)",
  };

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
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "10px",
            fontWeight: 500,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "var(--ink-2)",
          }}
        >
          {kicker}
        </span>
      ) : null}
      <span>{label}</span>
      {typeof count === "number" ? (
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--type-kicker)",
            color: "var(--ink-muted)",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {count}
        </span>
      ) : null}
    </>
  );

  if (as === "link" && href) {
    return (
      <a
        href={href}
        style={{ ...baseStyle, textDecoration: "none" }}
        aria-disabled={disabled || undefined}
      >
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
      style={baseStyle}
    >
      {content}
    </button>
  );
}
