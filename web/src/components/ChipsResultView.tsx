"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { ChipsResultPanel } from "@/components/ChipsResultPanel";
import { FilterBar } from "@/components/FilterBar";
import { Icon } from "@/components/Icon";
import type {
  ChipTipo,
  ChipsExecuteResponse,
  ChipsExplainResponse,
  DatasetFiltersResponse,
  FilterColumn,
  FilterSpec,
} from "@/lib/types";

/** Espejo de api/models/schemas.py::ChipsCandidateDataset */
type Candidate = {
  dataset_id: string;
  name: string;
  entity: string | null;
  category: string | null;
  row_count: number | null;
  view_count: number | null;
  last_updated: string | null;
  url: string;
  api_url: string;
  jurisdiccion_nivel: string | null;
  jurisdiccion_geo_codes: string[] | null;
};

type ChipsQueryResponse = {
  total_in_subset: number;
  candidates: Candidate[];
  chosen_dataset_id: string | null;
  suggested_chips: string[] | null;
  message: string | null;
};

const TIPO_VALUES: ChipTipo[] = ["Cuántos", "Comparar", "Ranking", "Tendencia", "Mapa"];

function isValidTipo(s: string | undefined | null): s is ChipTipo {
  return !!s && (TIPO_VALUES as string[]).includes(s);
}

type Props = {
  filters: Record<string, string[]>;
  subtags?: string[];
  refinador?: string;
  /** Aviso del mapper NL (p. ej. "marca tu municipio"). */
  hint?: string;
  /** Filtros de valor iniciales desde la URL (?filtro=col:valor). */
  initialValueFilters?: FilterSpec[];
};

const AXIS_LABEL: Record<string, string> = {
  tema: "Tema",
  tipo: "Tipo",
  territorio: "Territorio",
  entidad: "Entidad",
};

