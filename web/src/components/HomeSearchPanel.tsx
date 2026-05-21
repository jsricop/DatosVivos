"use client";

import { useMemo, useState } from "react";

import { ChipGroup, type Axis } from "@/components/ChipGroup";
import { HeroSearch } from "@/components/HeroSearch";
import { QueryBuilderBar } from "@/components/QueryBuilderBar";
import { SpeechInput } from "@/components/SpeechInput";
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
  const [voiceQuery, setVoiceQuery] = useState("");

  const extraQuery = useMemo(() => {
    const q: Record<string, string[]> = {};
    for (const axis of Object.keys(selected) as Axis[]) {
      if (selected[axis].length > 0) q[axis] = selected[axis];
    }
    return q;
  }, [selected]);

  function update(axis: Axis, values: string[]) {
    setSelected((s) => ({ ...s, [axis]: values }));
  }

  function clearOne(axis: Axis, value: string) {
    setSelected((s) => ({
      ...s,
      [axis]: s[axis].filter((v) => v !== value),
    }));
  }

  return (
    <section aria-label="Buscador principal" className="flex flex-col gap-8">
      <div className="flex flex-col gap-4">
        <HeroSearch
          initialValue={voiceQuery}
          extraQuery={extraQuery}
          size="display"
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

      <div className="flex flex-col gap-3">
        <p className="font-sans text-caption text-ink-muted max-w-prose">
          O construye tu consulta con los filtros de abajo. Cada selección se
          va sumando a la barra inferior.
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
      </div>

      <QueryBuilderBar selected={selected} chips={chips} onClear={clearOne} />
    </section>
  );
}
