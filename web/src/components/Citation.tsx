type CitationProps = {
  index: number;
};

/**
 * Cita inline `[N]` (BRAND.md §8.13).
 *
 * Sup link al ancla #cita-N dentro de la lista de DatasetCitation
 * al pie de la página. Color var(--accent), sin subrayado; hover subrayado.
 */
export function Citation({ index }: CitationProps) {
  return (
    <sup>
      <a
        href={`#cita-${index}`}
        aria-label={`Ver fuente ${index}`}
        className="text-accent font-mono text-[0.75em] px-0.5 no-underline hover:underline focus-ring"
      >
        [{index}]
      </a>
    </sup>
  );
}