export function ChipsResultView({
  filters,
  subtags,
  refinador,
  hint,
  initialValueFilters,
}: Props) {
  const [data, setData] = useState<ChipsQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const sectionRef = useRef<HTMLElement | null>(null);

  // Fase C — ejecución del SoQL determinista sobre el dataset elegido.
  const [exec, setExec] = useState<ChipsExecuteResponse | null>(null);
  const [execError, setExecError] = useState<string | null>(null);
  const [execLoading, setExecLoading] = useState(false);
  const [showSoql, setShowSoql] = useState(false);

  // Filtros de VALOR sobre el dataset elegido (ADR-024, Fase 2). Los
  // disponibles salen del perfil de la bodega; los activos viven aquí y
  // se reflejan en la URL (?filtro=col:valor) para que el enlace comparta
  // el resultado filtrado.
  const [availableFilters, setAvailableFilters] = useState<FilterColumn[]>([]);
  const [valueFilters, setValueFilters] = useState<FilterSpec[]>(
    initialValueFilters ?? [],
  );

  // Fase D — narrativa LLM "Explicar" (opt-in por botón).
  const [explain, setExplain] = useState<ChipsExplainResponse | null>(null);
  const [explainLoading, setExplainLoading] = useState(false);

  // TIPO seleccionado por el usuario (de los chips capa 1).
  const tipo = useMemo<ChipTipo | null>(() => {
    const v = filters.tipo?.[0];
    return isValidTipo(v) ? v : null;
  }, [filters.tipo]);

  // COUNT(*) por defecto: si hay dataset elegido pero el usuario no marcó
  // TIPO, ejecutamos "Cuántos" — siempre hay una cifra que mostrar en vez de
  // tarjetas sin número (el conteo es la pregunta base de cualquier dataset).
  const tipoEfectivo: ChipTipo | null = tipo ?? "Cuántos";

  // Cuando cambia el resultado, resetear narrativa.
  useEffect(() => {
    setExplain(null);
  }, [exec?.dataset_id, exec?.tipo]);

  async function requestExplain() {
    if (!exec || !data?.chosen_dataset_id) return;
    const dsName =
      data.candidates.find((c) => c.dataset_id === exec.dataset_id)?.name ?? exec.dataset_id;
    setExplainLoading(true);
    setExplain(null);
    try {
      const res = await fetch("/api/chips/explain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset_id: exec.dataset_id,
          dataset_name: dsName,
          tipo: exec.tipo,
          rows: exec.rows,
          columns_used: exec.columns_used,
        }),
      });
      if (!res.ok) throw new Error(`Backend ${res.status}`);
      const json: ChipsExplainResponse = await res.json();
      setExplain(json);
    } catch (e) {
      setExplain({
        dataset_id: exec.dataset_id,
        tipo: exec.tipo,
        narrative: "",
        model: "unknown",
        error: e instanceof Error ? e.message : "Error",
      });
    } finally {
      setExplainLoading(false);
    }
  }

  // Filtros disponibles del dataset elegido (perfil de la bodega). Al
  // cambiar de dataset se limpian los filtros activos: los valores son
  // específicos de CADA dataset.
  const lastDatasetRef = useRef<string | null>(null);
  useEffect(() => {
    const dsId = data?.chosen_dataset_id;
    if (!dsId) {
      setAvailableFilters([]);
      return;
    }
    if (lastDatasetRef.current && lastDatasetRef.current !== dsId) {
      setValueFilters([]);
    }
    lastDatasetRef.current = dsId;
    let cancelled = false;
    fetch(`/api/datasets/${encodeURIComponent(dsId)}/filters`)
      .then((r) => (r.ok ? r.json() : null))
      .then((j: DatasetFiltersResponse | null) => {
        if (!cancelled) setAvailableFilters(j?.filtros ?? []);
      })
      .catch(() => {
        if (!cancelled) setAvailableFilters([]);
      });
    return () => {
      cancelled = true;
    };
  }, [data?.chosen_dataset_id]);

  // Toggle de filtro: uno por columna; click en el activo lo quita. La URL
  // se actualiza sin navegación (replaceState) para compartir el enlace.
  function toggleFilter(col: string, value: string) {
    setValueFilters((prev) => {
      const existing = prev.find((f) => f.col === col);
      let next: FilterSpec[];
      if (existing?.value === value) {
        next = prev.filter((f) => f.col !== col);
      } else {
        next = [...prev.filter((f) => f.col !== col), { col, value }];
      }
      const url = new URL(window.location.href);
      url.searchParams.delete("filtro");
      for (const f of next) url.searchParams.append("filtro", `${f.col}:${f.value}`);
      window.history.replaceState(null, "", url.toString());
      return next;
    });
  }

  // Auto-execute cuando hay dataset elegido; sin TIPO marcado degrada a
  // "Cuántos" (tipoEfectivo) para que siempre haya cifra, no tarjetas mudas.
  useEffect(() => {
    const dsId = data?.chosen_dataset_id;
    if (!dsId || !tipoEfectivo) {
      setExec(null);
      setExecError(null);
      return;
    }
    let cancelled = false;
    async function go() {
      setExecLoading(true);
      setExecError(null);
      try {
        const res = await fetch("/api/chips/execute", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            dataset_id: dsId,
            tipo: tipoEfectivo,
            filters: valueFilters.length > 0 ? valueFilters : null,
          }),
        });
        if (!res.ok) {
          const txt = await res.text();
          throw new Error(`Backend ${res.status}: ${txt}`);
        }
        const json: ChipsExecuteResponse = await res.json();
        if (!cancelled) setExec(json);
      } catch (e) {
        if (!cancelled) {
          setExecError(e instanceof Error ? e.message : "Error desconocido");
        }
      } finally {
        if (!cancelled) setExecLoading(false);
      }
    }
    go();
    return () => {
      cancelled = true;
    };
  }, [data?.chosen_dataset_id, tipoEfectivo, valueFilters]);

  // (Se eliminó el scrollIntoView automático: movía el viewport sin acción del
  // usuario — anti-patrón de accesibilidad WCAG 2.4.3. El orden del DOM ya pone
  // la respuesta arriba.)

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      // Convertir filters {tema:["X","Y"]} a payload single-value
      // (en Fase 1 cada chip es single-value desde la UI; multi se maneja
      // tomando el primer valor de cada axis. Multi-select se trata en Fase 2.)
      const body: Record<string, string | string[] | null> = {
        tema: filters.tema?.[0] ?? null,
        tipo: filters.tipo?.[0] ?? null,
        territorio: filters.territorio?.[0] ?? null,
        entidad: filters.entidad?.[0] ?? null,
        subtags: subtags && subtags.length > 0 ? subtags : null,
        refinador: refinador ?? null,
      };
      try {
        const res = await fetch("/api/chips", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!res.ok) {
          const txt = await res.text();
          throw new Error(`Backend ${res.status}: ${txt}`);
        }
        const json: ChipsQueryResponse = await res.json();
        if (!cancelled) setData(json);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Error desconocido");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [filters, subtags, refinador]);

  if (loading) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="py-8 text-ink-2 border-l-2 border-accent pl-4 animate-pulse"
      >
        Buscando datasets que coincidan con tus filtros…
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        className="rounded-[var(--radius-2)] border border-l-4 border-bad p-4 text-ink-2"
      >
        <strong className="text-bad">Error: </strong> {error}
      </div>
    );
  }

  if (!data) return null;

  return (
    <section ref={sectionRef} className="flex flex-col gap-6 scroll-mt-4">
      <header className="flex flex-col gap-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <span className="text-kicker">Resultado</span>
          <span className="font-mono text-caption text-ink-muted">
            {data.total_in_subset} dataset
            {data.total_in_subset !== 1 ? "s" : ""} relacionado
            {data.total_in_subset !== 1 ? "s" : ""}
          </span>
        </div>
        {hint ? (
          <p className="font-sans text-body text-warn leading-relaxed m-0">
            {hint}
          </p>
        ) : null}
        {data.message ? (
          <p className="font-sans text-body text-ink-2 leading-relaxed">
            {data.message}
            {data.suggested_chips && data.suggested_chips.length > 0 ? (
              <>
                {" "}
                <span className="text-ink-muted">
                  Sugerencia: marca también{" "}
                  {data.suggested_chips
                    .map((s) => AXIS_LABEL[s] ?? s)
                    .join(", ")}
                  .
                </span>
              </>
            ) : null}
          </p>
        ) : null}
      </header>

      {/* Fase C — render del resultado SoQL determinista cuando hay TIPO + dataset elegido. */}
      {tipo && data.chosen_dataset_id ? (
        <section
          aria-label="Resultado de la consulta"
          className="flex flex-col gap-3"
        >
          {availableFilters.length > 0 ? (
            <FilterBar
              filtros={availableFilters}
              active={valueFilters}
              onToggle={toggleFilter}
            />
          ) : null}
          {execLoading ? (
            <div
              role="status"
              aria-live="polite"
              className="surface-elev p-6 animate-pulse text-ink-2"
            >
              Calculando la cifra…
            </div>
          ) : execError ? (
            <div
              role="alert"
              className="rounded-[var(--radius-2)] border border-l-4 border-bad p-4 flex flex-col gap-1"
            >
              <span className="text-kicker text-bad">
                No pudimos calcular
              </span>
              <p className="font-sans text-body text-ink-2 m-0">
                {execError.includes("502") || execError.includes("SODA")
                  ? "El servidor de datos.gov.co no respondió a tiempo."
                  : execError}
              </p>
              <a
                href={
                  data.candidates.find(
                    (c) => c.dataset_id === data.chosen_dataset_id,
                  )?.url
                }
                target="_blank"
                rel="noreferrer"
                className="font-mono text-caption text-ink hover:underline mt-1"
              >
                Ver el dataset directo →
              </a>
            </div>
          ) : exec ? (
            <>
              <ChipsResultPanel
                response={exec}
                datasetName={
                  data.candidates.find(
                    (c) => c.dataset_id === data.chosen_dataset_id,
                  )?.name ?? exec.dataset_id
                }
              />
              {exec.filters_applied && exec.filters_applied.length > 0 ? (
                <p className="font-sans text-body text-ink-2 m-0">
                  Filtrado:{" "}
                  <strong className="text-ink">
                    {exec.filters_applied
                      .map((f) => `${f.col.replace(/_/g, " ")} = ${f.value}`)
                      .join(" · ")}
                  </strong>
                  {exec.unfiltered_total != null ? (
                    <span className="text-ink-muted">
                      {" "}
                      (de {exec.unfiltered_total.toLocaleString("es-CO")}{" "}
                      registros sin filtro)
                    </span>
                  ) : null}
                </p>
              ) : null}
              {exec.filter_note ? (
                <p className="font-sans text-caption text-warn m-0">
                  {exec.filter_note}
                </p>
              ) : null}
              <div className="flex items-center justify-between flex-wrap gap-2">
                <span className="font-mono text-caption text-ink-muted">
                  {exec.row_count} fila{exec.row_count !== 1 ? "s" : ""} ·
                  columnas usadas: {exec.columns_used.join(", ") || "(ninguna)"}
                </span>
                <button
                  type="button"
                  onClick={() => setShowSoql((v) => !v)}
                  className="font-mono text-caption text-ink hover:underline focus-ring"
                  aria-expanded={showSoql}
                >
                  {showSoql ? "Ocultar" : "Ver"} consulta SoQL
                </button>
              </div>
              {showSoql && exec.soql ? (
                <pre className="font-mono text-caption bg-bg-elev border border-hairline p-3 overflow-x-auto m-0">
                  {exec.soql}
                </pre>
              ) : null}

              {/* Fase D — Botón "Explicar" + narrativa */}
              <div className="flex items-center gap-3 flex-wrap pt-1">
                <button
                  type="button"
                  onClick={requestExplain}
                  disabled={explainLoading}
                  className="font-mono text-caption text-accent border border-accent rounded-[var(--radius-1)] px-3 py-1 hover:bg-accent hover:text-bg disabled:opacity-50 transition-colors focus-ring"
                >
                  {explainLoading
                    ? "Explicando…"
                    : explain
                    ? "Re-explicar"
                    : "Explicar esta cifra"}
                </button>
                {explain?.model ? (
                  <span className="font-mono text-caption text-ink-muted">
                    modelo: {explain.model}
                  </span>
                ) : null}
              </div>
              {explain?.narrative ? (
                <article className="surface-elev p-4">
                  <p className="font-sans text-body text-ink m-0 leading-relaxed">
                    {explain.narrative}
                  </p>
                </article>
              ) : null}
              {explain?.error ? (
                <div
                  role="alert"
                  className="rounded-[var(--radius-2)] border border-l-4 border-warn p-3 font-sans text-caption text-ink-2"
                >
                  No pude generar la explicación: {explain.error}
                  {explain.hallucinated_numbers &&
                  explain.hallucinated_numbers.length > 0 ? (
                    <>
                      {" "}
                      (cifras sospechosas:{" "}
                      <code className="font-mono">
                        {explain.hallucinated_numbers.join(", ")}
                      </code>
                      )
                    </>
                  ) : null}
                </div>
              ) : null}
            </>
          ) : null}
        </section>
      ) : null}

      {data.candidates.length === 0 ? (
        <p className="font-sans text-body text-ink-2">
          Ningún dataset coincide. Prueba quitar algún filtro o ampliar el
          territorio (por ejemplo, usar &quot;Nacional&quot;).
        </p>
      ) : (
        <CandidatesSection
          candidates={data.candidates}
          chosenId={data.chosen_dataset_id}
        />
      )}
    </section>
  );
}

