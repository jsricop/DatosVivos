type CitationProps = {
  index: number;
};

/**
 * Cita inline `[N]` (BRAND.md §8.13).
 *
 * Renderiza un sup link al ancla `#cita-N` dentro de la lista de DatasetCitation
 * al pie de la página. Color var(--accent), sin subrayado; hover subrayado.
 */
export function Citation({ index }: CitationProps) {
  return (
    <sup>
      <a
        href={`#cita-${index}`}
        aria-label={`Ver fuente ${index}`}
        style={{
          color: "var(--accent)",
          fontFamily: "var(--font-mono)",
          fontSize: "0.75em",
          paddingInline: 2,
          textDecoration: "none",
        }}
      >
        [{index}]
      </a>
    </sup>
  );
}
