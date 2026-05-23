"use client";

import { useEffect, useState } from "react";

import { Chip } from "@/components/Chip";

type SubtagOption = {
  value: string;
  label: string;
  count?: number | null;
};

type SubtagsBarProps = {
  tema: string | null;
  territorio: string | null;
  entidad: string | null;
  selected: string[];
  onChange: (selected: string[]) => void;
};

/**
 * Capa 2 de chips: sub-tags refinadores extraídos del subset filtrado por
 * los chips capa 1 (TEMA + TERRITORIO + ENTIDAD).
 *
 * Aparece solo si hay ≥1 chip capa 1 marcado. Hace fetch a /api/v1/chips/refine
 * cada vez que cambia la combinación de chips capa 1. Multi-select, opcional.
 *
 * Las selecciones se pasan al backend POST /api/v1/query/chips como
 * `subtags: string[]`. Intersection: el dataset debe matchear TODOS.
 */
export function SubtagsBar({
  tema,
  territorio,
  entidad,
  selected,
  onChange,
}: SubtagsBarProps) {
  const [options, setOptions] = useState<SubtagOption[]>([]);
  const [subsetTotal, setSubsetTotal] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  const hasAnyChip = Boolean(tema || territorio || entidad);

  useEffect(() => {
    if (!hasAnyChip) {
      setOptions([]);
      setSubsetTotal(null);
      return;
    }
    let cancelled = false;
    async function load() {
      setLoading(true);
      const params = new URLSearchParams();
      if (tema) params.set("tema", tema);
      if (territorio) params.set("territorio", territorio);
      if (entidad) params.set("entidad", entidad);
      try {
        const res = await fetch(`/api/chips/refine?${params.toString()}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) {
          setOptions(data.subtags ?? []);
          setSubsetTotal(data.subset_total ?? 0);
        }
      } catch {
        if (!cancelled) {
          setOptions([]);
          setSubsetTotal(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [tema, territorio, entidad, hasAnyChip]);

  // Limpiar selecciones cuyo tag ya no aparezca en options (cambió capa 1).
  useEffect(() => {
    if (options.length === 0 && selected.length > 0) {
      onChange([]);
      return;
    }
    const valid = new Set(options.map((o) => o.value));
    const filtered = selected.filter((s) => valid.has(s));
    if (filtered.length !== selected.length) onChange(filtered);
  }, [options, selected, onChange]);

  if (!hasAnyChip) return null;
  if (loading && options.length === 0) {
    return (
      <div className="text-caption text-ink-muted px-1 py-2">
        Buscando sub-temas del subset…
      </div>
    );
  }
  if (options.length === 0) return null;

  function toggle(value: string) {
    onChange(
      selected.includes(value)
        ? selected.filter((v) => v !== value)
        : [...selected, value],
    );
  }

  return (
    <fieldset className="border border-hairline rounded-[var(--radius-1)] bg-bg-elev/40 px-5 pt-4 pb-5 m-0">
      <legend className="text-kicker px-1.5">Refinar</legend>
      <p className="font-sans text-caption text-ink-muted mb-3 -mt-1">
        sub-temas reales del subset
        {subsetTotal !== null ? ` (${subsetTotal} datasets)` : null}
      </p>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => (
          <Chip
            key={opt.value}
            label={opt.label}
            value={opt.value}
            count={opt.count ?? undefined}
            active={selected.includes(opt.value)}
            onToggle={toggle}
          />
        ))}
      </div>
    </fieldset>
  );
}
