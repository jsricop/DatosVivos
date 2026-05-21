import Link from "next/link";
import { Suspense } from "react";

import { HeroSearch } from "@/components/HeroSearch";
import { ResultStream } from "@/components/ResultStream";

type SearchPageProps = {
  searchParams: Promise<{
    q?: string;
    tema?: string | string[];
    tipo?: string | string[];
    territorio?: string | string[];
    entidad?: string | string[];
  }>;
};

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

  if (!q) {
    return <EmptyState />;
  }

  const intent = Array.isArray(filters.tipo)
    ? filters.tipo[0]
    : filters.tipo;
  const intentLabel = intent ? INTENT_LABEL[intent] : null;

  return (
    <div
      className="container-narrow"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-6)",
        paddingBlock: "var(--space-6)",
      }}
    >
      <header
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "var(--space-3)",
          paddingBlockEnd: "var(--space-4)",
          borderBlockEnd: "1px solid var(--hairline)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
          <span className="kicker">
            Pregunta
            {intentLabel ? ` · ${intentLabel}` : null}
          </span>
          <Link
            href="/"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "var(--type-caption)",
              color: "var(--ink-2)",
            }}
          >
            ← volver al inicio
          </Link>
        </div>
        <h1
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: "var(--type-h1)",
            margin: 0,
            color: "var(--ink)",
          }}
        >
          {q}
        </h1>
        <ActiveFilters filters={filters} />
      </header>

      <Suspense fallback={<p>Procesando…</p>}>
        <ResultStream question={q} filters={filters} />
      </Suspense>

      <section
        aria-label="Editar consulta"
        style={{
          paddingBlockStart: "var(--space-5)",
          borderBlockStart: "1px solid var(--hairline)",
        }}
      >
        <span
          className="kicker"
          style={{ display: "block", marginBlockEnd: 12 }}
        >
          Editar consulta
        </span>
        <HeroSearch initialValue={q} size="compact" />
      </section>
    </div>
  );
}

function EmptyState() {
  return (
    <div
      className="container-narrow"
      style={{
        paddingBlock: "var(--space-8)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-4)",
        maxInlineSize: "60ch",
      }}
    >
      <span className="kicker">Sin consulta</span>
      <h1
        style={{
          fontFamily: "var(--font-serif)",
          fontSize: "var(--type-h2)",
          margin: 0,
        }}
      >
        Empieza por una pregunta
      </h1>
      <p
        style={{
          fontFamily: "var(--font-sans)",
          fontSize: "var(--type-body-lg)",
          color: "var(--ink-2)",
          lineHeight: 1.6,
        }}
      >
        Pasa una pregunta en lenguaje natural sobre los datos públicos de
        Colombia. Por ejemplo: ¿Cuántos colegios públicos hay en Boyacá?
      </p>
      <HeroSearch size="display" />
    </div>
  );
}

function ActiveFilters({
  filters,
}: {
  filters: Record<string, string[]>;
}) {
  const chips = Object.entries(filters).flatMap(([axis, values]) =>
    values.map((v) => ({ axis, value: v })),
  );
  if (chips.length === 0) return null;
  return (
    <ul
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 6,
        listStyle: "none",
      }}
    >
      {chips.map(({ axis, value }) => (
        <li
          key={`${axis}-${value}`}
          style={{
            border: "1px solid var(--hairline)",
            padding: "4px 10px",
            borderRadius: "var(--radius-1)",
            fontFamily: "var(--font-mono)",
            fontSize: "var(--type-caption)",
            color: "var(--ink-2)",
          }}
        >
          <span style={{ color: "var(--ink-muted)" }}>{axis} ·</span> {value}
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
