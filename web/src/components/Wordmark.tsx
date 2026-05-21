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
 * - Composición: IBM Plex Serif 600, letter-spacing -0.01em
 * - La pleca `|` se renderiza en var(--accent) — es estructura, no decoración
 * - Bajo el wordmark va siempre `── datos.gov.co` en Plex Mono (BRAND.md §7.2)
 */
export function Wordmark({ asHeading = false, size = "header" }: WordmarkProps) {
  const Tag = asHeading ? "h1" : "div";
  const fontSize =
    size === "display"
      ? "var(--type-display-xl)"
      : "calc(var(--type-h3) * 0.95)";

  return (
    <div className="inline-flex flex-col items-start gap-1">
      <Link
        href="/"
        aria-label="Datos Vivos — ir al inicio"
        className="inline-block"
        style={{ borderBottom: "none" }}
      >
        <Tag
          style={{
            fontFamily: "var(--font-serif)",
            fontWeight: 600,
            letterSpacing: "-0.01em",
            fontSize,
            lineHeight: 1,
            color: "var(--ink)",
            margin: 0,
          }}
        >
          Datos
          <span style={{ color: "var(--accent)" }} aria-hidden="true">
            |
          </span>
          <span className="sr-only"> </span>
          Vivos
        </Tag>
      </Link>
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "var(--type-kicker)",
          fontWeight: 500,
          letterSpacing: "0.04em",
          color: "var(--ink-2)",
        }}
      >
        ── datos.gov.co
      </span>
    </div>
  );
}
