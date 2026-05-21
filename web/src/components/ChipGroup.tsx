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
 * Para `tipo` (Cuántos / Comparar / Ranking / Tendencia / Mapa): `multi=false`.
 * Para los otros tres ejes: `multi=true`.
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
    <fieldset
      style={{
        border: "none",
        margin: 0,
        padding: 0,
      }}
    >
      <legend
        className="kicker"
        style={{
          marginBottom: 12,
          padding: 0,
        }}
      >
        {KICKER_BY_AXIS[axis]}
        {description ? (
          <span
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: "var(--type-caption)",
              fontWeight: 400,
              textTransform: "none",
              letterSpacing: 0,
              color: "var(--ink-muted)",
              marginLeft: 12,
            }}
          >
            {description}
          </span>
        ) : null}
      </legend>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        {options.length === 0 ? (
          <span
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: "var(--type-caption)",
              color: "var(--ink-muted)",
            }}
          >
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
