/**
 * Iconos SVG inline del sistema (BRAND.md §11: cero emojis en código UI).
 * currentColor: heredan el color del texto que acompañan (text-ok, text-warn…).
 */

const base = {
  width: 12,
  height: 12,
  viewBox: "0 0 16 16",
  "aria-hidden": true as const,
  focusable: false as const,
  className: "inline-block shrink-0",
};

/** Chequecito de verificación (reemplaza el check U+2713). */
export function CheckIcon() {
  return (
    <svg {...base}>
      <path
        d="M2.5 8.5 6.5 12.5 13.5 3.5"
        stroke="currentColor"
        strokeWidth="2.4"
        fill="none"
        strokeLinecap="square"
      />
    </svg>
  );
}

/** Triángulo de advertencia (reemplaza el warning U+26A0). */
export function WarnIcon() {
  return (
    <svg {...base}>
      <path d="M8 1.5 15 14H1Z" stroke="currentColor" strokeWidth="1.6" fill="none" />
      <path d="M8 6v4" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="8" cy="12.2" r="0.9" fill="currentColor" />
    </svg>
  );
}

/** Destello de IA (reemplaza la estrella U+2726). */
export function SparkIcon() {
  return (
    <svg {...base}>
      <path d="M8 1.5 9.8 6.2 14.5 8 9.8 9.8 8 14.5 6.2 9.8 1.5 8 6.2 6.2Z" fill="currentColor" />
    </svg>
  );
}
