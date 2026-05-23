"use client";

import { useMemo, useState } from "react";

import { ChipGroup, type Axis } from "@/components/ChipGroup";
import { HeroSearch } from "@/components/HeroSearch";
import { QueryBuilderBar } from "@/components/QueryBuilderBar";
import { SpeechInput } from "@/components/SpeechInput";
import { SubtagsBar } from "@/components/SubtagsBar";
import type { SuggestOption } from "@/lib/types";

type ChipsByAxis = Record<Axis, SuggestOption[]>;

type HomeSearchPanelProps = {
  chips: ChipsByAxis;
};

const MULTI_SELECT: Record<Axis, boolean> = {
  tema: true,
  tipo: false,
  territorio: true,
  entidad: true,
};

const AXIS_HINT: Record<Axis, string> = {
  tema: "selecciona uno o varios sectores",
  tipo: "una sola forma de pregunta",
  territorio: "ámbito nacional o territorios específicos",
  entidad: "filtra por entidad publicadora",
};

export function HomeSearchPanel({ chips }: HomeSearchPanelProps) {
  const [selected, setSelected] = useState<Record<Axis, string[]>>({
    tema: [],
    tipo: [],
    territorio: [],
    entidad: [],
  });
  const [subtags, setSubtags] = useState<string[]>([]);
  const [voiceQuery, setVoiceQuery] = useState("");

  const extraQuery = useMemo(() => {
    const q: Record<string, string[]> = {};
    for (const axis of Object.keys(selected) as Axis[]) {
      if (selected[axis].length > 0) q[axis] = selected[axis];
    }
    if (subtags.length > 0) q.subtags = subtags;
    return q;
  }, [selected, subtags]);

  function update(axis: Axis, values: string[]) {
    setSelected((s) => ({ ...s, [axis]: values }));
  }

  function clearOne(axis: Axis, value: string) {
    setSelected((s) => ({
      ...s,
      [axis]: s[axis].filter((v) => v !== value),
    }));
  }

  function removeSubtag(value: string) {
    setSubtags((s) => s.filter((v) => v !== value));
  }

  return (
    <section aria-label="Buscador principal" className="flex flex-col gap-8">
      {/* PRIMARY: chips estructurados (Fase 1 audit top-down).
          La consulta se construye marcando chips de Tema/Tipo/Territorio/Entidad. */}
      <div className="flex flex-col gap-3">
        <div className="flex justify-between items-baseline flex-wrap gap-2">
          <h2 className="font-serif text-h3 m-0">Construí tu consulta</h2>
          <span className="font-mono text-caption text-ink-muted">
            marcá uno o varios filtros
          </span>
        </div>
        <p className="font-sans text-caption text-ink-muted max-w-prose">
          Elegí tema, tipo de pregunta, territorio y entidad. Cuando marques al
          menos un filtro, se habilita la búsqueda.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-5">
          {(Object.keys(chips) as Axis[]).map((axis) => (
            <ChipGroup
              key={axis}
              axis={axis}
              options={chips[axis] ?? []}
              multi={MULTI_SELECT[axis]}
              selected={selected[axis]}
              onChange={(v) => update(axis, v)}
              description={AXIS_HINT[axis]}
            />
          ))}
        </div>

        {/* Capa 2 — sub-tags refinadores del subset filtrado. Solo aparece
            si hay ≥1 chip capa 1 marcado. */}
        <SubtagsBar
          tema={selected.tema[0] ?? null}
          territorio={selected.territorio[0] ?? null}
          entidad={selected.entidad[0] ?? null}
          selected={subtags}
          onChange={setSubtags}
        />
      </div>

      <QueryBuilderBar
        selected={selected}
        chips={chips}
        subtags={subtags}
        onClear={clearOne}
        onClearSubtag={removeSubtag}
      />

      {/* SECONDARY: modo libre detrás de toggle. Durante el período de
          validación del paradigma chips, mantenemos la barra disponible para
          power users y comparación A/B. En Fase 2 vuelve como entrada con
          mapper NL→chips. */}
      <section aria-label="Modo libre (avanzado)" className="pt-6 hairline-top">
        <details>
          <summary className="cursor-pointer font-mono text-caption text-ink-2 hover:text-ink focus-ring">
            Modo libre (avanzado) — preguntar con texto libre
          </summary>
          <div className="mt-4 flex flex-col gap-3">
            <HeroSearch
              initialValue={voiceQuery}
              extraQuery={extraQuery}
              size="compact"
            />
            <div className="flex justify-between items-center flex-wrap gap-3">
              <span className="font-mono text-caption text-ink-muted">
                Pulsa{" "}
                <kbd className="inline-block border border-hairline-strong px-1.5 py-px font-mono text-[length:var(--type-kicker)] bg-bg-elev text-ink-2">
                  /
                </kbd>{" "}
                para enfocar el buscador
              </span>
              <SpeechInput onTranscript={setVoiceQuery} />
            </div>
          </div>
        </details>
      </section>
    </section>
  );
}
