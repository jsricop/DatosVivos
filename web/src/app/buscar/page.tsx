import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { AdvancedQueryBuilder } from "@/components/AdvancedQueryBuilder";
import { ChipsResultView } from "@/components/ChipsResultView";
import { HeroSearch } from "@/components/HeroSearch";
import { ResultStream } from "@/components/ResultStream";
import { SearchPanel } from "@/components/SearchPanel";
import { fetchChipsLists, fetchPopular } from "@/lib/api";
import type { Axis } from "@/components/ChipGroup";

type SearchPageProps = {
  searchParams: Promise<{
    q?: string;
    /** Pregunta NL original cuando el mapper la convirtió a chips. */
    pregunta?: string;
    tema?: string | string[];
    tipo?: string | string[];
    territorio?: string | string[];
    entidad?: string | string[];
    subtag?: string | string[];
    refinador?: string;
    hint?: string;
    /** Filtros de valor sobre el dataset elegido: "col:valor" (ADR-024). */
    filtro?: string | string[];
  }>;
};

export async function generateMetadata({
  searchParams,
}: SearchPageProps): Promise<Metadata> {
  const params = await searchParams;
  const q = (params.q ?? params.pregunta ?? "").trim();
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

  // Modo chips: filtros marcados sin texto libre — flujo determinista.
  if (!q && hasChips) {
    const pregunta = (params.pregunta ?? "").trim();
    // Etiquetas legibles para los chips activos: el TERRITORIO viaja como
    // código DIVIPOLA ("15") y la ENTIDAD como id — el ciudadano debe ver
    // "Boyacá", no el código (2026-07-13).
    const chipsLists = await fetchChipsLists();
    const labels: Record<string, Record<string, string>> = {
      territorio: Object.fromEntries(
        chipsLists.territorio.map((t) => [t.value, t.label]),
      ),
      entidad: Object.fromEntries(
        chipsLists.entidad.map((e) => [e.value, e.label]),
      ),
    };
    return (
      <div className="container-narrow flex flex-col gap-6 py-8">
        <header className="flex flex-col gap-4 pb-2">
          <Link href="/" className="font-mono text-caption text-ink-2 focus-ring">
            ← Volver al inicio
          </Link>
          {pregunta ? <h1 className="text-h2 m-0 text-ink">{pregunta}</h1> : null}
          {/* Buscador abierto arriba: refinar o preguntar otra cosa. */}
          <HeroSearch initialValue={pregunta} size="compact" />
          <ActiveFilters filters={filters} labels={labels} />
        </header>

        <Suspense fallback={<LoadingNote />}>
          <ChipsResultView
            filters={filters}
            subtags={subtags}
            refinador={refinador || undefined}
            hint={params.hint || undefined}
            initialValueFilters={parseValueFilters(params.filtro)}
          />
        </Suspense>
      </div>
    );
  }

  if (!q) {
    // Estado vacío = la puerta del buscador (ADR-023): panel NL + voz +
    // ejemplos, exploración por sector, populares y constructor avanzado.
    const [chipsLists, popular] = await Promise.all([
      fetchChipsLists(),
      fetchPopular(5),
    ]);
    return <EmptyState chipsLists={chipsLists} popular={popular} />;
  }

  const intent = Array.isArray(filters.tipo) ? filters.tipo[0] : filters.tipo;
  const intentLabel = intent ? INTENT_LABEL[intent] : null;

  return (
    <div className="container-narrow flex flex-col gap-6 py-8">
      <header className="flex flex-col gap-4 pb-2">
        <div className="flex justify-between gap-4 items-baseline">
          <span className="text-kicker">
            Pregunta{intentLabel ? ` · ${intentLabel}` : null}
          </span>
          <Link href="/" className="font-mono text-caption text-ink-2 focus-ring">
            ← Volver al inicio
          </Link>
        </div>
        <h1 className="text-h2 m-0 text-ink">{q}</h1>
        {/* Buscador abierto arriba: editar o preguntar otra cosa. */}
        <HeroSearch initialValue={q} size="compact" />
        <ActiveFilters filters={filters} />
      </header>

      <Suspense fallback={<LoadingNote />}>
        <ResultStream question={q} filters={filters} />
      </Suspense>
    </div>
  );
}

