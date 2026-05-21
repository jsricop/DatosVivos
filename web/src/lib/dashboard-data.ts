/**
 * Utilities para transformar rows crudos según un Block spec.
 * Compartido entre todos los *BlockRenderer.
 */

import type { ChartBlock, TableBlock } from "@/lib/schemas/dashboard";

export type Row = Record<string, unknown>;

const NUMBER_ES_CO = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 });
const PERCENT_ES_CO = new Intl.NumberFormat("es-CO", {
  style: "percent",
  maximumFractionDigits: 1,
});
const CURRENCY_COP = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});

export function formatValue(
  value: unknown,
  format: "number_es_co" | "percent" | "currency_cop" = "number_es_co",
): string {
  if (value === null || value === undefined) return "—";
  const num = typeof value === "number" ? value : Number(value);
  // NaN no se muestra como "NaN" — mejor un guion limpio (BRAND.md §1.3).
  if (!Number.isFinite(num)) return "—";
  if (format === "percent") return PERCENT_ES_CO.format(num);
  if (format === "currency_cop") return CURRENCY_COP.format(num);
  return NUMBER_ES_CO.format(num);
}

export function aggregate(
  rows: Row[],
  column: string,
  fn: "sum" | "count" | "mean",
): number {
  const values = rows
    .map((r) => r[column])
    .filter((v): v is number => v !== null && v !== undefined && !Number.isNaN(Number(v)))
    .map((v) => Number(v));
  if (fn === "count") return rows.length;
  if (values.length === 0) return 0;
  if (fn === "mean") return values.reduce((a, b) => a + b, 0) / values.length;
  return values.reduce((a, b) => a + b, 0);
}

/**
 * Prepara los datos para un ChartBlock: agrupa por x_column, agrega y_column,
 * aplica sort y limit. Si block.agg está ausente, devuelve los rows tal cual
 * (caso scatter o cuando ya vienen agregados desde SoQL).
 */
export function prepareChartData(
  block: ChartBlock,
  rows: Row[],
): Array<{ x: string | number; y: number; raw: Row }> {
  if (!block.agg) {
    return rows.map((r) => ({
      x: r[block.x_column] as string | number,
      y: Number(r[block.y_column] ?? 0),
      raw: r,
    }));
  }

  const groups = new Map<string, Row[]>();
  for (const r of rows) {
    const key = String(r[block.x_column] ?? "—");
    const arr = groups.get(key);
    if (arr) arr.push(r);
    else groups.set(key, [r]);
  }
  let entries = Array.from(groups.entries()).map(([key, group]) => ({
    x: key,
    y: aggregate(group, block.y_column, block.agg!),
    raw: group[0]!,
  }));

  if (block.sort === "asc") entries.sort((a, b) => a.y - b.y);
  if (block.sort === "desc") entries.sort((a, b) => b.y - a.y);
  if (block.limit && entries.length > block.limit) {
    entries = entries.slice(0, block.limit);
  }
  // Defensa NaN: si Socrata devuelve `"abc"` en columna numérica el chart
  // dibujaría barras inválidas. Filtramos en silencio (BRAND.md §1.3: cero
  // cifras inventadas — preferimos omisión a ruido visual).
  return entries.filter((e) => Number.isFinite(e.y));
}

export type ChartSeries = {
  /** Nombre legible de la serie. Si solo hay 1, suele ser block.y_column. */
  name: string;
  data: Array<{ x: string | number; y: number; raw: Row }>;
};

/**
 * Variante multi-serie cuando un block tiene `groupby`. Cada valor único en
 * la columna groupby produce una serie distinta — listas para colorear con
 * la paleta categórica `--chart-1..5` (BRAND.md §8.9).
 *
 * Si block.groupby está ausente, devuelve 1 sola serie equivalente a
 * `prepareChartData`. Limit y sort se aplican a las claves x del primer
 * grupo (criterio: la serie más larga marca el rango visible).
 */
export function prepareSeriesData(
  block: ChartBlock,
  rows: Row[],
): ChartSeries[] {
  if (!block.groupby) {
    const data = prepareChartData(block, rows);
    return [{ name: block.y_column, data }];
  }

  // 1) Agrupar por (x, group) → valor agregado.
  const cell = new Map<string, Map<string, Row[]>>();
  for (const r of rows) {
    const xKey = String(r[block.x_column] ?? "—");
    const gKey = String(r[block.groupby] ?? "—");
    const inner = cell.get(gKey) ?? new Map<string, Row[]>();
    const arr = inner.get(xKey) ?? [];
    arr.push(r);
    inner.set(xKey, arr);
    cell.set(gKey, inner);
  }

  // 2) Construir series.
  const aggFn = block.agg ?? "sum";
  const allX = new Set<string>();
  const series: ChartSeries[] = Array.from(cell.entries()).map(([gKey, xs]) => {
    const data = Array.from(xs.entries())
      .map(([x, group]) => {
        allX.add(x);
        return {
          x,
          y: aggregate(group, block.y_column, aggFn),
          raw: group[0]!,
        };
      })
      .filter((e) => Number.isFinite(e.y));
    return { name: gKey, data };
  });

  // 3) Limit cap: solo el top-N de claves x más comunes en términos del
  //    máximo Y de cualquier serie. Aplica solo si todas las series superan
  //    el limit (caso contrario podríamos cortar visualmente datos relevantes).
  if (block.limit && allX.size > block.limit) {
    const xMaxY = new Map<string, number>();
    for (const s of series) {
      for (const point of s.data) {
        xMaxY.set(String(point.x), Math.max(xMaxY.get(String(point.x)) ?? 0, point.y));
      }
    }
    const top = Array.from(xMaxY.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, block.limit)
      .map(([x]) => x);
    const keep = new Set(top);
    for (const s of series) {
      s.data = s.data.filter((p) => keep.has(String(p.x)));
    }
  }

  return series;
}

/** Tokens de la paleta categórica, cíclicos. */
export const CHART_PALETTE_TOKENS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
] as const;

export function chartColor(seriesIndex: number): string {
  return CHART_PALETTE_TOKENS[seriesIndex % CHART_PALETTE_TOKENS.length]!;
}

export function prepareTableRows(block: TableBlock, rows: Row[]): Row[] {
  if (block.max_rows && rows.length > block.max_rows) {
    return rows.slice(0, block.max_rows);
  }
  return rows;
}

export function resolveKpiValue(
  expr: string,
  rows: Row[],
  stats: Record<string, unknown> | null,
): unknown {
  // `value_from` puede ser:
  //   - `stats.aggregate_total` → busca en stats si está expuesto.
  //   - `stats.column_max` o `stats.column_min` → patrón.
  //   - Un nombre de columna → toma el valor de la primera fila.
  //   - Una expresión `sum(col)` o `mean(col)` → agrega los rows.
  const m = /^(sum|mean|count|max|min)\(([^)]+)\)$/i.exec(expr.trim());
  if (m && m[1] && m[2]) {
    const fn = m[1].toLowerCase();
    const col = m[2].trim();
    const numericValues = rows
      .map((r) => Number(r[col] ?? Number.NaN))
      .filter((v) => !Number.isNaN(v));
    if (fn === "max") {
      return numericValues.length ? Math.max(...numericValues) : 0;
    }
    if (fn === "min") {
      return numericValues.length ? Math.min(...numericValues) : 0;
    }
    return aggregate(rows, col, fn as "sum" | "mean" | "count");
  }
  if (stats && expr in stats) return stats[expr];
  if (rows.length > 0 && rows[0] && expr in rows[0]) return rows[0][expr];
  return null;
}