/**
 * Presenta las fuentes: la elegida (de donde sale la cifra) prominente como
 * "Fuente", y las alternativas condensadas en un `<details>`. Cuando no hay
 * elegida (navegación sin TIPO), lista los datasets relacionados para explorar.
 */
function CandidatesSection({
  candidates,
  chosenId,
}: {
  candidates: Candidate[];
  chosenId: string | null;
}) {
  const chosen = chosenId
    ? candidates.find((c) => c.dataset_id === chosenId) ?? null
    : null;
  const others = chosen
    ? candidates.filter((c) => c.dataset_id !== chosen.dataset_id)
    : candidates;

  return (
    <div className="flex flex-col gap-3">
      <span className="text-kicker">{chosen ? "Fuente" : "Datasets relacionados"}</span>

      {chosen ? <CandidateCard c={chosen} chosen /> : null}

      {others.length > 0 ? (
        chosen ? (
          <details className="group">
            <summary className="cursor-pointer font-mono text-caption text-ink-2 hover:text-ink focus-ring">
              Ver otras {others.length} fuente{others.length !== 1 ? "s" : ""} relacionada
              {others.length !== 1 ? "s" : ""}
            </summary>
            <ul className="mt-3 flex flex-col gap-3 list-none p-0 m-0">
              {others.map((c) => (
                <li key={c.dataset_id}>
                  <CandidateCard c={c} />
                </li>
              ))}
            </ul>
          </details>
        ) : (
          <ul className="flex flex-col gap-3 list-none p-0 m-0">
            {others.map((c) => (
              <li key={c.dataset_id}>
                <CandidateCard c={c} />
              </li>
            ))}
          </ul>
        )
      ) : null}
    </div>
  );
}