type EmptyStateProps = {
  chipsLists: Awaited<ReturnType<typeof fetchChipsLists>>;
  popular: Awaited<ReturnType<typeof fetchPopular>>;
};

function EmptyState({ chipsLists, popular }: EmptyStateProps) {
  const chips: Record<Axis, typeof chipsLists.tema> = {
    tema: chipsLists.tema,
    tipo: chipsLists.tipo,
    territorio: chipsLists.territorio,
    entidad: chipsLists.entidad,
  };
  const sectores = chipsLists.tema.slice(0, 8);

  return (
    <div className="container-narrow py-12 flex flex-col gap-10">
      <header className="flex flex-col gap-4">
        <span className="text-kicker">Buscador</span>
        <h1 className="text-h2 m-0">Empieza por una pregunta</h1>
        <p className="m-0 max-w-[60ch] font-sans text-body-lg text-ink-2 leading-relaxed">
          Escribe una pregunta en lenguaje natural sobre los datos públicos de
          Colombia y recibe la respuesta con su fuente original.
        </p>
      </header>

      <SearchPanel />

      {sectores.length > 0 ? (
        <section className="hairline-top pt-8">
          <div className="mb-4 flex items-baseline justify-between gap-2 flex-wrap">
            <h2 className="text-h3 m-0">¿No sabes por dónde empezar? Explora por sector</h2>
            <span className="font-mono text-caption text-ink-muted">
              {chipsLists.tema.length} sectores
            </span>
          </div>
          <ul className="grid grid-cols-2 md:grid-cols-4 gap-3 list-none m-0 p-0">
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

      {popular.length > 0 ? (
        <section className="hairline-top pt-8">
          <h2 className="text-kicker mb-4">Lo más consultado esta semana</h2>
          <ol className="list-none m-0 p-0 grid gap-3">
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
        </section>
      ) : null}

      {/* Constructor determinista para power users, colapsado al final. */}
      <AdvancedQueryBuilder chips={chips} />
    </div>
  );
}

const AXIS_LABEL: Record<string, string> = {
  tema: "Tema",
  tipo: "Tipo",
  territorio: "Territorio",
  entidad: "Entidad",
};

function ActiveFilters({
  filters,
  labels,
}: {
  filters: Record<string, string[]>;
  /** Mapa opcional eje → (valor → etiqueta legible), ej. "15" → "Boyacá". */
  labels?: Record<string, Record<string, string>>;
}) {
  const chips = Object.entries(filters).flatMap(([axis, values]) =>
    values.map((v) => ({ axis, value: v })),
  );
  if (chips.length === 0) return null;
  return (
    <ul className="flex flex-wrap gap-1.5 list-none">
      {chips.map(({ axis, value }) => (
        <li
          key={`${axis}-${value}`}
          className="inline-flex items-center gap-1 rounded-[var(--radius-3)] border border-hairline bg-bg-elev px-3 py-1 font-mono text-caption text-ink-2"
        >
          <span className="uppercase tracking-wide text-ink-muted">
            {AXIS_LABEL[axis] ?? axis}
          </span>
          <span className="text-hairline">·</span>{" "}
          {labels?.[axis]?.[value] ?? value}
        </li>
      ))}
    </ul>
  );
}

function LoadingNote() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="surface-card animate-pulse p-4 font-mono text-caption text-ink-2"
    >
      Procesando…
    </div>
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

/** "?filtro=sector:OFICIAL" → [{col:"sector", value:"OFICIAL"}]. El valor
 * puede contener ':' — solo el primer separador parte. */
function parseValueFilters(
  raw: string | string[] | undefined,
): Array<{ col: string; value: string }> {
  const items = !raw ? [] : Array.isArray(raw) ? raw : [raw];
  return items.flatMap((s) => {
    const i = s.indexOf(":");
    if (i <= 0 || i === s.length - 1) return [];
    return [{ col: s.slice(0, i), value: s.slice(i + 1) }];
  });
}
