"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon";

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

type Props = {
  filters: Record<string, string[]>;
  refinador?: string;
};

const AXIS_LABEL: Record<string, string> = {
  tema: "Tema",
  tipo: "Tipo",
  territorio: "Territorio",
  entidad: "Entidad",
};

export function ChipsResultView({ filters, refinador }: Props) {
  const [data, setData] = useState<ChipsQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      // Convertir filters {tema:["X","Y"]} a payload single-value
      // (en Fase 1 cada chip es single-value desde la UI; multi se maneja
      // tomando el primer valor de cada axis. Multi-select se trata en Fase 2.)
      const body: Record<string, string | null> = {
        tema: filters.tema?.[0] ?? null,
        tipo: filters.tipo?.[0] ?? null,
        territorio: filters.territorio?.[0] ?? null,
        entidad: filters.entidad?.[0] ?? null,
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
  }, [filters, refinador]);

  if (loading) {
    return (
      <div role="status" aria-live="polite" className="py-8 text-ink-2">
        Buscando datasets que coincidan con tus filtros…
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" className="py-6 text-red-700 border border-red-200 bg-red-50 p-4">
        <strong>Error: </strong> {error}
      </div>
    );
  }

  if (!data) return null;

  return (
    <section className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <span className="text-kicker">Resultado</span>
          <span className="font-mono text-caption text-ink-muted">
            {data.total_in_subset} dataset
            {data.total_in_subset !== 1 ? "s" : ""} en el subset
          </span>
        </div>
        {data.message ? (
          <p className="font-sans text-body text-ink-2 leading-relaxed">
            {data.message}
            {data.suggested_chips && data.suggested_chips.length > 0 ? (
              <>
                {" "}
                <span className="text-ink-muted">
                  Sugerencia: marcá también{" "}
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

      {data.candidates.length === 0 ? (
        <p className="font-sans text-body text-ink-2">
          Ningún dataset coincide. Probá quitar algún chip o ampliar el
          territorio (ej. usar &quot;Nacional&quot;).
        </p>
      ) : (
        <ul className="flex flex-col gap-3 list-none p-0 m-0">
          {data.candidates.map((c, i) => (
            <li
              key={c.dataset_id}
              className={`border border-hairline-strong p-4 ${
                c.dataset_id === data.chosen_dataset_id
                  ? "bg-bg-elev ring-2 ring-ink"
                  : "bg-bg"
              }`}
            >
              <div className="flex justify-between items-start gap-3 flex-wrap">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-kicker text-ink-muted">
                      #{i + 1}
                    </span>
                    {c.dataset_id === data.chosen_dataset_id ? (
                      <span className="font-mono text-kicker bg-ink text-bg px-1.5 py-0.5">
                        ELEGIDO
                      </span>
                    ) : null}
                    {c.jurisdiccion_nivel ? (
                      <span className="font-mono text-kicker text-ink-2 uppercase">
                        {c.jurisdiccion_nivel}
                      </span>
                    ) : null}
                  </div>
                  <h3 className="font-serif text-h4 m-0 mb-1">{c.name}</h3>
                  <p className="font-sans text-caption text-ink-2 mb-2">
                    {c.entity ?? "(sin entidad)"}
                    {c.category ? ` · ${c.category}` : null}
                  </p>
                  <div className="font-mono text-caption text-ink-muted flex gap-3 flex-wrap">
                    {c.row_count != null ? (
                      <span>{c.row_count.toLocaleString("es-CO")} filas</span>
                    ) : null}
                    {c.view_count != null ? (
                      <span>{c.view_count.toLocaleString("es-CO")} vistas</span>
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
                  className="inline-flex items-center gap-1 font-mono text-caption text-ink hover:underline focus-ring"
                >
                  Ver fuente <Icon name="external-link" size={12} aria-hidden />
                </a>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
