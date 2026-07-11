import type { Metadata } from "next";
import Link from "next/link";

import { BarList } from "@/components/panorama/BarList";
import { PanoramaKPIs } from "@/components/panorama/PanoramaKPIs";
import { PanoramaMapLazy } from "@/components/panorama/PanoramaMapLazy";
import { StackedBar } from "@/components/panorama/StackedBar";
import { fetchPanoramaStats } from "@/lib/api";
import type { PanoramaStats } from "@/lib/types";

export const metadata: Metadata = {
  description:
    "El panorama de los datos abiertos de Colombia: cuántos datasets hay, qué entidades publican, qué tan actualizados están y cómo consultarlos. Un solo catálogo que integra datos.gov.co y los portales territoriales.",
};

export const dynamic = "force-dynamic";
export const revalidate = 0;

/**
 * Home panorama (ADR-023): nivel 1 de la arquitectura de información.
 * Panorama nacional → /tablero (detalle por sector/entidad) → /buscar (dato
 * puntual). Cero cajas de búsqueda aquí: la búsqueda es un CTA.
 * Línea editorial sobre el CATÁLOGO COMPLETO (temáticos + administrativos);
 * la composición se muestra como una gráfica más.
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
          Cuántos datos públicos existen, qué entidades los publican, qué tan
          actualizados están y cómo consultarlos. Un solo catálogo, en vivo,
          que integra el portal nacional datos.gov.co con los portales
          territoriales de Bogotá, Cali, Medellín y Valle del Cauca.
        </p>
      </section>

      {stats ? (
        <>
          <PanoramaKPIs stats={stats} />

          {/* Gráficas de panorama: agregados nacionales, sin filtros — el
              corte interactivo por entidad/sector vive en /tablero. */}
          <div className="grid gap-8 md:grid-cols-2">
            <PanelCard
              title="Datasets por sector"
              note="Los 10 sectores con más datasets, entre los que declaran sector. Junto a cada barra: número de datasets y cuántas entidades publican en ese sector."
            >
              <BarList
                items={stats.por_sector.map((s) => ({
                  label: s.sector,
                  value: s.n_datasets,
                  detail: `${s.n_entidades.toLocaleString("es-CO")} entidades`,
                }))}
              />
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
              title="Cómo se accede a los datos"
              note="Consulta en línea: los datos se consultan aquí mismo, al instante. Archivo descargable: la entidad publica un archivo (por ejemplo CSV o Excel) que se descarga para ver su contenido. Solo metadatos: el catálogo registra qué es el recurso y quién lo publica, pero su contenido no es una tabla — son mapas, servicios geográficos o documentos."
            >
              <StackedBar
                ariaLabel="Cómo se accede a los datos"
                segments={[
                  { label: "Consulta en línea", value: stats.acceso.directo, color: "var(--chart-1)" },
                  { label: "Archivo descargable", value: stats.acceso.requiere_herramienta, color: "var(--chart-2)" },
                  { label: "Solo metadatos", value: stats.acceso.solo_metadatos, color: "var(--ink-muted)" },
                ]}
              />
            </PanelCard>

            <PanelCard
              title="Qué contiene el catálogo"
              note="Los reportes administrativos son las publicaciones que la Ley de Transparencia (Ley 1712 de 2014) exige a cada entidad: registros de activos de información, esquemas de publicación e índices. Los datos temáticos son todo lo demás: salud, contratación, educación, movilidad y más."
            >
              <StackedBar
                ariaLabel="Qué contiene el catálogo"
                segments={[
                  { label: "Datos temáticos", value: stats.composicion.tematicos, color: "var(--chart-1)" },
                  { label: "Reportes administrativos", value: stats.composicion.administrativos, color: "var(--ink-muted)" },
                ]}
              />
            </PanelCard>

            <PanelCard
              title="Portales integrados"
              note="Estos portales publican cada uno por su lado; DatosVivos los consolida en un solo catálogo consultable, que de otra forma habría que revisar sitio por sitio."
            >
              <BarList
                items={stats.por_portal.map((p) => ({
                  label: portalLabel(p.portal),
                  value: p.n_datasets,
                }))}
              />
            </PanelCard>
          </div>

          <p className="m-0 font-mono text-caption text-ink-muted">
            Cifras en vivo sobre el catálogo completo ·{" "}
            {relativeTime(stats.generated_at)}
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
          body="Frescura, uso y cobertura territorial del catálogo, con filtros por sector, entidad, tipo de acceso y territorio."
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
          Estado colombiano.{" "}
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

/** Nombre corto y reconocible de cada portal de origen. */
const PORTAL_LABELS: Record<string, string> = {
  "datos.gov.co": "datos.gov.co",
  "datosabiertos.bogota.gov.co": "Bogotá",
  "datos.cali.gov.co": "Cali",
  "www.medata.gov.co": "Medellín (MEDATA)",
  "datosabiertos.valledelcauca.gov.co": "Valle del Cauca",
};

function portalLabel(portal: string): string {
  return PORTAL_LABELS[portal] ?? portal;
}

function frescuraNote(stats: PanoramaStats): string {
  const conFecha =
    stats.semaforo.verde + stats.semaforo.amarillo + stats.semaforo.rojo;
  const base =
    "Un dataset está al día si su última actualización cumple la frecuencia que su propia entidad declaró (por ejemplo, mensual).";
  if (conFecha === 0) return base;
  const alDia = Math.round((10 * stats.semaforo.verde) / conFecha);
  return `${base} Hoy, ${alDia} de cada 10 con fecha conocida lo están.`;
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
