import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { auth, signOut } from "@/lib/auth";
import { buildEmbedUrl, isEmbedConfigured } from "@/lib/embed";

export const metadata: Metadata = {
  title: "Tablero ejecutivo",
  description:
    "Dashboard ejecutivo de DatosVivos: tus datasets, consultas y estado de actualización.",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function TableroPage() {
  const session = await auth();
  if (!session?.user?.email) {
    redirect("/login?callbackUrl=/tablero");
  }

  const entityName = session.user.entityName ?? "Entidad no identificada";
  const entityAbbrev = session.user.entityAbbrev;
  const embedUrl = buildEmbedUrl(entityAbbrev);
  const embedReady = isEmbedConfigured();

  async function doSignOut() {
    "use server";
    await signOut({ redirectTo: "/" });
  }

  return (
    <div className="container-narrow flex flex-col gap-6 py-8">
      <header className="flex flex-wrap items-baseline justify-between gap-4 pb-4 hairline-bottom">
        <div className="flex flex-col gap-1">
          <span className="text-kicker">Tablero ejecutivo</span>
          <h1 className="m-0 font-sans text-h1">{entityName}</h1>
          {!entityAbbrev ? (
            <p className="m-0 font-sans text-body-sm text-ink-muted">
              No reconocemos tu entidad en el directorio. Estás viendo el
              tablero global sin filtros.
            </p>
          ) : null}
        </div>
        <form action={doSignOut}>
          <button
            type="submit"
            className="font-mono text-caption text-ink-2 underline focus-ring"
          >
            Cerrar sesión ({session.user.email})
          </button>
        </form>
      </header>

      {embedReady ? (
        <section
          aria-label={`Dashboard PowerBI de ${entityName}`}
          className="surface-elev p-0 overflow-hidden"
        >
          <iframe
            src={embedUrl}
            title={`Tablero de ${entityName}`}
            allowFullScreen
            loading="lazy"
            referrerPolicy="strict-origin-when-cross-origin"
            sandbox="allow-scripts allow-same-origin allow-popups"
            className="w-full h-[78vh] border-0 block bg-bg-elev"
          />
        </section>
      ) : (
        <section className="surface-elev p-6 flex flex-col gap-3">
          <span className="text-kicker">Tablero no disponible aún</span>
          <p className="m-0 font-sans text-body text-ink-2">
            El equipo de ANI todavía no ha publicado el dashboard PowerBI. Una
            vez publicado con &laquo;publicar en la web&raquo; desde Power BI
            Service y configurada la variable{" "}
            <code className="font-mono">NEXT_PUBLIC_PBI_EMBED_URL</code>, el
            tablero aparecerá aquí filtrado por tu entidad.
          </p>
        </section>
      )}

      <aside
        role="note"
        className="border-l-2 border-accent-2 pl-4 py-3 text-ink-2"
      >
        <span className="text-kicker block mb-2">
          Sobre la seguridad de este tablero
        </span>
        <p className="m-0 font-sans text-body-sm leading-relaxed">
          El filtro por entidad usa parámetros de URL del servicio público de
          Power BI. Un usuario con conocimientos técnicos podría modificar el
          enlace y ver datos de otras entidades. Los datos mostrados son
          agregados del catálogo público <code className="font-mono">datos.gov.co</code>;
          no incluyen información personal ni sensible. Para auditoría estricta
          con Row-Level Security se requiere Power BI Embedded
          (upgrade documentado en ADR-014).
        </p>
      </aside>
    </div>
  );
}
