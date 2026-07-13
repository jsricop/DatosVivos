import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-16 border-t-2 border-accent bg-bg-elev text-ink-2">
      <div className="container-narrow flex flex-col gap-6 py-10">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="flex flex-col gap-1">
            <p className="m-0 font-sans text-body-sm font-bold text-ink">
              DatosVivos — el panorama de los datos abiertos de Colombia
            </p>
            <p className="m-0 font-sans text-caption text-ink-2">
              Andrea Navarro, Jhonatan Rico &amp; Hernán Gutiérrez · GIT-TIC,
              Agencia Nacional de Infraestructura (ANI)
            </p>
            <p className="m-0 font-sans text-caption text-ink-muted">
              Datos al Ecosistema 2026 · Equipo 93 · Reto 7
            </p>
          </div>
          <nav
            aria-label="Enlaces del pie de página"
            className="flex flex-wrap gap-x-6 gap-y-2"
          >
            <Link href="/" className="font-sans text-body-sm text-ink-2 focus-ring">
              Inicio
            </Link>
            <Link href="/tablero" className="font-sans text-body-sm text-ink-2 focus-ring">
              Detalle entidad
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
          Sin trackers · Fuentes: datos.gov.co + 6 portales integrados ·
          República de Colombia
        </p>
      </div>
    </footer>
  );
}
