/**
 * Patrones SVG y stroke-dasharray para diferenciar series sin depender solo del color.
 *
 * Motivación (BRAND.md §8.9 + WCAG 1.4.1 "Use of Color"): el color no puede
 * ser el único canal de información. Para usuarios con daltonismo o en modo
 * alto contraste, las series se distinguen también por textura (barras) o
 * por patrón de trazo (líneas).
 *
 * - `<ChartPatternDefs id="dv">` se renderiza una vez dentro del `<svg>` y
 *   expone los 5 patterns como `#dv-pattern-0..4`. Aplícalos como overlay
 *   sobre el color sólido: render dos shapes superpuestos.
 * - `dashArray(i)` devuelve el `stroke-dasharray` cíclico para LinePath.
 */

import type { ReactNode } from "react";

export const PATTERN_COUNT = 5;

const PATTERNS: Array<ReactNode> = [
  // 0: sólido (sin overlay decorativo)
  null,
  // 1: rayas diagonales / — más visibles para HC
  <line
    key="p1"
    x1={0}
    y1={0}
    x2={0}
    y2={8}
    stroke="currentColor"
    strokeWidth={1.5}
    strokeOpacity={0.75}
  />,
  // 2: rayas inversas \
  <line
    key="p2"
    x1={0}
    y1={0}
    x2={0}
    y2={8}
    stroke="currentColor"
    strokeWidth={1.5}
    strokeOpacity={0.75}
  />,
  // 3: cuadrícula fina
  <g key="p3">
    <line x1={0} y1={0} x2={8} y2={0} stroke="currentColor" strokeWidth={0.8} strokeOpacity={0.7} />
    <line x1={0} y1={0} x2={0} y2={8} stroke="currentColor" strokeWidth={0.8} strokeOpacity={0.7} />
  </g>,
  // 4: puntos
  <circle key="p4" cx={2} cy={2} r={1.4} fill="currentColor" fillOpacity={0.8} />,
];

const PATTERN_TRANSFORM = ["", "rotate(45)", "rotate(-45)", "", ""];

type DefsProps = { id: string; color?: string };

export function ChartPatternDefs({ id, color = "var(--ink)" }: DefsProps) {
  return (
    <defs>
      {PATTERNS.map((shape, i) => {
        if (!shape) return null;
        return (
          <pattern
            key={i}
            id={`${id}-pattern-${i}`}
            width={i === 4 ? 6 : 8}
            height={i === 4 ? 6 : 8}
            patternUnits="userSpaceOnUse"
            patternTransform={PATTERN_TRANSFORM[i]}
            style={{ color }}
          >
            {shape}
          </pattern>
        );
      })}
    </defs>
  );
}

/**
 * Devuelve la URL del pattern para serie `seriesIndex`. Si el pattern es
 * `null` (serie 0), devuelve `undefined` para que el caller omita el overlay.
 */
export function patternFill(id: string, seriesIndex: number): string | undefined {
  const slot = seriesIndex % PATTERN_COUNT;
  if (PATTERNS[slot] === null) return undefined;
  return `url(#${id}-pattern-${slot})`;
}

/** stroke-dasharray cíclico para LinePath. Serie 0 es continua. */
export function dashArray(seriesIndex: number): string | undefined {
  const slot = seriesIndex % PATTERN_COUNT;
  switch (slot) {
    case 0:
      return undefined; // sólida
    case 1:
      return "6 3"; // dashed corta
    case 2:
      return "2 3"; // dotted
    case 3:
      return "8 2 2 2"; // dash-dot
    case 4:
      return "12 4"; // dashed larga
    default:
      return undefined;
  }
}
