"use client";

import { useMemo, useState } from "react";

import { ChipGroup, type Axis } from "@/components/ChipGroup";
import { HeroSearch } from "@/components/HeroSearch";
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

      <div className="flex flex-col gap-7">
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
    </section>
  );
}
