/**
 * Tipos compartidos client/server. Espejo de los pydantic schemas en api/models/schemas.py.
 * Si cambias aquí, también allá.
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

/** Hito 1 / Fase B — Motor SoQL determinista. Espejo de api/models/schemas.py. */
export type ChipTipo = "Cuántos" | "Total" | "Comparar" | "Ranking" | "Tendencia" | "Mapa";

/** Un filtro de valor sobre el dataset elegido (ADR-024). */
export type FilterSpec = {
  col: string;
  value: string;
};

export type ChipsExecuteRequest = {
  dataset_id: string;
  tipo: ChipTipo;
  territorio?: string | null;
  filters?: FilterSpec[] | null;
  pregunta?: string | null;
};

export type ChipsExecuteResponse = {
  dataset_id: string;
  tipo: ChipTipo;
  soql: string;
  columns_used: string[];
  rows: Row[];
  row_count: number;
  error?: string | null;
  filters_applied?: FilterSpec[] | null;
  filter_note?: string | null;
  unfiltered_total?: number | null;
  /** Unidad de UNA fila ("estudiantes matriculados") — da unidad al conteo. */
  row_unit?: string | null;
};

/** GET /api/datasets/{id}/filters — perfil de filtrables (ADR-024). */
export type FilterOption = { value: string; n?: number | null };
export type FilterColumn = { col: string; kind: string; values: FilterOption[] };
export type DatasetFiltersResponse = {
  dataset_id: string;
  filtros: FilterColumn[];
};

/** Hito 1 / Fase D — narrativa LLM "Explicar" (ADR-017). */
export type ChipsExplainRequest = {
  dataset_id: string;
  dataset_name: string;
  tipo: ChipTipo;
  rows: Row[];
  columns_used?: string[];
};

export type ChipsFromNLResponse = {
  tema?: string | null;
  tipo?: ChipTipo | null;
  territorio?: string | null;
  entidad?: string | null;
  refinador?: string | null;
};

export type ChipsExplainResponse = {
  dataset_id: string;
  tipo: ChipTipo;
  narrative: string;
  hallucinated_numbers?: string[];
  model: string;
  error?: string | null;
};

/** GET /api/v1/stats/catalog — conteos en vivo desde la vista del tablero. */
export type CatalogStats = {
  total: number;
  nativos: number;
  federados: number;
  directo: number;
  requiere_herramienta: number;
  solo_metadatos: number;
  consultable_tabla: number;
  util: number;
  admin: number;
};

/** Agregado por sector administrativo (solo datasets con sector conocido). */
export type SectorCount = {
  sector: string;
  n_datasets: number;
  n_entidades: number;
};

/** Agregado por departamento DIVIPOLA. */
export type DeptCount = {
  codigo: string;
  nombre: string;
  n_datasets: number;
};

/** Agregado por portal de origen del catálogo integrado. */
export type PortalCount = {
  portal: string;
  n_datasets: number;
};

/** Punto de la línea de tiempo: acumulado del catálogo a fin de ese año. */
export type YearCumulative = {
  anio: number;
  acumulado: number;
};

/**
 * GET /api/v1/stats/panorama — panorama nacional para la home (ADR-023).
 * Línea editorial sobre el CATÁLOGO COMPLETO: `total` coincide con
 * CatalogStats. La división temáticos/administrativos va en `composicion`.
 */
export type PanoramaStats = {
  total: number;
  n_entidades: number;
  composicion: Record<"tematicos" | "administrativos", number>;
  semaforo: Record<"verde" | "amarillo" | "rojo" | "desconocido", number>;
  acceso: Record<"directo" | "requiere_herramienta" | "solo_metadatos", number>;
  por_sector: SectorCount[];
  por_departamento: DeptCount[];
  por_portal: PortalCount[];
  nacional_sin_geo: number;
  generated_at: string;
  /** finished_at de la última corrida del ETL (la fecha real del dato). */
  last_etl_at?: string | null;
  /** Acumulado de datasets por año de creación en su portal de origen. */
  crecimiento?: YearCumulative[];
};
