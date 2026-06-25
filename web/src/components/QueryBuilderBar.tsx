"use client";

import { useRouter } from "next/navigation";
import { useMemo } from "react";

import { Icon } from "@/components/Icon";
import type { Axis } from "@/components/ChipGroup";
import type { SuggestOption } from "@/lib/types";

type ChipsByAxis = Record<Axis, SuggestOption[]>;
type SelectedByAxis = Record<Axis, string[]>;

type QueryBuilderBarProps = {
  selected: SelectedByAxis;
  chips: ChipsByAxis;
  subtags?: string[];
  onClear: (axis: Axis, value: string) => void;
  onClearSubtag?: (value: string) => void;
};

const AXIS_LABEL: Record<Axis, string> = {
  tema: "Tema",
  tipo: "Tipo",
  territorio: "Territorio",
  entidad: "Entidad",
};

const SUBTAG_AXIS_LABEL = "Sub-tema";

type FlatSelection =
  | { kind: "axis"; axis: Axis; value: string; label: string }
  | { kind: "subtag"; value: string };

function flatten(
  selected: SelectedByAxis,
  chips: ChipsByAxis,
  subtags: string[],
): FlatSelection[] {
  const out: FlatSelection[] = [];
  for (const axis of Object.keys(selected) as Axis[]) {
    for (const value of selected[axis]) {
      const opt = chips[axis]?.find((o) => o.value === value);
      out.push({ kind: "axis", axis, value, label: opt?.label ?? value });
    }
  }
  for (const value of subtags) {
    out.push({ kind: "subtag", value });
  }
  return out;
}

/**
 * QueryBuilderBar (BRAND.md §8.3-bis).
 *
 * Muestra al ciudadano la consulta que se está construyendo a partir
 * de los chips seleccionados — chips removibles + botón "Buscar".
 * Oculto si no hay nada seleccionado.
 */
export function QueryBuilderBar({
  selected,
  chips,
  subtags = [],
  onClear,
  onClearSubtag,
}: QueryBuilderBarProps) {
  const router = useRouter();
  const items = useMemo(
    () => flatten(selected, chips, subtags),
    [selected, chips, subtags],
  );

  if (items.length === 0) return null;

  function submit() {
    const params = new URLSearchParams();
    for (const axis of Object.keys(selected) as Axis[]) {
      for (const v of selected[axis]) {
        params.append(axis, v);
      }
    }
    for (const s of subtags) {
      params.append("subtag", s);
    }
    router.push(`/buscar?${params.toString()}`);
  }

  return (
    <aside
      role="status"
      aria-live="polite"
      aria-label="Consulta construida con filtros"
      className="sticky bottom-0 z-30 -mx-6 px-6 py-4 border-t-2 border-accent bg-bg-elev/95 backdrop-blur supports-[backdrop-filter]:bg-bg-elev/85 shadow-[0_-6px_18px_-12px_rgba(0,0,0,0.25)] flex flex-wrap items-center gap-3"
    >
      <span className="font-mono text-kicker text-ink-muted uppercase tracking-[0.08em] shrink-0">
        Tu consulta
      </span>
      <ul className="flex flex-wrap gap-2 flex-1 min-w-0 list-none p-0 m-0">
        {items.map((item) => {
          if (item.kind === "subtag") {
            return (
              <li key={`subtag:${item.value}`}>
                <button
                  type="button"
                  onClick={() => onClearSubtag?.(item.value)}
                  aria-label={`Quitar ${item.value} de Sub-tema`}
                  className="inline-flex items-center gap-1.5 rounded-[var(--radius-3)] border border-accent bg-bg px-3 py-1 font-sans text-caption text-ink hover:bg-bg-overlay focus-ring"
                >
                  <span className="font-mono text-[length:var(--type-kicker)] text-accent uppercase tracking-[0.08em]">
                    {SUBTAG_AXIS_LABEL}
                  </span>
                  <span>{item.value}</span>
                  <Icon name="close" size={12} aria-hidden />
                </button>
              </li>
            );
          }
          return (
            <li key={`${item.axis}:${item.value}`}>
              <button
                type="button"
                onClick={() => onClear(item.axis, item.value)}
                aria-label={`Quitar ${item.label} de ${AXIS_LABEL[item.axis]}`}
                className="inline-flex items-center gap-1.5 rounded-[var(--radius-3)] border border-hairline bg-bg px-3 py-1 font-sans text-caption text-ink hover:border-accent focus-ring"
              >
                <span className="font-mono text-[length:var(--type-kicker)] text-ink-muted uppercase tracking-[0.08em]">
                  {AXIS_LABEL[item.axis]}
                </span>
                <span>{item.label}</span>
                <Icon name="close" size={12} aria-hidden />
              </button>
            </li>
          );
        })}
      </ul>
      <button
        type="button"
        onClick={submit}
        className="inline-flex items-center gap-2 rounded-[var(--radius-1)] bg-accent text-bg px-5 py-2 font-sans text-body font-bold hover:bg-accent-2 transition-colors focus-ring"
      >
        <span>Buscar</span>
        <Icon name="arrow-right" size={16} aria-hidden />
      </button>
    </aside>
  );
}
