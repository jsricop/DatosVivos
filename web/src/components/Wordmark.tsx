import Link from "next/link";

type WordmarkProps = {
  /** Si es true, el wordmark se renderiza como h1 (solo en home). */
  asHeading?: boolean;
  /** Tamaño: header (default) o display (XL en home). */
  size?: "header" | "display";
};

/**
 * Wordmark canónico `Datos|Vivos` (BRAND.md §7.1).
 *
 * - Composición: Nunito Sans ExtraBold, letter-spacing -0.02em.
 * - La pleca `|` se renderiza en var(--accent) — es estructura, no decoración.
 * - Bajo el wordmark va siempre `── datos.gov.co` en Plex Mono (§7.2).
 */
export function Wordmark({ asHeading = false, size = "header" }: WordmarkProps) {
  const Tag = asHeading ? "h1" : "div";
  const sizeClass = size === "display" ? "text-display-xl" : "text-h3";

  return (
    <div className="inline-flex flex-col items-start gap-1">
      <Link
        href="/"
        aria-label="Datos Vivos — ir al inicio"
        className="inline-block focus-ring"
      >
        <Tag
          className={`${sizeClass} font-serif font-extrabold text-ink m-0 leading-none`}
          style={{ letterSpacing: "-0.02em" }}
        >
          Datos
          <span className="text-accent" aria-hidden="true">
            |
          </span>
          <span className="sr-only"> </span>
          Vivos
        </Tag>
      </Link>
      <span className="font-mono text-[length:var(--type-kicker)] font-medium text-ink-2 tracking-[0.04em]">
        ── datos.gov.co
      </span>
    </div>
  );
}
