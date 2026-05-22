"use client";

import type { ReactNode } from "react";

import { Citation } from "@/components/Citation";

type NarrativeBlockProps = {
  /** Resumen corto (2-3 frases). Llega primero, TTFB ≤ 1s. */
  summary: string;
  /** Narrativa extendida (incluye bloque "Datos verificados" al cierre). */
  extended: string;
  /** True cuando el summary terminó de streamear. */
  summaryComplete: boolean;
  /** True cuando el extended terminó de streamear. */
  extendedComplete: boolean;
  /** Cantidad de fuentes citables (para validar referencias `[1]`, `[2]`). */
  citationCount: number;
};

/**
 * NarrativeBlock (BRAND.md §8.x, ADR-016).
 *
 * Render del resumen narrativo + opcional `<details>` con la versión
 * extendida. El summary aparece apenas llega del SSE (TTFB ≤ 1s); el
 * extended (con datos verificados al cierre) se muestra al expandir.
 *
 * Accesibilidad:
 * - `aria-live="polite"` en el container externo (sin sobre-anuncios).
 * - `<details>` nativo (focus-visible, keyboard, SR friendly).
 * - Mientras el extended está cargando pero el summary terminó, mostrar
 *   indicador sutil "Cargando detalle…".
 */
export function NarrativeBlock({
  summary,
  extended,
  summaryComplete,
  extendedComplete,
  citationCount,
}: NarrativeBlockProps) {
  // Si no hay summary aún, no renderizamos nada (estado de "Procesando…" lo
  // maneja el parent).
  if (!summary) return null;

  const extendedReady = extended.trim().length > summary.trim().length + 20;
  const showExtendedLoader = summaryComplete && !extendedComplete && !extended;

  return (
    <div className="flex flex-col gap-4">
      {/* Summary: siempre visible. */}
      <p className="font-serif text-body-lg leading-[1.7] text-ink">
        {renderWithCitations(summary, citationCount)}
      </p>

      {/* Indicador de carga del extended. */}
      {showExtendedLoader ? (
        <p className="font-mono text-caption text-ink-muted">
          Cargando análisis detallado…
        </p>
      ) : null}

      {/* Extended en <details> cuando hay contenido suficiente. */}
      {extendedReady ? (
        <details className="border-t border-hairline pt-3 mt-1 group">
          <summary className="cursor-pointer list-none flex items-baseline gap-2 font-mono text-kicker text-ink-2 hover:text-ink focus-ring">
            <span aria-hidden="true" className="group-open:rotate-90 inline-block transition-transform">
              ▸
            </span>
            <span>Ver respuesta completa con datos verificados</span>
          </summary>
          <div className="mt-4 font-serif text-body-lg leading-[1.7] text-ink whitespace-pre-line">
            {renderWithCitations(extended, citationCount)}
          </div>
        </details>
      ) : null}
    </div>
  );
}

const CITATION_REGEX = /\[(\d+)\]/g;

function renderWithCitations(text: string, maxCitations: number): ReactNode {
  const parts: Array<string | { citationIndex: number }> = [];
  let cursor = 0;
  for (const match of text.matchAll(CITATION_REGEX)) {
    const start = match.index ?? 0;
    if (start > cursor) parts.push(text.slice(cursor, start));
    const idx = Number(match[1]);
    if (idx > 0 && idx <= maxCitations) {
      parts.push({ citationIndex: idx });
    } else {
      parts.push(match[0] ?? "");
    }
    cursor = start + (match[0]?.length ?? 0);
  }
  if (cursor < text.length) parts.push(text.slice(cursor));
  return parts.map((p, i) =>
    typeof p === "string" ? (
      <span key={i}>{p}</span>
    ) : (
      <Citation key={i} index={p.citationIndex} />
    ),
  );
}
