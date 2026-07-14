"use client";

import { useState } from "react";

import { HeroSearch } from "@/components/HeroSearch";
import { SpeechInput } from "@/components/SpeechInput";

/** Ejemplos clicables: al pulsarlos siembran la caja (no navegan directo), de
 *  modo que pasan por el mapper NL→chips al motor determinista como cualquier
 *  pregunta escrita. */
const EXAMPLES = [
  "¿Cuántos colegios públicos hay en Boyacá?",
  "¿Está subiendo o bajando el hurto de celulares en Colombia?",
  "¿Cuántos hurtos hubo en Boyacá en 2024?",
  "¿Cuánto cuesta el programa de alimentación escolar?",
];

/**
 * Panel de búsqueda de /buscar (antes vivía en la home; ADR-023 movió la
 * búsqueda al nivel 3 de la arquitectura de información).
 *
 * La caja de texto es lo primero y más prominente. El submit prioriza el
 * mapper NL→chips → motor determinista (ver `HeroSearch`). La voz es de
 * primera clase (visible, no escondida).
 */
export function SearchPanel() {
  const [seed, setSeed] = useState("");

  return (
    <section aria-label="Buscador principal" className="flex flex-col gap-4">
      <HeroSearch size="display" initialValue={seed} />

      <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <SpeechInput onTranscript={setSeed} />
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-caption text-ink-muted">Ejemplos:</span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => setSeed(ex)}
              className="rounded-[var(--radius-3)] border border-hairline bg-bg px-3 py-1.5 font-sans text-body-sm text-ink-2 hover:border-accent hover:text-ink transition-colors focus-ring"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
