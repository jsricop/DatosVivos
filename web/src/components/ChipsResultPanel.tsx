"use client";

/**
 * Hito 1 / Fase C — render del resultado SoQL determinista.
 *
 * Recibe la respuesta de POST /api/v1/query/chips/execute y elige el bloque
 * de visualización apropiado según el TIPO:
 *
 *   Cuántos    → KPICardBlock   (count(*) único)
 *   Comparar   → BarChartBlock  (rows ordenados por n)
 *   Ranking    → BarChartBlock  (idéntico; si hay métrica, eje y = 'total')
 *   Tendencia  → LineChartBlock (eje x = periodo, eje y = n)
 *   Mapa       → ChoroplethMapBlock (region = DIVIPOLA dpto, valor = n)
 *
 * Reusa los componentes de `charts/` que ya valida el path SSE del LLM.
 * No hay nuevo viz code; solo armado de la spec por TIPO.
 */

import dynamic from "next/dynamic";

import type { ChipsExecuteResponse } from "@/lib/types";
import type {
  ChartBlock,
  KPIBlock,
  MapBlock,
} from "@/lib/schemas/dashboard";
import type { Row } from "@/lib/dashboard-data";
import { CheckIcon } from "@/components/icons";

// Cargas dinámicas con SSR off — mismo patrón que BlockRenderer.tsx para
// los charts pesados.
const KPICardBlock = dynamic(
  () => import("@/components/charts/KPICardBlock").then((m) => m.KPICardBlock),
  { ssr: false },
);
const BarChartBlock = dynamic(
  () => import("@/components/charts/BarChartBlock").then((m) => m.BarChartBlock),
  { ssr: false },
);
const LineChartBlock = dynamic(
  () => import("@/components/charts/LineChartBlock").then((m) => m.LineChartBlock),
  { ssr: false },
);
const ChoroplethMapBlock = dynamic(
  () =>
    import("@/components/charts/ChoroplethMapBlock").then(
      (m) => m.ChoroplethMapBlock,
    ),
  { ssr: false },
);

type Props = {
  /** Respuesta del POST /api/v1/query/chips/execute. */
  response: ChipsExecuteResponse;
  /** Nombre legible del dataset (para títulos). */
  datasetName: string;
};

export function ChipsResultPanel({ response, datasetName }: Props) {
  const { tipo, rows, columns_used, error } = response;

  // 1) El motor SoQL no pudo construir la query (TIPO incompatible con el
  //    dataset). Mensaje útil + sugerencia.
  if (error) {
    return (
      <article
        role="status"
        className="surface-card border-l-4 border-l-warn p-4 flex flex-col gap-2"
      >
        <span className="text-kicker text-ink">
          Este dataset no soporta {tipo}
        </span>
        <p className="font-sans text-body text-ink-2 m-0">{error}</p>
        <p className="font-sans text-caption text-ink-muted m-0">
          Prueba <em>Cuántos</em> o <em>Comparar</em> — funcionan sobre cualquier
          dataset con datos tabulares.
        </p>
      </article>
    );
  }

  // 2) El motor corrió pero SODA devolvió 0 filas (raro, p.ej. filtro
  //    geográfico sin coincidencias).
  if (rows.length === 0) {
    return (
      <article
        role="status"
        className="surface-card p-4 flex flex-col gap-2"
      >
        <span className="text-kicker">Sin datos</span>
        <p className="font-sans text-body text-ink-2 m-0">
          El dataset existe pero no devolvió filas para esta combinación. Prueba
          quitar un chip o cambiar de TIPO.
        </p>
      </article>
    );
  }

  // 3) Renderizar el bloque adecuado.
  const rowsTyped = rows as Row[];

  if (tipo === "Cuántos") {
    const block: KPIBlock = {
      type: "kpi",
      title: `Total · ${datasetName}`,
      value_from: "n",
      format: "number_es_co",
    };
    return (
      <div className="flex flex-col gap-2">
        <KPICardBlock block={block} rows={rowsTyped} stats={null} />
        <VerifiedNote countNote />
      </div>
    );
  }

  if (tipo === "Comparar" || tipo === "Ranking") {
    const yCol = columns_used.length >= 2 ? "total" : "n";
    const block: ChartBlock = {
      type: "bar",
      title:
        tipo === "Ranking"
          ? `Top 10 — ${datasetName}`
          : `Comparación — ${datasetName}`,
      x_column: "categoria",
      y_column: yCol,
    };
    return (
      <div className="flex flex-col gap-2">
        <BarChartBlock block={block} rows={rowsTyped} />
        <VerifiedNote />
      </div>
    );
  }

  if (tipo === "Tendencia") {
    const block: ChartBlock = {
      type: "line",
      title: `Tendencia — ${datasetName}`,
      x_column: "periodo",
      y_column: "n",
    };
    return (
      <div className="flex flex-col gap-2">
        <LineChartBlock block={block} rows={rowsTyped} />
        <VerifiedNote />
      </div>
    );
  }

  if (tipo === "Mapa") {
    // El choropleth casa por CÓDIGO DIVIPOLA contra el GeoJSON. Muchos
    // datasets solo traen NOMBRES ("Bogotá D.C.") — pintarían un mapa en
    // blanco. Si la mayoría de regiones no son códigos numéricos, degradamos
    // a barras: misma cifra verificada, artefacto legible.
    const numericas = rowsTyped.filter((r) =>
      /^\d{1,5}$/.test(String(r["region"] ?? "").trim()),
    ).length;
    if (rowsTyped.length > 0 && numericas < rowsTyped.length / 2) {
      const block: ChartBlock = {
        type: "bar",
        title: `Por región — ${datasetName}`,
        x_column: "region",
        y_column: "n",
      };
      return (
        <div className="flex flex-col gap-2">
          <BarChartBlock block={block} rows={rowsTyped.slice(0, 10)} />
          <p className="m-0 font-sans text-caption text-ink-muted">
            Este dataset registra la región por nombre (sin código DIVIPOLA),
            así que se muestra como barras en lugar de mapa.
          </p>
          <VerifiedNote />
        </div>
      );
    }
    const block: MapBlock = {
      type: "choropleth",
      title: `Mapa — ${datasetName}`,
      level: "dpto",
      code_column: "region",
      metric_column: "n",
      legend_format: "number_es_co",
    };
    return (
      <div className="flex flex-col gap-2">
        <ChoroplethMapBlock block={block} rows={rowsTyped} />
        <VerifiedNote />
      </div>
    );
  }

  // Type guard exhaustivo: TIPO desconocido (no debería pasar — el backend
  // valida el enum).
  return null;
}

/**
 * Nota de verificación bajo la cifra/visualización determinista. Refuerza el
 * pilar de Verificabilidad: la cifra sale del SoQL real, no de IA.
 * `countNote` añade la advertencia COUNT(*)≠suma (ADR-017).
 */
function VerifiedNote({ countNote = false }: { countNote?: boolean }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="inline-flex items-center gap-1.5 font-sans text-caption font-semibold text-ok">
        <CheckIcon /> Cifra verificada — sale del dataset, no de IA
      </span>
      {countNote ? (
        <span className="font-sans text-caption text-ink-muted">
          ⓘ Cuenta registros del dataset, no suma valores.
        </span>
      ) : null}
    </div>
  );
}
