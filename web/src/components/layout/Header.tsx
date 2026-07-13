import { ColorModeToggle } from "@/components/ColorModeToggle";
import { NavLink } from "@/components/layout/NavLink";
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
          className="flex items-center gap-1.5"
        >
          <NavLink href="/">Inicio</NavLink>
          <NavLink href="/tablero">Tablero</NavLink>
          <NavLink href="/buscar">Buscar</NavLink>
          <NavLink href="/mcp">MCP</NavLink>
          <NavLink href="/acerca">Acerca</NavLink>
          {/* La página /accesibilidad vive en el footer: el header ya cubre
              la necesidad inmediata con el switch de apariencia. */}
          <span className="ml-3">
            <ColorModeToggle />
          </span>
        </nav>
      </div>
    </header>
  );
}
