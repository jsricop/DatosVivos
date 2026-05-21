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
    <section
      aria-label="Buscador principal"
      style={{ display: "flex", flexDirection: "column", gap: 32 }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <HeroSearch
          initialValue={voiceQuery}
          extraQuery={extraQuery}
          size="display"
        />
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 12,
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "var(--type-caption)",
              color: "var(--ink-muted)",
            }}
          >
            Pulsa <kbd style={kbdStyle}>/</kbd> para enfocar el buscador
          </span>
          <SpeechInput onTranscript={setVoiceQuery} />
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
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

const kbdStyle: React.CSSProperties = {
  display: "inline-block",
  border: "1px solid var(--hairline-strong)",
  padding: "1px 6px",
  fontFamily: "var(--font-mono)",
  fontSize: "var(--type-kicker)",
  background: "var(--bg-elev)",
  color: "var(--ink-2)",
};
