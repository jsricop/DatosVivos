import type { Metadata } from "next";
import Link from "next/link";

import { PanoramaKPIs } from "@/components/panorama/PanoramaKPIs";
import { PanoramaMapLazy } from "@/components/panorama/PanoramaMapLazy";
import { SectorBars } from "@/components/panorama/SectorBars";
import { StackedBar } from "@/components/panorama/StackedBar";
import { fetchPanoramaStats } from "@/lib/api";
import type { PanoramaStats } from "@/lib/types";

export const metadata: Metadata = {
  description:
    "El panorama de los datos abiertos de Colombia: cuántos datasets hay, qué entidades publican, qué tan actualizados están y cómo acceder a ellos. Explora el detalle o pregunta en tus palabras.",
};

export const dynamic = "force-dynamic";
export const revalidate = 0;

/**
 * Home panorama (ADR-023): nivel 1 de la arquitectura de información.
 * Panorama nacional → /tablero (detalle por sector/entidad) → /buscar (dato
 * puntual). Cero cajas de búsqueda aquí: la búsqueda es un CTA.
 */
export default async function HomePage() {
  const stats = await fetchPanoramaStats();

  return (
    <div className="container-narrow flex flex-col gap-10 py-10">
      {/* Hero: línea de marca como kicker, titular de panorama. */}
      <section className="flex flex-col gap-4">
        <span className="text-kicker">Datos del Estado, en tus palabras</span>
        <h1 className="m-0 max-w-[22ch] text-h1 font-extrabold leading-tight text-ink">
          El panorama de los datos abiertos de Colombia
        </h1>
        <p className="m-0 max-w-[58ch] font-sans text-body-lg text-ink-2 leading-[1.5]">
          Cuántos datasets públicos hay, qué entidades los publican, qué tan
          actualizados están y cómo acceder a ellos. Cifras en vivo del
          catálogo oficial de datos.gov.co.
        </p>
      </section>

      {stats ? (
        <>
          <PanoramaKPIs stats={stats} />

          {/* Gráficas de panorama: agregados nacionales, sin filtros — el
              corte interactivo por entidad/sector vive en /tablero. */}
          <div className="grid gap-8 md:grid-cols-2">
            <PanelCard title="Datasets por sector" note={sectorNote(stats)}>
              <SectorBars sectores={stats.por_sector} />
            </PanelCard>

            <PanelCard title="Cobertura por departamento">
              <PanoramaMapLazy
                departamentos={stats.por_departamento}
                nacionalSinGeo={stats.nacional_sin_geo}
              />
            </PanelCard>

            <PanelCard title="Frescura del catálogo" note={frescuraNote(stats)}>
              <StackedBar
                ariaLabel="Frescura del catálogo"
                segments={[
                  { label: "Al día", value: stats.semaforo.verde, color: "var(--ok)" },
                  { label: "Atrasados", value: stats.semaforo.amarillo, color: "var(--warn)" },
                  { label: "Muy atrasados", value: stats.semaforo.rojo, color: "var(--bad)" },
                  { label: "Sin fecha", value: stats.semaforo.desconocido, color: "var(--ink-muted)" },
                ]}
              />
            </PanelCard>

            <PanelCard
              title="Acceso a los datos"
              note="Directo = consulta inmediata vía API. Con herramienta = archivo externo descargable. Solo metadatos = descubrible pero no tabular."
            >
              <StackedBar
                ariaLabel="Acceso a los datos"
                segments={[
                  { label: "Directo", value: stats.acceso.directo, color: "var(--chart-1)" },
                  { label: "Con herramienta", value: stats.acceso.requiere_herramienta, color: "var(--chart-2)" },
                  { label: "Solo metadatos", value: stats.acceso.solo_metadatos, color: "var(--ink-muted)" },
                ]}
              />
            </PanelCard>
          </div>

          <p className="m-0 font-mono text-caption text-ink-muted">
            Cifras en vivo del catálogo útil (excluye reportes administrativos
            de Ley 1712) · {relativeTime(stats.generated_at)}
          </p>
        </>
      ) : (
        <section className="surface-elev p-6">
          <p className="m-0 font-sans text-body text-ink-2">
            Las cifras del catálogo no están disponibles en este momento.
            Puedes explorar el tablero o hacer una consulta directa.
          </p>
        </section>
      )}

      {/* LA salida de la página: dos rutas, jerarquía clara. */}
      <section aria-label="Explora los datos" className="grid gap-4 md:grid-cols-2">
        <CTACard
          href="/tablero"
          kicker="Tablero interactivo"
          title="Explora el detalle por sector y entidad"
          body="Salud del catálogo, engagement y cobertura territorial, con filtros por sector, entidad, acceso y territorio."
        />
        <CTACard
          href="/buscar"
          kicker="Buscador"
          title="Pregunta en tus palabras"
          body="Haz una pregunta en lenguaje natural sobre cualquier dato público y recibe la respuesta con su fuente original."
        />
      </section>

      <section className="hairline-top pt-6">
        <p className="m-0 max-w-[60ch] font-sans text-body text-ink-2 leading-relaxed">
          Este servicio es público y gratuito, sobre el catálogo oficial del
          Estado colombiano en datos.gov.co.{" "}
          <Link href="/acerca" className="focus-ring">
            Cómo funciona y quién está detrás.
          </Link>
        </p>
      </section>
    </div>
  );
}

function PanelCard({
  title,
  note,
  children,
}: {
  title: string;
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <section aria-label={title} className="surface-elev p-6 flex flex-col gap-4">
      <h2 className="text-h4 m-0">{title}</h2>
      {children}
      {note ? (
        <p className="m-0 font-sans text-caption text-ink-muted leading-relaxed">
          {note}
        </p>
      ) : null}
    </section>
  );
}

function CTACard({
  href,
  kicker,
  title,
  body,
}: {
  href: "/tablero" | "/buscar";
  kicker: string;
  title: string;
  body: string;
}) {
  return (
    <Link
      href={href}
      className="surface-elev p-6 flex flex-col gap-2 no-underline transition-colors hover:border-accent focus-ring"
    >
      <span className="text-kicker">{kicker}</span>
      <span className="font-sans text-h3 font-semibold text-ink leading-snug">
        {title} <span aria-hidden="true">→</span>
      </span>
      <span className="font-sans text-body-sm text-ink-2 leading-relaxed">
        {body}
      </span>
    </Link>
  );
}

/** Solo datasets con sector declarado — federados sin sector quedan fuera. */
function sectorNote(_stats: PanoramaStats): string {
  return 'Los 10 sectores con más datasets, entre los que declaran sector · barras: datasets · "ent." = entidades del sector.';
}

function frescuraNote(stats: PanoramaStats): string {
  const conFecha =
    stats.semaforo.verde + stats.semaforo.amarillo + stats.semaforo.rojo;
  if (conFecha === 0) {
    return "Frescura medida contra la frecuencia de actualización que declara cada dataset.";
  }
  const alDia = Math.round((10 * stats.semaforo.verde) / conFecha);
  return `${alDia} de cada 10 datasets con fecha conocida están al día frente a su propia frecuencia declarada.`;
}

/** Tiempo relativo corto para "actualizado hace N min" (render server-side). */
function relativeTime(iso: string): string {
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return "actualizado en vivo";
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return "actualizado hace un momento";
  if (mins < 60) return `actualizado hace ${mins} min`;
  return `actualizado hace ${Math.round(mins / 60)} h`;
}
