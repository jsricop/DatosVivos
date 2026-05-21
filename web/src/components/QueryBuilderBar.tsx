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
  onClear: (axis: Axis, value: string) => void;
};

const AXIS_LABEL: Record<Axis, string> = {
  tema: "Tema",
  tipo: "Tipo",
  territorio: "Territorio",
  entidad: "Entidad",
};

type FlatSelection = {
  axis: Axis;
  value: string;
  label: string;
};

function flatten(
  selected: SelectedByAxis,
  chips: ChipsByAxis,
): FlatSelection[] {
  const out: FlatSelection[] = [];
  for (const axis of Object.keys(selected) as Axis[]) {
    for (const value of selected[axis]) {
      const opt = chips[axis]?.find((o) => o.value === value);
      out.push({ axis, value, label: opt?.label ?? value });
    }
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
  onClear,
}: QueryBuilderBarProps) {
  const router = useRouter();
  const items = useMemo(() => flatten(selected, chips), [selected, chips]);

  if (items.length === 0) return null;

  function submit() {
    const params = new URLSearchParams();
    for (const axis of Object.keys(selected) as Axis[]) {
      for (const v of selected[axis]) {
        params.append(axis, v);
      }
    }
    router.push(`/buscar?${params.toString()}`);
  }

  return (
    <aside
      role="status"
      aria-live="polite"
      aria-label="Consulta construida con filtros"
      className="border-t border-hairline-strong bg-bg-elev px-6 py-4 flex flex-wrap items-center gap-3"
    >
      <span className="font-mono text-kicker text-ink-muted uppercase tracking-[0.08em] shrink-0">
        Tu consulta
      </span>
      <ul className="flex flex-wrap gap-2 flex-1 min-w-0 list-none p-0 m-0">
        {items.map((item) => (
          <li key={`${item.axis}:${item.value}`}>
            <button
              type="button"
              onClick={() => onClear(item.axis, item.value)}
              aria-label={`Quitar ${item.label} de ${AXIS_LABEL[item.axis]}`}
              className="inline-flex items-center gap-1.5 border border-hairline-strong bg-bg px-2.5 py-1 font-sans text-caption text-ink hover:bg-bg-elev focus-ring"
            >
              <span className="font-mono text-[length:var(--type-kicker)] text-ink-muted uppercase tracking-[0.08em]">
                {AXIS_LABEL[item.axis]}
              </span>
              <span>{item.label}</span>
              <Icon name="close" size={12} aria-hidden />
            </button>
          </li>
        ))}
      </ul>
      <button
        type="button"
        onClick={submit}
        className="inline-flex items-center gap-2 bg-ink text-bg px-4 py-2 font-sans text-body font-semibold focus-ring"
      >
        <span>Buscar</span>
        <Icon name="arrow-right" size={16} aria-hidden />
      </button>
    </aside>
  );
}
