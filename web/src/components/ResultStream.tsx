"use client";

import { useEffect, useRef, useState } from "react";

import { DashboardRenderer } from "@/components/dashboard/DashboardRenderer";
import { DatasetCitation } from "@/components/DatasetCitation";
import { DataTable } from "@/components/DataTable";
import { DisclaimerBeta } from "@/components/DisclaimerBeta";
import { Icon } from "@/components/Icon";
import { NarrativeBlock } from "@/components/NarrativeBlock";
import { SpeechOutput } from "@/components/SpeechOutput";
import {
  type DashboardSpec,
  parseDashboardSpec,
} from "@/lib/schemas/dashboard";
import type {
  DatasetCitation as Citation_,
  Row,
} from "@/lib/types";

type ResultStreamProps = {
  question: string;
  /** Si se pasa, restringe la consulta con los filtros seleccionados. */
  filters?: Record<string, string[] | string>;
};

type State = {
  intent?: string;
  intentConfidence?: number;
  datasets: Array<{ id: string; name: string; entity?: string | null; score: number }>;
  /** Resumen corto (2-3 frases, llega primero, TTFB ≤ 1s). */
  narrativeSummary: string;
  /** Narrativa extendida (con bloque verificado al cierre). */
  narrative: string;
  /** True cuando llegó el evento `narrative_chunk_summary` con `done=true`. */
  summaryComplete: boolean;
  /** True cuando llegó el evento `narrative_chunk_extended` con `done=true`. */
  extendedComplete: boolean;
  /** True si el backend emitió al menos un `narrative_chunk_extended`. En ese
   *  caso ignoramos el legacy `narrative_chunk` para evitar duplicación. */
  hasExtendedEvents: boolean;
  rows: Row[];
  rowCount: number;
  columns: string[];
  soql: string;
  citations: Citation_[];
  dashboardSpec: DashboardSpec | null;
  status: "idle" | "streaming" | "done" | "error";
  elapsed?: number;
  errorMessage?: string;
};

const INTENT_LABEL: Record<string, string> = {
  search: "Catálogo",
  descriptive: "Descripción",
  comparative: "Comparativa",
  temporal: "Tendencia",
  cross_source: "Cruce multi-fuente",
};

/**
 * Consume el endpoint SSE /api/proxy/query y renderiza la respuesta
 * incrementalmente. Cada evento del backend (ADR-013 + PLAN_DASHBOARD §2)
 * actualiza el estado.
 */
