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
    <fieldset className="border-0 m-0 p-0">
      <legend className="text-kicker mb-3 p-0">
        {KICKER_BY_AXIS[axis]}
        {description ? (
          <span className="ml-3 font-sans text-caption font-normal text-ink-muted normal-case tracking-normal">
            {description}
          </span>
        ) : null}
      </legend>
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
