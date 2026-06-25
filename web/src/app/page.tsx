import Link from "next/link";

import { AdvancedQueryBuilder } from "@/components/AdvancedQueryBuilder";
import { HomeSearchPanel } from "@/components/HomeSearchPanel";
import { fetchChipsLists, fetchPopular } from "@/lib/api";
import type { Axis } from "@/components/ChipGroup";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function HomePage() {
  const [chipsLists, popular] = await Promise.all([
    fetchChipsLists(),
    fetchPopular(7),
  ]);

  const chips: Record<Axis, typeof chipsLists.tema> = {
    tema: chipsLists.tema,
    tipo: chipsLists.tipo,
    territorio: chipsLists.territorio,
    entidad: chipsLists.entidad,
  };

  const sectores = chipsLists.tema.slice(0, 8);

  return (
    <div className="container-narrow flex flex-col gap-10 py-10">
      {/* Hero compacto: la tarea (buscar) queda arriba, en el primer fold. */}
      <section className="flex flex-col gap-4">
        <h1 className="m-0 max-w-[20ch] text-h1 font-extrabold leading-tight text-ink">
          Datos del Estado, en tus palabras.
        </h1>
        <p className="m-0 max-w-[58ch] font-sans text-body-lg text-ink-2 leading-[1.5]">
          Pregunta sobre cualquier dato público colombiano y recibe la respuesta
          con su fuente original. Sin registro, sin filtros, sin opiniones.
        </p>
      </section>

      {/* Entrada PRIMARIA: lenguaje natural. */}
      <HomeSearchPanel />

      {/* Descubrimiento por navegación para quien no sabe qué preguntar. */}
      {sectores.length > 0 ? (
        <section className="hairline-top pt-8">
          <div className="mb-4 flex items-baseline justify-between gap-2 flex-wrap">
            <h2 className="text-h3 m-0">¿No sabes por dónde empezar? Explora por sector</h2>
            <span className="font-mono text-caption text-ink-muted">
              {chipsLists.tema.length} sectores
            </span>
          </div>
          <ul className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {sectores.map((s) => (
              <li key={s.value}>
                <Link
                  href={`/buscar?tema=${encodeURIComponent(s.value)}`}
                  className="surface-card flex h-full items-center px-4 py-3 font-sans text-body-sm font-semibold text-ink no-underline transition-colors hover:border-accent focus-ring"
                >
                  {s.label}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="hairline-top pt-8">
        <h2 className="text-kicker mb-4">Lo más consultado esta semana</h2>
        {popular.length > 0 ? (
          <ol className="list-none grid gap-3">
            {popular.map((p, i) => (
              <li
                key={`${p.question}-${i}`}
                className="grid grid-cols-[auto_1fr_auto] gap-4 items-baseline py-2 hairline-bottom"
              >
                <span className="font-mono [font-variant-numeric:tabular-nums] text-body text-accent font-medium">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <Link
                  href={`/buscar?q=${encodeURIComponent(p.question)}`}
                  className="font-sans text-body-lg font-semibold text-ink focus-ring"
                >
                  {p.question}
                </Link>
                <span className="font-mono text-[length:var(--type-kicker)] text-ink-muted [font-variant-numeric:tabular-nums]">
                  {p.count} consultas
                </span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="font-sans text-body-sm text-ink-muted max-w-[60ch]">
            Aún no hay consultas suficientes para componer este ranking.
            Empieza haciendo tu primera pregunta — la telemetría es anónima y
            se queda en la máquina del Estado.
          </p>
        )}
      </section>

      <section className="hairline-top pt-6">
        <p className="m-0 max-w-[60ch] font-sans text-body text-ink-2 leading-relaxed">
          Este servicio es público y gratuito. Los datos que consultas vienen
          del catálogo oficial del Estado colombiano publicado en datos.gov.co.
          ¿Quieres saber cómo funciona y quién está detrás?{" "}
          <Link href="/acerca" className="focus-ring">
            Lee el manifiesto.
          </Link>
        </p>
      </section>

      {/* Entrada SECUNDARIA (power users): constructor de chips, colapsado. */}
      <AdvancedQueryBuilder chips={chips} />
    </div>
  );
}
