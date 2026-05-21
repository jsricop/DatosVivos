"use client";

import { AxisBottom, AxisLeft } from "@visx/axis";
import { Group } from "@visx/group";
import { ParentSize } from "@visx/responsive";
import { scaleBand, scaleLinear } from "@visx/scale";
import { Bar, LinePath } from "@visx/shape";
import { useMemo } from "react";

type DataPoint = { x: string | number; y: number };

type ChartBlockProps = {
  type: "bar" | "line";
  data: DataPoint[];
  title?: string;
  caption?: string;
  xLabel?: string;
  yLabel?: string;
  altText?: string;
};

/**
 * ChartBlock (BRAND.md §8.9) — Visx headless.
 *
 * Reglas: tipografía Plex Mono tnum en ejes, grilla horizontal con --hairline,
 * barras/líneas en --accent. Sin animaciones de aparición.
 */
export function ChartBlock(props: ChartBlockProps) {
  const { title, caption, altText, type, data } = props;

  return (
    <figure
      aria-label={altText ?? caption ?? title}
      style={{
        margin: 0,
        border: "1px solid var(--hairline)",
        background: "var(--bg-elev)",
        padding: "var(--space-5)",
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      {title ? (
        <figcaption
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: "var(--type-h4)",
            fontWeight: 600,
            color: "var(--ink)",
          }}
        >
          {title}
        </figcaption>
      ) : null}

      {data.length === 0 ? (
        <p
          style={{
            margin: 0,
            fontFamily: "var(--font-sans)",
            fontSize: "var(--type-body-sm)",
            color: "var(--ink-muted)",
          }}
        >
          Sin datos suficientes para graficar.
        </p>
      ) : (
        <div style={{ width: "100%", height: 320 }}>
          <ParentSize>
            {({ width, height }) =>
              type === "bar" ? (
                <BarChart {...props} width={width} height={height} data={data} />
              ) : (
                <LineChart {...props} width={width} height={height} data={data} />
              )
            }
          </ParentSize>
        </div>
      )}

      {caption ? (
        <p
          style={{
            margin: 0,
            fontFamily: "var(--font-mono)",
            fontSize: "var(--type-caption)",
            color: "var(--ink-2)",
            borderBlockStart: "1px solid var(--hairline)",
            paddingBlockStart: 12,
          }}
        >
          {caption}
        </p>
      ) : null}
    </figure>
  );
}

const MARGIN = { top: 12, right: 16, bottom: 48, left: 56 };

const AXIS_TICK_LABEL = {
  fontFamily: "var(--font-mono)",
  fontSize: 11,
  fill: "var(--ink-2)",
  fontVariantNumeric: "tabular-nums" as const,
};

function BarChart({
  width,
  height,
  data,
  xLabel,
  yLabel,
}: ChartBlockProps & { width: number; height: number; data: DataPoint[] }) {
  const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
  const innerH = Math.max(0, height - MARGIN.top - MARGIN.bottom);

  const x = useMemo(
    () =>
      scaleBand<string>({
        domain: data.map((d) => String(d.x)),
        range: [0, innerW],
        padding: 0.3,
      }),
    [data, innerW],
  );
  const y = useMemo(() => {
    const max = Math.max(0, ...data.map((d) => d.y));
    return scaleLinear<number>({
      domain: [0, max * 1.1],
      range: [innerH, 0],
      nice: true,
    });
  }, [data, innerH]);

  return (
    <svg width={width} height={height} role="img">
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
            />
          );
        })}
        <AxisLeft
          scale={y}
          numTicks={5}
          stroke="var(--hairline-strong)"
          tickStroke="var(--hairline-strong)"
          tickLabelProps={() => AXIS_TICK_LABEL}
          label={yLabel}
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
          tickLabelProps={() => ({ ...AXIS_TICK_LABEL, textAnchor: "middle" })}
          label={xLabel}
          labelProps={{
            fontFamily: "var(--font-mono)",
            fontSize: 10,
            fill: "var(--ink-2)",
          }}
        />
      </Group>
    </svg>
  );
}

function LineChart({
  width,
  height,
  data,
  xLabel,
  yLabel,
}: ChartBlockProps & { width: number; height: number; data: DataPoint[] }) {
  const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
  const innerH = Math.max(0, height - MARGIN.top - MARGIN.bottom);

  const x = useMemo(() => {
    const labels = data.map((d) => String(d.x));
    return scaleBand<string>({ domain: labels, range: [0, innerW], padding: 0.1 });
  }, [data, innerW]);
  const y = useMemo(() => {
    const values = data.map((d) => d.y);
    const min = Math.min(0, ...values);
    const max = Math.max(0, ...values);
    return scaleLinear<number>({
      domain: [min, max * 1.1],
      range: [innerH, 0],
      nice: true,
    });
  }, [data, innerH]);

  return (
    <svg width={width} height={height} role="img">
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
        <LinePath
          data={data}
          x={(d) => (x(String(d.x)) ?? 0) + x.bandwidth() / 2}
          y={(d) => y(d.y)}
          stroke="var(--accent)"
          strokeWidth={2}
          strokeLinejoin="miter"
          strokeLinecap="square"
        />
        {data.map((d) => (
          <circle
            key={String(d.x)}
            cx={(x(String(d.x)) ?? 0) + x.bandwidth() / 2}
            cy={y(d.y)}
            r={3}
            fill="var(--accent)"
          />
        ))}
        <AxisLeft
          scale={y}
          numTicks={5}
          stroke="var(--hairline-strong)"
          tickStroke="var(--hairline-strong)"
          tickLabelProps={() => AXIS_TICK_LABEL}
          label={yLabel}
          labelProps={{ fontFamily: "var(--font-mono)", fontSize: 10, fill: "var(--ink-2)" }}
        />
        <AxisBottom
          top={innerH}
          scale={x}
          stroke="var(--hairline-strong)"
          tickStroke="var(--hairline-strong)"
          tickLabelProps={() => ({ ...AXIS_TICK_LABEL, textAnchor: "middle" })}
          label={xLabel}
          labelProps={{ fontFamily: "var(--font-mono)", fontSize: 10, fill: "var(--ink-2)" }}
        />
      </Group>
    </svg>
  );
}
