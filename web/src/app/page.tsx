import type { Metadata } from "next";
import Link from "next/link";

import { BarList } from "@/components/panorama/BarList";
import { PanoramaKPIs } from "@/components/panorama/PanoramaKPIs";
import { PanoramaMapLazy } from "@/components/panorama/PanoramaMapLazy";
import { StackedBar } from "@/components/panorama/StackedBar";
import { TimelineArea } from "@/components/panorama/TimelineArea";
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
        <span className="text-kicker">Panorama de datos abiertos · Colombia</span>
        <h1 className="m-0 max-w-[22ch] text-h1 font-extrabold leading-tight text-ink">
          El panorama de los datos abiertos de Colombia
        </h1>
        <p className="m-0 max-w-[58ch] font-sans text-body-lg text-ink-2 leading-[1.5]">
          Cuántos datos públicos existen, qué entidades los publican, qué tan
          actualizados están y cómo consultarlos. Un solo catálogo, en vivo,
          que integra el portal nacional datos.gov.co, el geoportal del IGAC
          y los portales territoriales de Bogotá, Cali, Medellín y Valle del
          Cauca.
        </p>
      </section>

      {stats ? (
        <>
          <PanoramaKPIs stats={stats} />

          {/* Línea de tiempo a ancho completo: el crecimiento del catálogo
              es LA historia del ecosistema — abre la sección de gráficas. */}
          {stats.crecimiento && stats.crecimiento.length >= 2 ? (
            <PanelCard
              title="Cómo ha crecido el catálogo"
              note="Acumulado según la fecha de creación de cada dataset en su portal de origen. Para los publicados antes de la integración de DatosVivos esa fecha es el mejor estimado disponible."
            >
              <TimelineArea puntos={stats.crecimiento} />
            </PanelCard>
          ) : null}

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

            <PanelCard title="Frescura del catálogo">
              <StackedBar
                ariaLabel="Frescura del catálogo"
                segments={[
                  { label: "Al día", value: stats.semaforo.verde, color: "var(--ok)" },
                  { label: "Atrasados", value: stats.semaforo.amarillo, color: "var(--warn)" },
                  { label: "Muy atrasados", value: stats.semaforo.rojo, color: "var(--bad)" },
                  { label: "Sin fecha", value: stats.semaforo.desconocido, color: "var(--ink-muted)" },
                ]}
              />
              <DefList
                items={[
                  {
                    term: "Al día",
                    def: "la última actualización cumple la frecuencia que la propia entidad declaró (por ejemplo, mensual).",
                  },
                ]}
              />
              {frescuraResumen(stats) ? (
                <p className="m-0 font-sans text-body-sm font-semibold text-ink">
                  {frescuraResumen(stats)}
                </p>
              ) : null}
            </PanelCard>

            <PanelCard title="Cómo se accede a los datos">
              <StackedBar
                ariaLabel="Cómo se accede a los datos"
                segments={[
                  { label: "Consulta en línea", value: stats.acceso.directo, color: "var(--chart-1)" },
                  { label: "Archivo descargable", value: stats.acceso.requiere_herramienta, color: "var(--chart-2)" },
                  { label: "Solo metadatos", value: stats.acceso.solo_metadatos, color: "var(--ink-muted)" },
                ]}
              />
              <DefList
                items={[
                  {
                    term: "Consulta en línea",
                    def: "los datos se consultan aquí mismo, al instante.",
                  },
                  {
                    term: "Archivo descargable",
                    def: "la entidad publica un archivo (por ejemplo CSV o Excel) que se descarga para ver su contenido.",
                  },
                  {
                    term: "Solo metadatos",
                    def: "el catálogo registra qué es el recurso y quién lo publica, pero su contenido no es una tabla: mapas, servicios geográficos o documentos.",
                  },
                ]}
              />
            </PanelCard>

            <PanelCard title="Qué contiene el catálogo">
              <StackedBar
                ariaLabel="Qué contiene el catálogo"
                segments={[
                  { label: "Datos temáticos", value: stats.composicion.tematicos, color: "var(--chart-1)" },
                  { label: "Reportes administrativos", value: stats.composicion.administrativos, color: "var(--ink-muted)" },
                ]}
              />
              <DefList
                items={[
                  {
                    term: "Datos temáticos",
                    def: "salud, contratación, educación, movilidad y más.",
                  },
                  {
                    term: "Reportes administrativos",
                    def: "las publicaciones que la Ley de Transparencia (Ley 1712 de 2014) exige a cada entidad: registros de activos de información, esquemas de publicación e índices.",
                  },
                ]}
              />
            </PanelCard>

            <PanelCard
              title="Portales integrados"
              note="Cada dataset se atribuye al portal donde su entidad lo publica originalmente. Publican cada uno por su lado; DatosVivos los consolida en un solo catálogo consultable."
            >
              <BarList
                items={stats.por_portal.map((p) => ({
                  label: portalLabel(p.portal),
                  value: p.n_datasets,
                  href: portalUrl(p.portal),
                }))}
              />
              <p className="m-0 font-sans text-caption text-ink-2 leading-relaxed">
                Consúltalos directamente:{" "}
                {stats.por_portal.map((p, i) => (
                  <span key={p.portal}>
                    {i > 0 ? " · " : null}
                    <a
                      href={portalUrl(p.portal)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="focus-ring font-mono"
                    >
                      {p.portal.replace(/^www\./, "")}
                    </a>
                  </span>
                ))}
              </p>
            </PanelCard>
          </div>

          <p className="m-0 font-mono text-caption text-ink-muted">
            Cifras en vivo sobre el catálogo completo ·{" "}
            {etlTimestamp(stats.last_etl_at)}
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

/** Nombre corto y reconocible de cada portal de origen (claves sin www). */
const PORTAL_LABELS: Record<string, string> = {
  "datos.gov.co": "datos.gov.co",
  "colombiaenmapas.igac.gov.co": "IGAC (Colombia en Mapas)",
  "datosabiertos.bogota.gov.co": "Bogotá",
  "datos.cali.gov.co": "Cali",
  "medata.gov.co": "Medellín (MEDATA)",
  "datosabiertos.valledelcauca.gov.co": "Valle del Cauca",
};

function portalLabel(portal: string): string {
  return PORTAL_LABELS[portal] ?? portal;
}

/** URL pública del portal (claves canónicas sin www; algunos sirven con www). */
const PORTAL_URLS: Record<string, string> = {
  "datos.gov.co": "https://www.datos.gov.co",
  "colombiaenmapas.igac.gov.co": "https://www.colombiaenmapas.igac.gov.co",
  "medata.gov.co": "https://www.medata.gov.co",
};

function portalUrl(portal: string): string {
  return PORTAL_URLS[portal] ?? `https://${portal}`;
}

/**
 * Lista de definiciones: cada término con su ancla en negrilla y la
 * explicación al lado — un renglón por tema, sin párrafos corridos.
 */
function DefList({ items }: { items: Array<{ term: string; def: string }> }) {
  return (
    <dl className="m-0 flex flex-col gap-2">
      {items.map((it) => (
        <div key={it.term} className="font-sans text-caption leading-relaxed">
          <dt className="inline font-semibold text-ink-2">{it.term}:</dt>{" "}
          <dd className="inline m-0 p-0 text-ink-muted">{it.def}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Lectura en una frase del semáforo, destacada aparte de las definiciones. */
function frescuraResumen(stats: PanoramaStats): string | null {
  const conFecha =
    stats.semaforo.verde + stats.semaforo.amarillo + stats.semaforo.rojo;
  if (conFecha === 0) return null;
  const alDia = Math.round((10 * stats.semaforo.verde) / conFecha);
  return `Hoy, ${alDia} de cada 10 datasets con fecha conocida están al día.`;
}

/**
 * Fecha y hora del cierre de la última corrida del ETL, en hora de Colombia.
 * Es la fecha REAL del dato — no la del caché de la API (que se regenera cada
 * 5 min y producía el engañoso "actualizado hace 2 min").
 */
function etlTimestamp(iso: string | null | undefined): string {
  const then = iso ? Date.parse(iso) : NaN;
  if (Number.isNaN(then)) return "actualización diaria automática";
  const fecha = new Intl.DateTimeFormat("es-CO", {
    timeZone: "America/Bogota",
    day: "numeric",
    month: "long",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(new Date(then));
  return `actualizado el ${fecha} (hora de Colombia)`;
}
