"use client";

import type { FilterColumn, FilterSpec } from "@/lib/types";

/**
 * Chips de filtro de VALOR sobre el dataset elegido (ADR-024, Fase 2).
 *
 * Los valores salen del perfil de la bodega (`dataset_filter_values`):
 * son valores REALES del dato con su conteo — el ciudadano filtra
 * eligiendo, nunca escribiendo. Un filtro activo por columna; click en
 * el activo lo quita, click en otro valor de la misma columna lo
 * reemplaza.
 */

const MAX_COLS = 4;
const MAX_VALUES = 6;

function labelCol(f: FilterColumn): string {
  if (f.kind === "anio") return "Año";
  // snake_case / encabezados crudos → legible
  return f.col.replace(/_/g, " ").toLowerCase();
}

export function FilterBar({
  filtros,
  active,
  onToggle,
}: {
  filtros: FilterColumn[];
  active: FilterSpec[];
  onToggle: (col: string, value: string) => void;
}) {
  const cols = filtros.slice(0, MAX_COLS);
  if (cols.length === 0) return null;

  return (
    <section aria-label="Filtrar el resultado" className="flex flex-col gap-2">
      <span className="text-kicker">Filtra dentro del dataset</span>
      {cols.map((f) => {
        const activeValue = active.find((a) => a.col === f.col)?.value ?? null;
        // Los años vienen DESC del perfil; valores por conteo DESC.
        const values = f.values.slice(0, f.kind === "anio" ? 8 : MAX_VALUES);
        return (
          <div key={f.col} className="flex flex-wrap items-baseline gap-1.5">
            <span className="font-mono text-caption text-ink-muted uppercase tracking-wide min-w-[7ch]">
              {labelCol(f)}
            </span>
            {values.map((v) => {
              const isActive = activeValue === v.value;
              return (
                <button
                  key={v.value}
                  type="button"
                  onClick={() => onToggle(f.col, v.value)}
                  aria-pressed={isActive}
                  className={[
                    "rounded-[var(--radius-3)] border px-3 py-1 font-mono text-caption transition-colors focus-ring",
                    isActive
                      ? "border-accent bg-accent text-bg"
                      : "border-hairline bg-bg-elev text-ink-2 hover:border-accent",
                  ].join(" ")}
                >
                  {v.value}
                  {v.n != null ? (
                    <span className={isActive ? "opacity-80" : "text-ink-muted"}>
                      {" "}
                      · {v.n.toLocaleString("es-CO")}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>
        );
      })}
    </section>
  );
}
