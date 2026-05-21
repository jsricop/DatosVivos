"use client";

import { AxisBottom, AxisLeft } from "@visx/axis";
import { Group } from "@visx/group";
import { ParentSize } from "@visx/responsive";
import { scaleBand, scaleLinear } from "@visx/scale";
import { Bar } from "@visx/shape";
import { useMemo } from "react";

import { useUserScale } from "@/lib/motion";
import { formatValue, prepareChartData, type Row } from "@/lib/dashboard-data";
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
  const data = useMemo(() => prepareChartData(block, rows), [block, rows]);
  const userScale = useUserScale();
  const height = Math.round(BASE_HEIGHT * userScale);

  return (
    <figure
      aria-label={block.title}
      className="surface-elev m-0 p-4 flex flex-col gap-3"
    >
      <figcaption className="text-kicker">{block.title}</figcaption>
      <div style={{ width: "100%", height }}>
        <ParentSize>
          {({ width, height: h }) => {
            const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
            const innerH = Math.max(0, h - MARGIN.top - MARGIN.bottom);
            const x = scaleBand<string>({
              domain: data.map((d) => String(d.x)),
              range: [0, innerW],
              padding: 0.3,
            });
            const max = Math.max(0, ...data.map((d) => d.y));
            const y = scaleLinear<number>({
              domain: [0, max * 1.1 || 1],
              range: [innerH, 0],
              nice: true,
            });
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
                  {data.map((d) => {
                    const bx = x(String(d.x)) ?? 0;
                    const bw = x.bandwidth();
                    const by = y(d.y);
                    const bh = innerH - by;
                    return (
                      <Bar
                        key={String(d.x)}
                        x={bx}
                        y={by}
                        width={bw}
                        height={bh}
                        fill="var(--accent)"
                      >
                        <title>{`${d.x}: ${formatValue(d.y)}`}</title>
                      </Bar>
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
