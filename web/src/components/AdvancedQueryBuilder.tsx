"use client";

import { useState } from "react";

import { ChipGroup, type Axis } from "@/components/ChipGroup";
import { QueryBuilderBar } from "@/components/QueryBuilderBar";
import { SubtagsBar } from "@/components/SubtagsBar";
import type { SuggestOption } from "@/lib/types";

type ChipsByAxis = Record<Axis, SuggestOption[]>;

type AdvancedQueryBuilderProps = {
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

/**
 * Constructor avanzado de consultas con chips (Tema/Tipo/Territorio/Entidad).
 *
 * En la versión final es la entrada SECUNDARIA (power users): vive colapsado en
 * un `<details>` al pie de la home. La entrada primaria es el lenguaje natural
 * (`HomeSearchPanel`/`HeroSearch`). El motor determinista de chips se conserva
 * intacto — solo cambia su jerarquía visual.
 */
export function AdvancedQueryBuilder({ chips }: AdvancedQueryBuilderProps) {
  const [selected, setSelected] = useState<Record<Axis, string[]>>({
    tema: [],
    tipo: [],
    territorio: [],
    entidad: [],
  });
  const [subtags, setSubtags] = useState<string[]>([]);

  function update(axis: Axis, values: string[]) {
    setSelected((s) => ({ ...s, [axis]: values }));
  }

  function clearOne(axis: Axis, value: string) {
    setSelected((s) => ({ ...s, [axis]: s[axis].filter((v) => v !== value) }));
  }

  function removeSubtag(value: string) {
    setSubtags((s) => s.filter((v) => v !== value));
  }

  return (
    <section aria-label="Consulta avanzada con filtros" className="hairline-top pt-6">
      <details className="group">
        <summary className="cursor-pointer font-mono text-caption text-ink-2 hover:text-ink focus-ring">
          Construye una consulta avanzada con filtros
        </summary>

        <div className="mt-5 flex flex-col gap-5">
          <p className="font-sans text-caption text-ink-muted max-w-prose m-0">
            Marca tema, tipo de pregunta, territorio y entidad. La respuesta se
            calcula con un motor determinista sobre el catálogo, sin IA.
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

          <SubtagsBar
            tema={selected.tema[0] ?? null}
            territorio={selected.territorio[0] ?? null}
            entidad={selected.entidad[0] ?? null}
            selected={subtags}
            onChange={setSubtags}
          />
        </div>
      </details>

      <QueryBuilderBar
        selected={selected}
        chips={chips}
        subtags={subtags}
        onClear={clearOne}
        onClearSubtag={removeSubtag}
      />
    </section>
  );
}
