"use client";

import { Chip } from "@/components/Chip";

export type ChipOption = {
  value: string;
  label: string;
  count?: number;
};

export type Axis = "tema" | "tipo" | "territorio" | "entidad";

const KICKER_BY_AXIS: Record<Axis, string> = {
  tema: "Tema",
  tipo: "Tipo de pregunta",
  territorio: "Territorio",
  entidad: "Entidad",
};

type ChipGroupProps = {
  axis: Axis;
  options: ChipOption[];
  multi?: boolean;
  selected: string[];
  onChange: (selected: string[]) => void;
  description?: string;
};

/**
 * ChipGroup — grupo de chips bajo un eje (BRAND.md §8.3).
 *
 * Para `tipo` (Cuántos / Comparar / Ranking / Tendencia / Mapa): multi=false.
 * Para los otros tres ejes: multi=true.
 */
export function ChipGroup({
  axis,
  options,
  multi = true,
  selected,
  onChange,
  description,
}: ChipGroupProps) {
  function toggle(value: string) {
    if (multi) {
      onChange(
        selected.includes(value)
          ? selected.filter((v) => v !== value)
          : [...selected, value],
      );
    } else {
      onChange(selected.includes(value) ? [] : [value]);
    }
  }

  return (
    <fieldset className="border border-hairline rounded-[var(--radius-1)] bg-bg-elev/60 px-5 pt-4 pb-5 m-0">
      <legend className="text-kicker px-1.5">
        {KICKER_BY_AXIS[axis]}
      </legend>
      {description ? (
        <p className="font-sans text-caption text-ink-muted mb-3 -mt-1">
          {description}
        </p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        {options.length === 0 ? (
          <span className="font-sans text-caption text-ink-muted">
            Sin opciones disponibles.
          </span>
        ) : null}
        {options.map((opt) => (
          <Chip
            key={opt.value}
            label={opt.label}
            value={opt.value}
            count={opt.count}
            active={selected.includes(opt.value)}
            onToggle={toggle}
          />
        ))}
      </div>
    </fieldset>
  );
}
