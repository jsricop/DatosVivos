import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { ChipsResultView } from "@/components/ChipsResultView";
import { HeroSearch } from "@/components/HeroSearch";
import { ResultStream } from "@/components/ResultStream";

type SearchPageProps = {
  searchParams: Promise<{
    q?: string;
    tema?: string | string[];
    tipo?: string | string[];
    territorio?: string | string[];
    entidad?: string | string[];
    subtag?: string | string[];
    refinador?: string;
  }>;
};

export async function generateMetadata({
  searchParams,
}: SearchPageProps): Promise<Metadata> {
  const params = await searchParams;
  const q = (params.q ?? "").trim();
  // No indexar resultados dinámicos: cada combinación de query parameters
  // generaría una URL distinta que no aporta valor SEO único.
  return {
    title: q ? `${q.slice(0, 60)} · Consulta` : "Buscar",
    description: q
      ? `Resultados de "${q}" sobre el catálogo de datos.gov.co.`
      : "Pregunta sobre cualquier dato público colombiano y recibe la respuesta con la fuente original a un click.",
    robots: { index: false, follow: true },
    alternates: { canonical: q ? null : "/buscar" },
  };
}

const INTENT_LABEL: Record<string, string> = {
  count: "Conteo",
  compare: "Comparativa",
  ranking: "Ranking",
  trend: "Tendencia",
  map: "Mapa",
};

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const params = await searchParams;
  const q = (params.q ?? "").trim();
  const filters = normalizeFilters(params);
  const subtags = normalizeSubtags(params.subtag);
  const refinador = (params.refinador ?? "").trim();
  const hasChips =
    Object.values(filters).some((v) => v.length > 0) || subtags.length > 0;

  // Modo chips: chips marcados sin texto libre — flujo determinista
  // (Fase 1.1 del audit top-down).
  if (!q && hasChips) {
    return (
      <div className="container-narrow flex flex-col gap-5 py-6">
        <header className="flex flex-col gap-2 pb-3 hairline-bottom">
          <div className="flex justify-between gap-4 items-baseline">
            <span className="text-kicker">Búsqueda por filtros</span>
            <Link
              href="/"
              className="font-mono text-caption text-ink-2 focus-ring"
            >
              ← volver al inicio
            </Link>
          </div>
          <ActiveFilters filters={filters} />
        </header>

        <Suspense fallback={<p>Procesando…</p>}>
          <ChipsResultView
            filters={filters}
            subtags={subtags}
            refinador={refinador || undefined}
          />
        </Suspense>

        <section aria-label="Modo libre (avanzado)" className="pt-6 hairline-top">
          <details>
            <summary className="cursor-pointer font-mono text-caption text-ink-2 hover:text-ink focus-ring">
              Modo libre (avanzado) — preguntar con texto libre
            </summary>
            <div className="mt-4">
              <HeroSearch size="compact" />
            </div>
          </details>
        </section>
      </div>
    );
  }

  if (!q) return <EmptyState />;

  const intent = Array.isArray(filters.tipo) ? filters.tipo[0] : filters.tipo;
  const intentLabel = intent ? INTENT_LABEL[intent] : null;

  return (
    <div className="container-narrow flex flex-col gap-8 py-8">
      <header className="flex flex-col gap-3 pb-4 hairline-bottom">
        <div className="flex justify-between gap-4">
          <span className="text-kicker">
            Pregunta
            {intentLabel ? ` · ${intentLabel}` : null}
          </span>
          <Link
            href="/"
            className="font-mono text-caption text-ink-2 focus-ring"
          >
            ← volver al inicio
          </Link>
        </div>
        <h1 className="font-serif text-h1 m-0 text-ink">{q}</h1>
        <ActiveFilters filters={filters} />
      </header>

      <Suspense fallback={<p>Procesando…</p>}>
        <ResultStream question={q} filters={filters} />
      </Suspense>

      <section aria-label="Editar consulta" className="pt-6 hairline-top">
        <span className="text-kicker block mb-3">Editar consulta</span>
        <HeroSearch initialValue={q} size="compact" />
      </section>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="container-narrow py-16 flex flex-col gap-4 max-w-[60ch]">
      <span className="text-kicker">Sin consulta</span>
      <h1 className="font-serif text-h2 m-0">Empieza por una pregunta</h1>
      <p className="font-sans text-body-lg text-ink-2 leading-relaxed">
        Pasa una pregunta en lenguaje natural sobre los datos públicos de
        Colombia. Por ejemplo: ¿Cuántos colegios públicos hay en Boyacá?
      </p>
      <HeroSearch size="display" />
    </div>
  );
}

function ActiveFilters({ filters }: { filters: Record<string, string[]> }) {
  const chips = Object.entries(filters).flatMap(([axis, values]) =>
    values.map((v) => ({ axis, value: v })),
  );
  if (chips.length === 0) return null;
  return (
    <ul className="flex flex-wrap gap-1.5 list-none">
      {chips.map(({ axis, value }) => (
        <li
          key={`${axis}-${value}`}
          className="border border-hairline px-2.5 py-1 rounded-[var(--radius-1)] font-mono text-caption text-ink-2"
        >
          <span className="text-ink-muted">{axis} ·</span> {value}
        </li>
      ))}
    </ul>
  );
}

function normalizeFilters(
  params: Awaited<SearchPageProps["searchParams"]>,
): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const key of ["tema", "tipo", "territorio", "entidad"] as const) {
    const raw = params[key];
    if (!raw) continue;
    out[key] = Array.isArray(raw) ? raw : [raw];
  }
  return out;
}

function normalizeSubtags(raw: string | string[] | undefined): string[] {
  if (!raw) return [];
  return Array.isArray(raw) ? raw : [raw];
}
