"use client";

import { AxisBottom, AxisLeft } from "@visx/axis";
import { Group } from "@visx/group";
import { ParentSize } from "@visx/responsive";
import { scaleBand, scaleLinear } from "@visx/scale";
import { AreaClosed, LinePath } from "@visx/shape";
import { useMemo, useState } from "react";

import { useUserScale } from "@/lib/motion";
import {
  chartColor,
  formatValue,
  prepareSeriesData,
  type Row,
} from "@/lib/dashboard-data";
import type { ChartBlock } from "@/lib/schemas/dashboard";
import { dashArray } from "@/components/charts/chart-patterns";

// bottom amplio: las etiquetas X van VERTICALES (fechas completas se
// solapaban en horizontal, 2026-07-13).
const MARGIN = { top: 12, right: 16, bottom: 92, left: 56 };
const BASE_HEIGHT = 300;

/**
 * Etiqueta legible para un periodo del eje X: quita la hora ("2021-04-01
 * 00:00:00" → "2021-04") y deja el día solo cuando aporta ("2021-04-15").
 * Valores que no parecen fecha (años, trimestres) pasan tal cual.
 */
function formatPeriodo(raw: string): string {
  const m = raw.match(/^"?(\d{4})-(\d{2})-(\d{2})[T ]?/);
  if (m) return m[3] === "01" ? `${m[1]}-${m[2]}` : `${m[1]}-${m[2]}-${m[3]}`;
  return raw.replace(/"/g, "");
}

const AXIS_TICK_LABEL = {
  fontFamily: "var(--font-mono)",
  fontSize: 11,
  fill: "var(--ink-2)",
} as const;

type Props = { block: ChartBlock; rows: Row[] };

export function LineChartBlock({ block, rows }: Props) {
  const series = useMemo(() => prepareSeriesData(block, rows), [block, rows]);
  // Punto bajo el cursor (serie, índice): tooltip SVG propio — el <title>
  // nativo tarda y el punto de 3px era un blanco imposible (2026-07-13).
  const [hover, setHover] = useState<{ s: number; i: number } | null>(null);
  const userScale = useUserScale();
  const height = Math.round(BASE_HEIGHT * userScale);
  const isArea = block.type === "area";
  const isMulti = series.length > 1;

  const xDomain = useMemo(() => {
    const set = new Set<string>();
    for (const s of series) for (const p of s.data) set.add(String(p.x));
    return Array.from(set);
  }, [series]);

  const { yMin, yMax } = useMemo(() => {
    let min = 0;
    let max = 0;
    for (const s of series) {
      for (const p of s.data) {
        min = Math.min(min, p.y);
        max = Math.max(max, p.y);
      }
    }
    return { yMin: min, yMax: max };
  }, [series]);

  return (
    <figure
      aria-label={block.title}
      className="surface-elev m-0 p-4 flex flex-col gap-3"
    >
      <figcaption className="text-kicker">{block.title}</figcaption>
      {isMulti ? (
        <ul className="flex flex-wrap gap-x-4 gap-y-1 list-none">
          {series.map((s, i) => (
            <li
              key={s.name}
              className="inline-flex items-center gap-1.5 font-mono text-caption text-ink-2"
            >
              <svg
                aria-hidden
                width={18}
                height={6}
                viewBox="0 0 18 6"
                className="inline-block"
              >
                <line
                  x1={0}
                  y1={3}
                  x2={18}
                  y2={3}
                  stroke={chartColor(i)}
                  strokeWidth={2}
                  strokeDasharray={dashArray(i)}
                  strokeLinecap="square"
                />
              </svg>
              <span>{s.name}</span>
            </li>
          ))}
        </ul>
      ) : null}
      <div style={{ width: "100%", height }}>
        <ParentSize>
          {({ width, height: h }) => {
            const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
            const innerH = Math.max(0, h - MARGIN.top - MARGIN.bottom);
            const x = scaleBand<string>({
              domain: xDomain,
              range: [0, innerW],
              padding: 0.1,
            });
            const y = scaleLinear<number>({
              domain: [yMin, (yMax || 1) * 1.1],
              range: [innerH, 0],
              nice: true,
            });
            const xAt = (d: { x: string | number }) =>
              (x(String(d.x)) ?? 0) + x.bandwidth() / 2;

            return (
              <svg width={width} height={h} role="img" aria-label={block.title}>
                <Group left={MARGIN.left} top={MARGIN.top}>
                  {y.ticks(5).map((t) => (
                    <line
                      key={t}
                      x1={0}
                      x2={innerW}
                      y1={y(t)}
                      y2={y(t)}
                      stroke="var(--hairline)"
                      strokeWidth={1}
                    />
                  ))}
                  {series.map((s, sIdx) => {
                    const color = chartColor(sIdx);
                    // Dash-array cíclico cuando hay multi-serie: garantiza
                    // diferenciación visual aunque dos colores choquen para
                    // un usuario con daltonismo (BRAND.md §8.9 + WCAG 1.4.1).
                    const dash = isMulti ? dashArray(sIdx) : undefined;
                    return (
                      <g key={s.name}>
                        {isArea ? (
                          <AreaClosed
                            data={s.data}
                            x={xAt}
                            y={(d) => y(d.y)}
                            yScale={y}
                            fill={color}
                            fillOpacity={isMulti ? 0.08 : 0.18}
                            stroke={color}
                            strokeWidth={2}
                            strokeDasharray={dash}
                          />
                        ) : (
                          <LinePath
                            data={s.data}
                            x={xAt}
                            y={(d) => y(d.y)}
                            stroke={color}
                            strokeWidth={2}
                            strokeLinejoin="miter"
                            strokeLinecap="square"
                            strokeDasharray={dash}
                          />
                        )}
                        {s.data.map((d, i) => (
                          <g key={`${s.name}-${String(d.x)}`}>
                            <circle
                              cx={xAt(d)}
                              cy={y(d.y)}
                              r={hover?.s === sIdx && hover?.i === i ? 5 : 3}
                              fill={color}
                            />
                            {/* blanco de hover generoso e invisible */}
                            <circle
                              cx={xAt(d)}
                              cy={y(d.y)}
                              r={12}
                              fill="transparent"
                              onMouseEnter={() => setHover({ s: sIdx, i })}
                              onMouseLeave={() => setHover(null)}
                            />
                          </g>
                        ))}
                      </g>
                    );
                  })}
                  {hover && series[hover.s]?.data[hover.i] ? (
                    (() => {
                      const s = series[hover.s]!;
                      const d = s.data[hover.i]!;
                      const texto = `${isMulti ? `${s.name} · ` : ""}${formatPeriodo(
                        String(d.x),
                      )}: ${formatValue(d.y)}`;
                      const tw = texto.length * 7 + 16;
                      const tx = Math.min(
                        Math.max(xAt(d) - tw / 2, 0),
                        Math.max(0, innerW - tw),
                      );
                      const ty = Math.max(y(d.y) - 34, -MARGIN.top + 2);
                      return (
                        <g pointerEvents="none" transform={`translate(${tx}, ${ty})`}>
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
                            fontFamily="var(--font-mono)"
                            fontSize={12}
                            fill="var(--bg)"
                          >
                            {texto}
                          </text>
                        </g>
                      );
                    })()
                  ) : null}
                  <AxisLeft
                    scale={y}
                    numTicks={5}
                    stroke="var(--hairline-strong)"
                    tickStroke="var(--hairline-strong)"
                    tickFormat={(v) => formatValue(Number(v))}
                    tickLabelProps={() => AXIS_TICK_LABEL}
                    label={block.y_column}
                    labelProps={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 10,
                      fill: "var(--ink-2)",
                    }}
                  />
                  <AxisBottom
                    top={innerH}
                    scale={x}
                    stroke="var(--hairline-strong)"
                    tickStroke="var(--hairline-strong)"
                    numTicks={Math.max(4, Math.floor(innerW / 30))}
                    tickFormat={(v) => formatPeriodo(String(v))}
                    // Verticales: las fechas completas en horizontal se
                    // solapaban hasta ser ilegibles (2026-07-13).
                    tickLabelProps={() => ({
                      ...AXIS_TICK_LABEL,
                      textAnchor: "end" as const,
                      angle: -90,
                      dx: -4,
                      dy: -4,
                    })}
                    label={block.x_column}
                    labelProps={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 10,
                      fill: "var(--ink-2)",
                      dy: 24,
                    }}
                    labelOffset={62}
                  />
                </Group>
              </svg>
            );
          }}
        </ParentSize>
      </div>
    </figure>
  );
}
