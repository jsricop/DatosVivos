import Link from "next/link";

import { ColorModeToggle } from "@/components/ColorModeToggle";
import { Wordmark } from "@/components/Wordmark";

export function Header() {
  return (
    <header
      className="hairline-bottom"
      style={{
        position: "sticky",
        insetBlockStart: 0,
        zIndex: 10,
        background: "var(--bg)",
        backdropFilter: "none",
      }}
    >
      <div
        className="container-narrow"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 24,
          paddingBlock: "var(--space-4)",
        }}
      >
        <Wordmark size="header" />
        <nav
          aria-label="Navegación primaria"
          style={{ display: "flex", alignItems: "center", gap: 24 }}
        >
          <Link
            href="/buscar"
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: "var(--type-body-sm)",
              color: "var(--ink-2)",
              borderBottom: "1px solid transparent",
            }}
          >
            Buscar
          </Link>
          <Link
            href="/acerca"
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: "var(--type-body-sm)",
              color: "var(--ink-2)",
              borderBottom: "1px solid transparent",
            }}
          >
            Acerca
          </Link>
          <Link
            href="/accesibilidad"
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: "var(--type-body-sm)",
              color: "var(--ink-2)",
              borderBottom: "1px solid transparent",
            }}
          >
            Accesibilidad
          </Link>
          <ColorModeToggle />
        </nav>
      </div>
    </header>
  );
}