function CandidateCard({ c, chosen = false }: { c: Candidate; chosen?: boolean }) {
  return (
    <article className={`surface-card p-4 ${chosen ? "border-accent" : ""}`}>
      <div className="flex justify-between items-start gap-3 flex-wrap">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {chosen ? (
              <span className="rounded-[var(--radius-1)] bg-accent text-bg font-sans text-[length:var(--type-kicker)] font-bold uppercase tracking-wide px-2 py-0.5">
                Fuente de la cifra
              </span>
            ) : null}
            {c.jurisdiccion_nivel ? (
              <span className="rounded-[var(--radius-1)] border border-hairline bg-bg-elev font-mono text-kicker text-ink-2 uppercase px-2 py-0.5">
                {c.jurisdiccion_nivel}
              </span>
            ) : null}
          </div>
          <h3 className="text-h4 m-0 mb-1">{c.name}</h3>
          <p className="font-sans text-caption text-ink-2 mb-2">
            {c.entity ?? "(sin entidad)"}
            {c.category ? ` · ${c.category}` : null}
          </p>
          <div className="font-mono text-caption text-ink-muted flex gap-3 flex-wrap">
            {c.row_count != null ? (
              <span>{c.row_count.toLocaleString("es-CO")} filas</span>
            ) : null}
            {c.last_updated ? (
              <span>actualizado {c.last_updated.slice(0, 10)}</span>
            ) : null}
          </div>
        </div>
        <a
          href={c.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 rounded-[var(--radius-1)] border border-accent px-3 py-1 font-sans text-body-sm font-semibold text-accent no-underline hover:bg-bg-overlay focus-ring"
        >
          Ver dataset <Icon name="external-link" size={12} aria-hidden />
        </a>
      </div>
    </article>
  );
}
