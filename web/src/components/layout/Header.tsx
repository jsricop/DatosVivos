import Link from "next/link";

import { ColorModeToggle } from "@/components/ColorModeToggle";
import { Wordmark } from "@/components/Wordmark";

export function Header() {
  return (
    <header className="sticky top-0 z-10 bg-bg hairline-bottom">
      <div className="container-narrow flex items-center justify-between gap-6 py-4">
        <Wordmark size="header" />
        <nav
          aria-label="Navegación primaria"
          className="flex items-center gap-6"
        >
          <Link
            href="/buscar"
            className="font-sans text-body-sm text-ink-2 focus-ring"
          >
            Buscar
          </Link>
          <Link
            href="/acerca"
            className="font-sans text-body-sm text-ink-2 focus-ring"
          >
            Acerca
          </Link>
          <Link
            href="/accesibilidad"
            className="font-sans text-body-sm text-ink-2 focus-ring"
          >
            Accesibilidad
          </Link>
          <ColorModeToggle />
        </nav>
      </div>
    </header>
  );
}
