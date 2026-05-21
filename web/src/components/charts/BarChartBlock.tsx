"use client";

import { AxisBottom, AxisLeft } from "@visx/axis";
import { Group } from "@visx/group";
import { ParentSize } from "@visx/responsive";
import { scaleBand, scaleLinear } from "@visx/scale";
import { Bar } from "@visx/shape";
import { useMemo } from "react";

import { useUserScale } from "@/lib/motion";
import {
  chartColor,
  formatValue,
  prepareSeriesData,
  type Row,
} from "@/lib/dashboard-data";
import type { ChartBlock } from "@/lib/schemas/dashboard";

const MARGIN = { top: 12, right: 16, bottom: 56, left: 64 };
const BASE_HEIGHT = 280;

const AXIS_TICK_LABEL = {
  fontFamily: "var(--font-mono)",
  fontSize: 11,
  fill: "var(--ink-2)",
} as const;

type Props = { block: ChartBlock; rows: Row[] };

export function BarChartBlock({ block, rows }: Props) {
  const series = useMemo(() => prepareSeriesData(block, rows), [block, rows]);
  const userScale = useUserScale();
  const height = Math.round(BASE_HEIGHT * userScale);

  // Eje X compartido y máximo Y para escala común a todas las series.
  const xDomain = useMemo(() => {
    const set = new Set<string>();
    for (const s of series) for (const p of s.data) set.add(String(p.x));
    return Array.from(set);
  }, [series]);

  const yMax = useMemo(() => {
    let max = 0;
    for (const s of series) for (const p of s.data) max = Math.max(max, p.y);
    return max;
  }, [series]);

  const hasData = xDomain.length > 0 && yMax > 0;
  const isMulti = series.length > 1;

  return (
    <figure
      aria-label={block.title}
      className="surface-elev m-0 p-4 flex flex-col gap-3"
    >
      <figcaption className="text-kicker">{block.title}</figcaption>
      {isMulti ? <Legend series={series} /> : null}
      <div style={{ width: "100%", height }}>
        <ParentSize>
          {({ width, height: h }) => {
            const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
            const innerH = Math.max(0, h - MARGIN.top - MARGIN.bottom);
            const x = scaleBand<string>({
              domain: xDomain,
              range: [0, innerW],
              padding: isMulti ? 0.2 : 0.3,
            });
            const y = scaleLinear<number>({
              domain: [0, yMax * 1.1 || 1],
              range: [innerH, 0],
              nice: true,
            });
            const subBand = isMulti
              ? scaleBand<string>({
                  domain: series.map((s) => s.name),
                  range: [0, x.bandwidth()],
                  padding: 0.1,
                })
              : null;

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
                  {hasData
                    ? series.flatMap((s, sIdx) => {
                        const color = chartColor(sIdx);
                        return s.data.map((d) => {
                          const xKey = String(d.x);
                          const bx = x(xKey) ?? 0;
                          const innerX = subBand
                            ? bx + (subBand(s.name) ?? 0)
                            : bx;
                          const bw = subBand
                            ? subBand.bandwidth()
                            : x.bandwidth();
                          const by = y(d.y);
                          const bh = innerH - by;
                          return (
                            <Bar
                              key={`${s.name}-${xKey}`}
                              x={innerX}
                              y={by}
                              width={bw}
                              height={bh}
                              fill={color}
                            >
                              <title>
                                {isMulti ? `${s.name} · ` : ""}
                                {xKey}: {formatValue(d.y)}
                              </title>
                            </Bar>
                          );
                        });
                      })
                    : null}
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
                    tickLabelProps={() => ({
                      ...AXIS_TICK_LABEL,
                      textAnchor: "middle",
                    })}
                    label={block.x_column}
                    labelProps={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 10,
                      fill: "var(--ink-2)",
                    }}
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

function Legend({
  series,
}: {
  series: Array<{ name: string; data: unknown[] }>;
}) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 list-none">
      {series.map((s, i) => (
        <li
          key={s.name}
          className="inline-flex items-center gap-1.5 font-mono text-caption text-ink-2"
        >
          <span
            aria-hidden
            className="inline-block w-3 h-3"
            style={{ background: chartColor(i), border: "1px solid var(--ink)" }}
          />
          <span>{s.name}</span>
        </li>
      ))}
    </ul>
  );
}