export function ResultStream({ question, filters }: ResultStreamProps) {
  const [state, setState] = useState<State>({
    datasets: [],
    narrativeSummary: "",
    narrative: "",
    summaryComplete: false,
    extendedComplete: false,
    hasExtendedEvents: false,
    rows: [],
    rowCount: 0,
    columns: [],
    soql: "",
    citations: [],
    dashboardSpec: null,
    status: "idle",
  });
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    abortRef.current?.abort();
    if (!question) return;
    const controller = new AbortController();
    abortRef.current = controller;

    setState({
      datasets: [],
      narrativeSummary: "",
      narrative: "",
      summaryComplete: false,
      extendedComplete: false,
      hasExtendedEvents: false,
      rows: [],
      rowCount: 0,
      columns: [],
      soql: "",
      citations: [],
      dashboardSpec: null,
      status: "streaming",
    });

    (async () => {
      try {
        // Fetch DIRECTO a /api/v1/* — nginx tiene location específica con
        // `proxy_buffering off` y `proxy_read_timeout 300s` (ADR-013). El
        // route handler /api/query intermedio caía en location `/` genérica
        // con timeout 60s y además tenía bug ReadableStream locked en cancel.
        const res = await fetch("/api/v1/query", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify({ q: question, filters: filters ?? {} }),
          signal: controller.signal,
        });
        if (!res.ok || !res.body) {
          setState((s) => ({
            ...s,
            status: "error",
            errorMessage: `Backend respondió ${res.status}`,
          }));
          return;
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let currentEvent: string | null = null;

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";
          for (const rawLine of lines) {
            const line = rawLine.trimEnd();
            if (!line) {
              currentEvent = null;
              continue;
            }
            if (line.startsWith("event:")) {
              currentEvent = line.slice(6).trim();
              continue;
            }
            if (line.startsWith("data:") && currentEvent) {
              const payloadRaw = line.slice(5).trim();
              try {
                const payload = JSON.parse(payloadRaw);
                applyEvent(setState, currentEvent, payload);
              } catch {
                /* ignore malformed JSON */
              }
            }
          }
        }
        setState((s) =>
          s.status === "streaming" ? { ...s, status: "done" } : s,
        );
      } catch (err) {
        if (controller.signal.aborted) return;
        setState((s) => ({
          ...s,
          status: "error",
          errorMessage: err instanceof Error ? err.message : "Error de red",
        }));
      }
    })();

    return () => controller.abort();
  }, [question, filters]);

  const isLoading = state.status === "streaming";

  return (
    <article className="flex flex-col gap-8" aria-live="polite">
      {state.intent ? (
        <header className="flex flex-wrap items-baseline justify-between gap-4 pb-3 hairline-bottom">
          <span className="text-kicker">
            {INTENT_LABEL[state.intent] ?? state.intent}
            {state.datasets[0]?.entity ? ` · ${state.datasets[0].entity}` : null}
          </span>
          {state.elapsed ? (
            <span className="font-mono text-[length:var(--type-kicker)] text-ink-muted [font-variant-numeric:tabular-nums]">
              {state.elapsed.toFixed(1)} s
            </span>
          ) : null}
        </header>
      ) : null}

      {isLoading && !state.narrative ? (
        <p className="font-mono text-caption text-ink-2">
          Procesando consulta {state.intent ? `(${state.intent})` : ""}…
        </p>
      ) : null}

      {state.narrativeSummary || state.narrative ? (
        <section className="measure">
          <NarrativeBlock
            summary={state.narrativeSummary || state.narrative}
            extended={state.narrative}
            summaryComplete={state.summaryComplete}
            extendedComplete={state.extendedComplete}
            citationCount={state.citations.length}
          />
          <div className="mt-3">
            <SpeechOutput
              text={state.narrative || state.narrativeSummary}
            />
          </div>
        </section>
      ) : null}

      {state.dashboardSpec ? (
        <DashboardRenderer
          spec={state.dashboardSpec}
          rows={state.rows as Record<string, unknown>[]}
        />
      ) : null}

      {state.soql ? (
        <section className="surface-elev p-4">
          <div className="flex items-center justify-between gap-4 mb-2">
            <span className="text-kicker">SoQL ejecutado</span>
            <button
              type="button"
              onClick={() => navigator.clipboard.writeText(state.soql)}
              aria-label="Copiar SoQL"
              className="inline-flex items-center gap-1.5 border border-hairline-strong px-2.5 py-1 font-mono text-[length:var(--type-kicker)] uppercase tracking-[0.08em] text-ink hover:bg-bg focus-ring"
            >
              <Icon name="copy" size={12} aria-hidden />
              <span>Copiar</span>
            </button>
          </div>
          <pre className="font-mono text-mono text-ink overflow-auto m-0 whitespace-pre-wrap">
            {state.soql}
          </pre>
        </section>
      ) : null}

      {state.rows.length > 0 ? (
        <section className="mt-3">
          <details>
            <summary>
              Ver tabla cruda ({state.rowCount.toLocaleString("es-CO")} filas)
            </summary>
            <div className="mt-4">
              <DataTable
                columns={state.columns}
                rows={state.rows}
                downloadFilename="datosvivos-rows.csv"
              />
            </div>
          </details>
        </section>
      ) : null}

      {state.citations.length > 0 ? (
        <section>
          <h2 className="text-kicker mb-4">Fuentes consultadas</h2>
          <ol className="list-none">
            {state.citations.map((c) => (
              <DatasetCitation key={c.index} citation={c} />
            ))}
          </ol>
        </section>
      ) : null}

      {state.status === "error" ? (
        <p
          role="alert"
          className="inline-flex items-center gap-2 font-mono text-body-sm text-danger"
        >
          <Icon name="close" size={16} aria-hidden />
          {state.errorMessage ?? "Error procesando la consulta"}
        </p>
      ) : null}

      <DisclaimerBeta variant="footer" />
    </article>
  );
}

function applyEvent(
  setState: (updater: (s: State) => State) => void,
  event: string,
  payload: Record<string, unknown>,
) {
  setState((s) => {
    switch (event) {
      case "intent":
        return {
          ...s,
          intent: payload.intent as string,
          intentConfidence: (payload.confidence as number) ?? 0,
        };
      case "dataset_hits":
        return { ...s, datasets: (payload.datasets as State["datasets"]) ?? [] };
      case "soql":
        return { ...s, soql: (payload.soql as string) ?? "" };
      case "narrative_chunk":
        // Legacy event (ADR-013). Si el backend ya emitió narrative_chunk_extended
        // ignoramos esto para evitar duplicación.
        if (s.hasExtendedEvents) return s;
        return { ...s, narrative: s.narrative + ((payload.text as string) ?? "") };
      case "narrative_chunk_summary": {
        const text = (payload.text as string) ?? "";
        const done = Boolean(payload.done);
        return {
          ...s,
          narrativeSummary: s.narrativeSummary + text,
          summaryComplete: s.summaryComplete || done,
        };
      }
      case "narrative_chunk_extended": {
        const text = (payload.text as string) ?? "";
        const done = Boolean(payload.done);
        return {
          ...s,
          narrative: s.narrative + text,
          extendedComplete: s.extendedComplete || done,
          hasExtendedEvents: true,
        };
      }
      case "narrative_correction": {
        // Reemplazo total del extended (el validador censuró cifras).
        return { ...s, narrative: (payload.text as string) ?? s.narrative };
      }
      case "rows":
        return {
          ...s,
          rowCount: (payload.count as number) ?? 0,
          columns: (payload.columns as string[]) ?? s.columns,
          rows: (payload.preview as Row[]) ?? [],
        };
      case "citations":
        return { ...s, citations: (payload.citations as State["citations"]) ?? [] };
      case "dashboard_spec": {
        const parsed = parseDashboardSpec(payload);
        return { ...s, dashboardSpec: parsed };
      }
      case "error":
        return {
          ...s,
          status: "error",
          errorMessage: (payload.message as string) ?? "Error procesando la consulta",
        };
      case "done":
        return {
          ...s,
          status: "done",
          elapsed: (payload.elapsed_s as number) ?? undefined,
        };
      default:
        return s;
    }
  });
}

