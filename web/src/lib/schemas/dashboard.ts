/**
 * Schemas zod del Dashboard Spec — espejo de `api/models/dashboard.py`.
 *
 * El backend FastAPI emite un evento SSE `dashboard_spec` con un JSON que
 * coincide con `dashboardSpecSchema`. Si zod falla en `safeParse`, el frontend
 * cae a fallback (PlainTable) en lugar de romper el render.
 */

import { z } from "zod";

export const kpiBlockSchema = z.object({
  type: z.literal("kpi"),
  title: z.string().min(1).max(120),
  value_from: z.string().min(1).max(80),
  format: z
    .enum(["number_es_co", "percent", "currency_cop"])
    .default("number_es_co"),
  delta: z
    .object({
      value_from: z.string().optional(),
      trend: z.enum(["up", "down", "flat"]).optional(),
    })
    .nullable()
    .optional(),
});
export type KPIBlock = z.infer<typeof kpiBlockSchema>;

export const chartBlockSchema = z.object({
  type: z.enum(["bar", "line", "area", "scatter", "pie", "donut"]),
  title: z.string().min(1).max(120),
  x_column: z.string().min(1).max(80),
  y_column: z.string().min(1).max(80),
  groupby: z.string().max(80).nullable().optional(),
  agg: z.enum(["sum", "count", "mean"]).nullable().optional(),
  sort: z.enum(["asc", "desc", "none"]).nullable().optional(),
  limit: z.number().int().min(1).max(100).nullable().optional(),
  stacked: z.boolean().nullable().optional(),
});
export type ChartBlock = z.infer<typeof chartBlockSchema>;

export const mapBlockSchema = z.object({
  type: z.literal("choropleth"),
  title: z.string().min(1).max(120),
  level: z.enum(["dpto", "mpio"]),
  code_column: z.string().min(1).max(80),
  metric_column: z.string().min(1).max(80),
  legend_format: z.enum(["number_es_co", "percent"]).default("number_es_co"),
});
export type MapBlock = z.infer<typeof mapBlockSchema>;

export const tableBlockSchema = z.object({
  type: z.literal("table"),
  title: z.string().min(1).max(120),
  columns: z.array(z.string()).min(1).max(20),
  max_rows: z.number().int().min(1).max(500).nullable().optional(),
});
export type TableBlock = z.infer<typeof tableBlockSchema>;

export const blockSchema = z.discriminatedUnion("type", [
  kpiBlockSchema,
  chartBlockSchema,
  mapBlockSchema,
  tableBlockSchema,
]);
export type Block = z.infer<typeof blockSchema>;

export const dashboardSpecSchema = z.object({
  version: z.literal("1"),
  title: z.string().min(1).max(200),
  subtitle: z.string().max(300).nullable().optional(),
  layout: z.enum(["grid", "stack"]).default("grid"),
  blocks: z.array(blockSchema).min(1).max(6),
  caveats: z.array(z.string()).max(10).nullable().optional(),
});
export type DashboardSpec = z.infer<typeof dashboardSpecSchema>;

export function parseDashboardSpec(
  raw: unknown,
): DashboardSpec | null {
  const result = dashboardSpecSchema.safeParse(raw);
  if (!result.success) return null;
  return result.data;
}
