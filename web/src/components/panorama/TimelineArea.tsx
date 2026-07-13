"use client";

import { useState } from "react";

import { useRevealOnce } from "@/components/panorama/useRevealOnce";
import type { YearCumulative } from "@/lib/types";

const fmt = (n: number) => n.toLocaleString("es-CO");

/**
 * Línea de tiempo del catálogo: área acumulada de datasets por año, a ancho
 * completo. SVG puro (sin librerías): eje X = años, eje Y = acumulado.
 * El primer punto agrupa ≤2015; el último es el total actual del catálogo.
 * Reveal con clip-path horizontal (fail-safe sin JS: se ve completa).
 */
export function TimelineArea({ puntos }: { puntos: YearCumulative[] }) {
  const { ref, revealed } = useRevealOnce<HTMLDivElement>();
  // Punto bajo el cursor: muestra su valor exacto (tooltip SVG propio — el
  // <title> nativo tarda y el punto de 3px era un blanco imposible).
  const [hover, setHover] = useState<number | null>(null);
  const primero = puntos[0];
  const ultimo = puntos[puntos.length - 1];
  if (!primero || !ultimo || puntos.length < 2) return null;

  const W = 960;
  const H = 220;
  const PAD_L = 8;
  const PAD_R = 8;
  const PAD_T = 18;
  const PAD_B = 26;
  const max = ultimo.acumulado;
  const innerW = W - PAD_L - PAD_R;
  const innerH = H - PAD_T - PAD_B;

  const x = (i: number) => PAD_L + (innerW * i) / (puntos.length - 1);
  const y = (v: number) => PAD_T + innerH * (1 - v / max);

  const linea = puntos
    .map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.acumulado).toFixed(1)}`)
    .join(" ");
  const area = `${linea} L${x(puntos.length - 1).toFixed(1)},${(PAD_T + innerH).toFixed(1)} L${PAD_L},${(PAD_T + innerH).toFixed(1)} Z`;

  // Etiquetas del eje X: primer año, último y saltos intermedios legibles.
  const paso = puntos.length > 8 ? 2 : 1;
  const etiquetas = puntos
    .map((p, i) => ({ p, i }))
    .filter(({ i }) => i === 0 || i === puntos.length - 1 || i % paso === 0);

  // Líneas guía horizontales en 1/2 y máximo.
  const guias = [max / 2, max];

  return (
    <div ref={ref} className="flex flex-col gap-2">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Crecimiento acumulado del catálogo: de ${fmt(
          primero.acumulado,
        )} datasets en ${primero.anio} a ${fmt(max)} en ${ultimo.anio}`}
        className="w-full h-auto"
      >
        {guias.map((v) => (
          <g key={v}>
            <line
              x1={PAD_L}
              x2={W - PAD_R}
              y1={y(v)}
              y2={y(v)}
              stroke="var(--hairline)"
              strokeDasharray="3 4"
            />
            <text
              x={W - PAD_R}
              y={y(v) - 5}
              textAnchor="end"
              className="font-mono"
              fontSize="12"
              fill="var(--ink-muted)"
            >
              {fmt(Math.round(v))}
            </text>
          </g>
        ))}

        <g
          style={{
            clipPath: revealed ? "inset(0 0% 0 0)" : "inset(0 100% 0 0)",
            transition: "clip-path 1100ms cubic-bezier(0.22, 1, 0.36, 1)",
          }}
        >
          <path d={area} fill="var(--chart-1)" opacity="0.16" />
          <path d={linea} fill="none" stroke="var(--chart-1)" strokeWidth="2.5" />
          {puntos.map((p, i) => (
            <circle
              key={p.anio}
              cx={x(i)}
              cy={y(p.acumulado)}
              r={hover === i ? 5 : 3}
              fill="var(--chart-1)"
            />
          ))}
        </g>

        {/* Blancos de hover invisibles (columna completa por punto) + tooltip. */}
        {puntos.map((p, i) => (
          <rect
            key={`hit-${p.anio}`}
            x={x(i) - innerW / (puntos.length - 1) / 2}
            y={0}
            width={innerW / (puntos.length - 1)}
            height={H - PAD_B}
            fill="transparent"
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
          />
        ))}
        {hover !== null && puntos[hover] ? (
          <g pointerEvents="none">
            <line
              x1={x(hover)}
              x2={x(hover)}
              y1={PAD_T}
              y2={PAD_T + innerH}
              stroke="var(--hairline-strong)"
              strokeDasharray="2 3"
            />
            {(() => {
              const p = puntos[hover]!;
              const texto = `${hover === 0 ? "≤" : ""}${p.anio}: ${fmt(p.acumulado)}`;
              const tw = texto.length * 7.5 + 16;
              const tx = Math.min(Math.max(x(hover) - tw / 2, PAD_L), W - PAD_R - tw);
              const ty = Math.max(y(p.acumulado) - 34, 2);
              return (
                <g transform={`translate(${tx}, ${ty})`}>
                  <rect
                    width={tw}
                    height={24}
                    rx={3}
                    fill="var(--ink)"
                    opacity="0.92"
                  />
                  <text
                    x={tw / 2}
                    y={16}
                    textAnchor="middle"
                    className="font-mono"
                    fontSize="12"
                    fill="var(--bg)"
                  >
                    {texto}
                  </text>
                </g>
              );
            })()}
          </g>
        ) : null}

        {etiquetas.map(({ p, i }) => (
          <text
            key={p.anio}
            x={x(i)}
            y={H - 8}
            textAnchor={i === 0 ? "start" : i === puntos.length - 1 ? "end" : "middle"}
            className="font-mono"
            fontSize="12"
            fill="var(--ink-2)"
          >
            {i === 0 ? `≤${p.anio}` : p.anio}
          </text>
        ))}
      </svg>
      <p className="m-0 font-mono text-caption text-ink-muted">
        {fmt(primero.acumulado)} datasets hasta {primero.anio} →{" "}
        <strong className="text-ink">{fmt(max)}</strong> hoy
      </p>
    </div>
  );
}
