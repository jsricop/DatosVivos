"use client";

import { AxisBottom, AxisLeft } from "@visx/axis";
import { Group } from "@visx/group";
import { ParentSize } from "@visx/responsive";
import { scaleBand, scaleLinear } from "@visx/scale";
import { AreaClosed, LinePath } from "@visx/shape";
import { useMemo } from "react";

import { useUserScale } from "@/lib/motion";
import {
  chartColor,
  formatValue,
  prepareSeriesData,
  type Row,
} from "@/lib/dashboard-data";
import type { ChartBlock } from "@/lib/schemas/dashboard";
import { dashArray } from "@/components/charts/chart-patterns";

const MARGIN = { top: 12, right: 16, bottom: 48, left: 56 };
const BASE_HEIGHT = 280;

const AXIS_TICK_LABEL = {
  fontFamily: "var(--font-mono)",
  fontSize: 11,
  fill: "var(--ink-2)",
} as const;

type Props = { block: ChartBlock; rows: Row[] };

export function LineChartBlock({ block, rows }: Props) {
  const series = useMemo(() => prepareSeriesData(block, rows), [block, rows]);
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
                        {s.data.map((d) => (
                          <circle
                            key={`${s.name}-${String(d.x)}`}
                            cx={xAt(d)}
                            cy={y(d.y)}
                            r={3}
                            fill={color}
                          >
                            <title>
                              {isMulti ? `${s.name} · ` : ""}
                              {String(d.x)}: {formatValue(d.y)}
                            </title>
                          </circle>
                        ))}
                      </g>
                    );
                  })}
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
