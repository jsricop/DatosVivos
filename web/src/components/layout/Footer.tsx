import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-16 border-t-2 border-accent bg-bg-elev text-ink-2">
      <div className="container-narrow flex flex-col gap-6 py-10">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="flex flex-col gap-1">
            <p className="m-0 font-sans text-body-sm font-bold text-ink">
              República de Colombia
            </p>
            <p className="m-0 font-sans text-caption text-ink-2">
              Agencia Nacional de Infraestructura — Reto #07 MinTIC 2026
            </p>
          </div>
          <nav
            aria-label="Enlaces del pie de página"
            className="flex flex-wrap gap-x-6 gap-y-2"
          >
            <Link href="/tablero" className="font-sans text-body-sm text-ink-2 focus-ring">
              Tablero
            </Link>
            <Link href="/buscar" className="font-sans text-body-sm text-ink-2 focus-ring">
              Buscar
            </Link>
            <Link href="/acerca" className="font-sans text-body-sm text-ink-2 focus-ring">
              Acerca
            </Link>
            <Link
              href="/accesibilidad"
              className="font-sans text-body-sm text-ink-2 focus-ring"
            >
              Accesibilidad
            </Link>
            <a
              href="https://www.datos.gov.co"
              className="font-sans text-body-sm text-ink-2 focus-ring"
            >
              datos.gov.co
            </a>
          </nav>
        </div>
        <p className="m-0 font-mono text-caption text-ink-muted">
          Beta · Sin trackers · Servicio sobre infraestructura del Estado
        </p>
      </div>
    </footer>
  );
}
