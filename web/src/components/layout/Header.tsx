import Link from "next/link";

import { ColorModeToggle } from "@/components/ColorModeToggle";
import { Wordmark } from "@/components/Wordmark";

export function Header() {
  return (
    <header className="sticky top-0 z-10 bg-bg hairline-bottom">
      {/* Barra institucional — imagen del Estado colombiano (atribución textual,
          sin escudo ni logo gov.co). Evoca el patrón GovHead. */}
      <div className="bg-accent text-bg">
        <div className="container-narrow flex items-center justify-between gap-4 py-1.5">
          <span className="font-sans text-[length:var(--type-kicker)] font-semibold tracking-wide uppercase">
            República de Colombia
          </span>
          <span className="font-mono text-[length:var(--type-kicker)] tracking-wide">
            Datos abiertos del Estado
          </span>
        </div>
      </div>
      <div className="container-narrow flex items-center justify-between gap-6 py-4">
        <Wordmark size="header" />
        <nav
          aria-label="Navegación primaria"
          className="flex items-center gap-6"
        >
          <Link
            href="/"
            className="font-sans text-body-sm text-ink-2 focus-ring"
          >
            Inicio
          </Link>
          <Link
            href="/tablero"
            className="font-sans text-body-sm text-ink-2 focus-ring"
          >
            Tablero
          </Link>
          <Link
            href="/buscar"
            className="font-sans text-body-sm text-ink-2 focus-ring"
          >
            Buscar
          </Link>
          <Link
            href="/mcp"
            className="font-sans text-body-sm text-ink-2 focus-ring"
          >
            MCP
          </Link>
          <Link
            href="/acerca"
            className="font-sans text-body-sm text-ink-2 focus-ring"
          >
            Acerca
          </Link>
          {/* La página /accesibilidad vive en el footer: el header ya cubre
              la necesidad inmediata con el switch de apariencia. */}
          <ColorModeToggle />
        </nav>
      </div>
    </header>
  );
}
