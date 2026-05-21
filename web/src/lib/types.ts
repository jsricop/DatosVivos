/**
 * Tipos compartidos client/server. Espejo de los pydantic schemas en api/models/schemas.py.
 * Si cambias acá, también allá.
 */

export type Intent =
  | "search"
  | "descriptive"
  | "comparative"
  | "temporal"
  | "cross_source";

export type DatasetCitation = {
  index: number;
  id: string;
  name: string;
  entity: string | null;
  url: string;
  api_url: string;
};

export type Row = Record<string, string | number | boolean | null>;

export type PopularQuery = {
  question: string;
  count: number;
  intent?: Intent | null;
};

export type SuggestOption = {
  value: string;
  label: string;
  count?: number;
  kicker?: string;
};

export type Axis = "tema" | "tipo" | "territorio" | "entidad";

export type DivipolaItem = {
  code: string;
  name: string;
  dpto_code?: string;
};

export type DatasetMetadata = {
  id: string;
  name: string;
  entity: string | null;
  description: string;
  columns: Array<{
    field_name: string;
    name: string;
    data_type: string;
    description?: string;
  }>;
  row_count?: number;
  last_updated?: string;
  url: string;
  api_url: string;
};

/** Eventos SSE emitidos por POST /api/v1/query (ADR-013 + PLAN_DASHBOARD §2). */
export type QueryEvent =
  | { type: "intent"; intent: Intent; confidence: number }
  | { type: "dataset_hits"; datasets: Array<{ id: string; name: string; entity?: string | null; score: number }> }
  | { type: "narrative_chunk"; text: string }
  | { type: "rows"; count: number; columns: string[]; preview: Row[] }
  | { type: "citations"; citations: DatasetCitation[] }
  | { type: "soql"; soql: string }
  | { type: "dashboard_spec"; spec: unknown } // validado con zod en el cliente
  | { type: "error"; code: string; message: string }
  | { type: "done"; elapsed_s: number };
