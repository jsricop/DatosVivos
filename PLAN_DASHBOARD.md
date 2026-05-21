# PLAN_DASHBOARD.md — Dashboards autogenerados por razonamiento LLM

> Plan operativo para la capa de visualización dinámica de Beta-2. Los dashboards no son plantillas fijas: el LLM 14B **razona qué visualizaciones tienen sentido** para cada pregunta y emite un **Dashboard Spec** (JSON) que el frontend Next.js renderiza dinámicamente.
>
> **Alineado con**: [ADR-011](./docs/adr/011-migracion-streamlit-a-nextjs.md) (migración Streamlit→Next.js), [ADR-012](./docs/adr/012-civic-editorial-design-system.md) (design system civic-editorial), [ADR-013](./docs/adr/013-fastapi-sse-vs-mcp-http.md) (FastAPI+SSE), [BRAND.md](./docs/BRAND.md) (3 modos color + WCAG AAA + IBM Plex + sin emojis).

---

## 0. Resumen ejecutivo

| Aspecto | Decisión |
|---|---|
| Generador de specs | LLM `qwen2.5:14b` (in-prod, sin GPU) emite JSON spec por pregunta |
| Transporte | Evento SSE adicional `dashboard_spec` en `POST /api/v1/query` (extiende ADR-013) |
| Validación spec | Pydantic + zod (schema dual Python/TS via OpenAPI) |
| Renderizado | Next.js 15 + React 19 + `<DashboardRenderer spec={...} data={...} />` |
| Stack visual base | **Tremor** (skeleton/KPIs) + **Recharts** (charts canónicos) + **react-leaflet** (mapas DIVIPOLA) |
| Stack visual avanzado | **Visx** (cuando Tremor/Recharts no alcanzan: sankey, treemap, bubble) |
| Accesibilidad | Cada chart genera alt-text desde stats deterministas + navegación teclado obligatoria |
| Modos color | Charts respetan tokens `[data-theme="light|dark|hc"]` desde BRAND.md |
| Motor IA backend | **NO se toca** — solo se extiende `api/routes/query.py` para emitir el evento |

**Dependencias críticas**: requiere `qwen2.5:14b` deployado (en curso al cierre de esta sesión) y la migración Next.js de [ADR-011](./docs/adr/011-migracion-streamlit-a-nextjs.md) avanzada hasta tener `web/components/` operativo.

---

## 1. Por qué dashboards generativos (no plantillas)

Plantillas fijas (un layout por intent) **no escalan** a la diversidad de preguntas reales del ciudadano:

- "Homicidios en Antioquia 2020-2024" → serie temporal + top mpios.
- "Compara Antioquia vs Valle en salud" → barras agrupadas + KPIs lado a lado.
- "Qué departamento contrata más" → ranking + mapa coroplético.
- "Tendencia de deforestación Amazonía" → línea + área apilada.
- "Pensionados de Antioquia por tipo" → pie/donut + tabla.

Hacer una plantilla por caso es trabajo infinito y se queda corto. La alternativa: **el LLM razona qué charts son útiles dada la pregunta + los datos disponibles** y emite un spec. Esto requiere razonamiento, contexto y creatividad — exactamente la capacidad que justifica el 14B vs el 3B.

---

## 2. Arquitectura

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          Next.js 15 (web/)                                   │
│                                                                              │
│   /chat                              /dashboard/:id                          │
│      ▼                                  ▼                                    │
│   <ChatPage>                          <DashboardPage>                        │
│      │                                                                       │
│      │  EventSource: GET /api/v1/query (SSE)                                 │
│      │                                                                       │
│      ├── event:intent             → muestra "Entendí: comparar"              │
│      ├── event:dataset_hits       → muestra cards de datasets                │
│      ├── event:narrative_chunk    → renderiza prosa progresiva               │
│      ├── event:rows               → guarda data cruda para charts            │
│      ├── event:citations          → muestra fuentes verificables             │
│      ├── event:dashboard_spec  ◀── NUEVO                                     │
│      │      ▼                                                                │
│      │   <DashboardRenderer spec={...} data={...} />                         │
│      │      ├── <KPICard>     × N                                            │
│      │      ├── <BarChart>    × N                                            │
│      │      ├── <LineChart>   × N                                            │
│      │      ├── <ChoroplethMap> (Colombia)                                   │
│      │      └── <DataTable>                                                  │
│      └── event:done                                                          │
└──────────────────────────────────────────────────────────────────────────────┘
                                  │ HTTP/SSE
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          FastAPI (api/)                                      │
│                                                                              │
│   POST /api/v1/query  ── (extiende routes/query.py)                          │
│      │                                                                       │
│      ├── ai_engine.Analyzer.analyze() ── existente, intacto                  │
│      │       └── devuelve: intent, hits, soql, rows, narrative, citations    │
│      ├── DashboardSpecGenerator.generate(ctx) ── NUEVO (~150 LoC)            │
│      │       └── llama Ollama qwen2.5:14b con prompt estructurado            │
│      │       └── valida JSON con Pydantic                                    │
│      └── yield SSE event "dashboard_spec"                                    │
└──────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│              Motor IA Python — INTACTO (ai_engine/, mcp_server/)             │
│   GeoResolver, VectorIndex, StatsComputer, Analyzer, telemetría              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Dashboard Spec (DSL)

El LLM emite un único JSON con esta estructura. Pydantic lo valida en backend, zod en frontend (schema sincronizado via `openapi-typescript`).

```typescript
type DashboardSpec = {
  version: "1";
  title: string;             // ej. "Homicidios en Antioquia 2020-2024"
  subtitle?: string;
  layout: "grid" | "stack";
  blocks: Block[];           // entre 1 y 6 — el LLM decide cuántos
  caveats?: string[];        // advertencias visibles (heredado de validate_geographic_attribution)
};

type Block =
  | KPIBlock
  | ChartBlock
  | MapBlock
  | TableBlock;

type KPIBlock = {
  type: "kpi";
  title: string;
  value_from: "stats.aggregate" | "stats.column_max" | "stats.column_min" | string;
  format: "number_es_co" | "percent" | "currency_cop";
  delta?: { value_from: string; trend: "up" | "down" | "flat" };
};

type ChartBlock = {
  type: "bar" | "line" | "area" | "scatter" | "pie" | "donut";
  title: string;
  x_column: string;
  y_column: string;
  groupby?: string;          // para barras agrupadas / líneas múltiples
  agg?: "sum" | "count" | "mean";
  sort?: "asc" | "desc" | "none";
  limit?: number;            // top-N
  stacked?: boolean;
};

type MapBlock = {
  type: "choropleth";
  title: string;
  level: "dpto" | "mpio";    // qué GeoJSON usar
  code_column: string;       // ej. "cod_dpto"
  metric_column: string;     // ej. "n"
  legend_format: "number_es_co" | "percent";
};

type TableBlock = {
  type: "table";
  title: string;
  columns: string[];
  max_rows?: number;
};
```

**Diseño deliberado:**
- Cada `Block` referencia columnas de `rows` por nombre exacto — el LLM ve el schema en el prompt.
- Sin colores, sin tamaños, sin posiciones absolutas: **el design system los pone**. El LLM solo decide *qué* mostrar, no *cómo*.
- Layout solo tiene dos valores (`grid` o `stack`) — evita parálisis de decisión y mantiene consistencia visual.

---

## 4. Capa de razonamiento (`DashboardSpecGenerator`)

Nuevo módulo en `ai_engine/dashboard_spec_generator.py`:

```python
class DashboardSpecGenerator:
    def __init__(self, llm: LLMBackend):
        self.llm = llm

    async def generate(
        self,
        question: str,
        intent: str,
        dataset_name: str,
        columns: list[ColumnSummary],
        rows: list[dict],
        stats: Statistics,
        geo_ctx: GeoContext | None,
    ) -> DashboardSpec | None:
        """Emite un DashboardSpec usando qwen2.5:14b.

        Devuelve None (no dashboard) si:
        - rows está vacío.
        - stats indica una sola fila escalar (no hay nada que graficar).
        - validación JSON falla 2 veces.
        """
        ...
```

**Prompt estructurado** (resumen — el archivo completo va en `ai_engine/prompts/dashboard_spec.md`):

```
Eres un diseñador de dashboards de datos abiertos colombianos.
Recibes una pregunta del ciudadano y los datos reales devueltos por Socrata.
Devuelves un JSON con un dashboard útil — máximo 4 bloques, mínimo 1.

PREGUNTA: «{question}»
INTENT: {intent}
DATASET: {dataset_name}

COLUMNAS DISPONIBLES (no inventes otras):
{columns_with_types}

PREVIEW DE FILAS:
{rows_preview[:5]}

STATS (cifras autorizadas):
{stats.summary_lines}

REGLAS:
1. Devolvés SOLO JSON válido — sin prosa, sin markdown.
2. Cada `x_column` y `y_column` debe existir en COLUMNAS DISPONIBLES.
3. Si hay columna temporal Y métrica numérica → considerá `line` o `area`.
4. Si hay columna categórica con ≤10 valores → considerá `bar` ranking.
5. Si hay `cod_dpto` o `cod_mpio` + métrica → incluí un `choropleth`.
6. KPI siempre cuando stats.aggregate_hits no esté vacío.
7. Si solo hay UNA fila → tabla simple, sin gráficos.
8. Si dudás del valor → omitílo (mejor menos charts buenos que muchos malos).
```

**Salida esperada para "Homicidios Antioquia 2020-2024" con 50 filas (anio, cod_mpio, casos):**

```json
{
  "version": "1",
  "title": "Homicidios en Antioquia 2020-2024",
  "layout": "grid",
  "blocks": [
    {"type": "kpi", "title": "Total acumulado", "value_from": "stats.aggregate_total", "format": "number_es_co"},
    {"type": "line", "title": "Tendencia anual", "x_column": "anio", "y_column": "casos", "agg": "sum"},
    {"type": "bar", "title": "Top 10 municipios", "x_column": "cod_mpio", "y_column": "casos", "agg": "sum", "sort": "desc", "limit": 10},
    {"type": "choropleth", "title": "Distribución geográfica", "level": "mpio", "code_column": "cod_mpio", "metric_column": "casos", "legend_format": "number_es_co"}
  ]
}
```

---

## 5. Capa de renderizado

### 5.1 Stack visual

| Necesidad | Librería | Por qué |
|---|---|---|
| Skeleton de dashboard | **Tremor** | Diseñado para esto, componentes pre-built (Card, KPI, Metric), respeta tokens custom |
| Charts canónicos (bar/line/area/scatter/pie) | **Recharts** | Liviano, idiomático React, tooltips, hover, brush, legible |
| Mapas Colombia | **react-leaflet** + GeoJSON DIVIPOLA | OSS, sin token, tile gratuito (OpenStreetMap), buen render de coropletas |
| Charts avanzados (sankey, treemap, bubble) | **Visx (Airbnb)** | Cuando Recharts no alcanza; D3 idiomático en React |
| KPIs animados | **Tremor `<DeltaBar>`, `<BadgeDelta>`** | Soporte semántico de trends, ariaLabels |
| Tablas | **TanStack Table** | Headless, soporta sort/filter/virtualization; estilizable 100% |

**NO usar**: Chart.js, Highcharts, AmCharts. Razón: licencia o estética inconsistente con BRAND.md.

### 5.2 Componente raíz

`web/components/dashboard/DashboardRenderer.tsx`:

```tsx
type Props = { spec: DashboardSpec; data: Record<string, unknown>[]; stats: Statistics };

export function DashboardRenderer({ spec, data, stats }: Props) {
  if (!spec.blocks.length) return null;

  const className = spec.layout === "grid"
    ? "grid gap-4 md:grid-cols-2 lg:grid-cols-3"
    : "flex flex-col gap-4";

  return (
    <section aria-label={`Dashboard: ${spec.title}`}>
      <header>
        <h2 className="font-display text-2xl">{spec.title}</h2>
        {spec.subtitle && <p className="text-muted">{spec.subtitle}</p>}
      </header>

      <div className={className}>
        {spec.blocks.map((block, i) => (
          <BlockRenderer key={i} block={block} data={data} stats={stats} />
        ))}
      </div>

      {spec.caveats?.length ? <Caveats items={spec.caveats} /> : null}
    </section>
  );
}
```

`BlockRenderer` despacha por `block.type` a `KPICardBlock`, `BarChartBlock`, `ChoroplethMapBlock`, etc.

### 5.3 Tokens visuales por modo

Cada chart consume **tokens CSS de BRAND.md** — no hardcodea colores:

```css
/* tokens.css (ya definidos en BRAND.md) */
[data-theme="light"] { --chart-1: #0033A0; --chart-2: #B22234; ... }
[data-theme="dark"]  { --chart-1: #5B91FF; --chart-2: #FF6B6B; ... }
[data-theme="hc"]    { --chart-1: #FFFF00; --chart-2: #FFFFFF; ... }
```

Recharts y Tremor reciben los colores via prop, leyendo el token:

```tsx
<Bar fill="var(--chart-1)" />
```

Esto garantiza que **un mismo Dashboard Spec rinde correctamente en los 3 modos color sin tocar JSON**.

---

## 6. Mapas Colombia

`web/components/dashboard/ChoroplethMap.tsx` usa react-leaflet + tile OSM. GeoJSON oficial:

| Nivel | Fuente | Tamaño aprox |
|---|---|---|
| Departamentos (33 features) | `web/public/geo/co_dptos.geojson` (DIVIPOLA + límites IGAC públicos) | ~50 KB minified |
| Municipios (1122 features) | `web/public/geo/co_mpios.geojson` | ~2 MB → servido con Cache-Control inmutable + gzip |

Pattern de coloreado: 5 buckets por cuantiles, paleta secuencial monocromática que respete los tokens. Tooltip muestra nombre + cifra normalizada es-CO.

**Caveat**: GeoJSON municipios pesa. Implementar lazy-load (solo si el spec lo requiere) con `dynamic(() => import('./ChoroplethMap'), { ssr: false })`.

---

## 7. Validación y seguridad del spec

### 7.1 Backend (Pydantic)

```python
class DashboardSpec(BaseModel):
    version: Literal["1"]
    title: str = Field(..., max_length=200)
    blocks: list[Block] = Field(..., min_length=1, max_length=6)
    # ...

    @model_validator(mode="after")
    def validate_columns_exist(self, info: ValidationInfo) -> "DashboardSpec":
        """Toda columna referenciada por blocks debe existir en `rows[0].keys()`.
        Si una falla, descartar el block (no abortar todo el spec)."""
        ...
```

Si el LLM 14B inventa una columna (alucinación), el block se descarta silenciosamente y se loggea en telemetría para análisis.

### 7.2 Frontend (zod)

```typescript
import { dashboardSpecSchema } from "@/lib/schemas/dashboard";

const result = dashboardSpecSchema.safeParse(rawSpec);
if (!result.success) {
  reportTelemetry("invalid_dashboard_spec", result.error);
  return <PlainTable data={data} />; // fallback
}
```

### 7.3 Fallback "no dashboard"

Cuándo NO mostrar dashboard (devolver `null` desde el generador):
- Rows vacíos.
- Una sola fila escalar (un KPI ya cubre todo, no necesita Dashboard wrapper).
- El LLM devolvió JSON inválido 2 veces (timeout o malformado).
- Pregunta de intent `metadata_only` o `cross_source` adversarial.

En esos casos, la respuesta del chat queda como hoy: prosa + bloque verificado + tabla cruda.

---

## 8. Accesibilidad (cumplir [BRAND.md](./docs/BRAND.md) WCAG AAA en HC)

Cada chart debe cumplir:

| Requisito | Implementación |
|---|---|
| Alt-text | `aria-label` generado desde `stats.summary_lines` (ya existe en `chart_narrator.py` legacy — portar la lógica a TS) |
| Navegación por teclado | `tabindex=0` en cada elemento interactivo, focus visible con `outline: 2px solid var(--focus)` |
| Contraste de líneas y barras | Tokens HC garantizan ≥7:1 en modo `[data-theme="hc"]` |
| Patrones además de color | En modo HC, agregar `pattern` (rayas, puntos) además del color — útil para daltónicos |
| Lectores de pantalla | `<title>` y `<desc>` SVG en cada chart; tabla equivalente debajo (oculta visualmente, no en SR) |
| Reduced motion | Animaciones desactivadas si `prefers-reduced-motion: reduce` |

Tests automatizados con **Playwright + axe-core** ejecutados en CI sobre 10 dashboards generados de muestra.

---

## 9. Tests

### 9.1 Backend (Python)

`tests/test_dashboard_spec_generator.py` — frozen acceptance:

1. Pregunta count + 1 fila → genera 1 KPIBlock, sin chart.
2. Pregunta temporal + rows con `anio` y `casos` → incluye LineChart.
3. Pregunta geo + rows con `cod_mpio` y métrica → incluye ChoroplethMap level=mpio.
4. Pregunta ranking + groupby → incluye BarChart con sort=desc + limit.
5. Spec con columna inexistente → block se descarta, resto se conserva.
6. LLM devuelve JSON malformado dos veces → generator devuelve None.
7. Rows vacíos → None.
8. Determinismo: misma pregunta + mismos rows + temperatura=0 → mismo spec.

### 9.2 Frontend (TypeScript + Playwright)

`web/tests/dashboard.spec.ts`:

1. Render de cada tipo de block con datos sintéticos.
2. Renderiza correctamente en los 3 modos color (snapshot por modo).
3. Navegación por teclado funciona en `BarChartBlock`.
4. Axe-core no reporta violaciones AA en modo `light/dark`, AAA en modo `hc`.
5. Lazy-load del mapa de mpios no rompe el render del resto.
6. Spec inválido (zod falla) renderiza fallback table.

### 9.3 E2E

`web/tests/e2e_dashboard.spec.ts`:

1. Pregunta "Homicidios en Antioquia 2020-2024" → dashboard con ≥3 blocks visibles.
2. Pregunta "Cuántos municipios tiene Antioquia" → solo KPI con valor 125.
3. Pregunta adversarial "Quiero datos sobre Ecuador" → sin dashboard, fallback prose.

---

## 10. Roadmap incremental

Coordinado con sprints de [ADR-011](./docs/adr/011-migracion-streamlit-a-nextjs.md).

| Sprint | Entregable |
|---|---|
| **A (paralelo a migración Next.js)** | Definir Pydantic + zod schemas. Implementar `DashboardSpecGenerator` con tests unitarios (sin LLM, con mock). |
| **B** | `<DashboardRenderer />` con `<KPICardBlock>` + `<BarChartBlock>` + `<LineChartBlock>` solamente. Datos sintéticos. |
| **C** | Integrar SSE event `dashboard_spec` en endpoint `/api/v1/query`. Conectar Next.js a fuente real. |
| **D** | `<ChoroplethMapBlock>` con GeoJSON departamentos. Lazy-load. |
| **E** | `<TableBlock>` + `<DonutChartBlock>` + paleta HC validada con axe-core. |
| **F** | Choropleth mpios (1122) con virtualización. Playwright E2E. |
| **G** (cutover) | Streamlit movido a perfil `legacy`. Beta-2 live en `/`. |

---

## 11. Consideraciones críticas

### 11.1 Latencia con 14B

El 14B en CPU-only tarda **25-40 s/pregunta**. Generar el dashboard_spec **agrega ~10-15 s extra** si lo hacemos en un segundo prompt secuencial.

**Mitigación**: el `dashboard_spec` puede generarse en **paralelo** con la narrativa final. Mientras Ollama genera tokens de la narrativa (streaming), una segunda llamada al mismo modelo (con seed distinto) genera el spec. Total: ~30-50 s por pregunta. Aceptable si el SSE muestra progreso visible.

**Alternativa más rápida**: usar el 3B SOLO para generar el spec (porque el JSON es un formato muy constreñido y el 3B lo maneja decentemente). El 14B queda exclusivo para la narrativa. Total: ~20-30 s. Vale probarlo si la latencia molesta al jurado.

### 11.2 Costo de tokens vs valor del dashboard

Cada spec son ~500-800 tokens output del LLM. Para 1.000 consultas/día son ~700 k tokens/día = $0 (local). No hay restricción económica.

### 11.3 Datasets sin estructura tabular clara

Algunos datasets de `datos.gov.co` tienen schemas raros: arrays anidados, strings con CSV interno, columnas que son JSON. El generador debe degradar a `<TableBlock>` simple en esos casos. Detección: si más del 30% de columnas son `kind="id"` o `kind="other"` en `ColumnSummary`, saltar charts.

### 11.4 GeoJSON municipios

2 MB es mucho para mobile 4G. Tres mitigaciones obligatorias:
1. Simplificar geometrías con `mapshaper -simplify 10%`.
2. Servir con `Cache-Control: max-age=31536000, immutable`.
3. Dynamic import — solo cargar cuando el dashboard incluye un ChoroplethMap level=mpio.

### 11.5 Consistencia entre el dashboard y la narrativa

El LLM puede generar un dashboard que enfatice X y una narrativa que enfatice Y. Aceptable porque ambas son interpretaciones de los mismos datos verificados, pero hay que monitorear coherencia en telemetría — agregar campo `dashboard_narrative_alignment` en `telemetry/queries.csv` para revisión manual periódica.

### 11.6 Compatibilidad con MCP

[ADR-013](./docs/adr/013-fastapi-sse-vs-mcp-http.md) mantiene MCP intacto. Los dashboards **NO** se exponen vía MCP — son una característica HTTP/SSE para Next.js. Clientes MCP (Claude Desktop, agentes externos) siguen recibiendo solo `narrative + rows + citations`.

### 11.7 Versionado del Spec

`version: "1"` es obligatorio en cada spec. Futuras versiones (`"2"`, etc.) son incompatibles y requieren nuevo renderer. El frontend rechaza specs de versiones desconocidas.

### 11.8 Auditabilidad para jurado MinTIC

Cada dashboard renderizado debe permitir:
- Ver el spec JSON crudo (botón "Ver spec" en producción).
- Descargar los rows que lo alimentaron (CSV).
- Ver el SoQL ejecutado y la URL del dataset original.

Esto satisface criterio 7.x de [`docs/crisp_mlq/08_mintic_checklist.md`](./docs/crisp_mlq/08_mintic_checklist.md) sobre trazabilidad.

---

## 12. Referencias

- [ADR-011](./docs/adr/011-migracion-streamlit-a-nextjs.md) — migración Streamlit→Next.js
- [ADR-012](./docs/adr/012-civic-editorial-design-system.md) — civic-editorial design system
- [ADR-013](./docs/adr/013-fastapi-sse-vs-mcp-http.md) — FastAPI + SSE
- [BRAND.md](./docs/BRAND.md) — paletas 3 modos color + tipografía + tokens
- [docs/accessibility.md](./docs/accessibility.md) — requisitos WCAG
- [docs/PROD_IMPROV.md](./docs/PROD_IMPROV.md) — mejoras restantes post-Beta-2
- Tremor: <https://tremor.so>
- Recharts: <https://recharts.org>
- Visx: <https://airbnb.io/visx>
- react-leaflet: <https://react-leaflet.js.org>

---

## Apéndice A — Por qué no usar plantillas estáticas

Considerado y descartado: definir 5-10 plantillas (timeseries, comparison, ranking, geo, kpi-only) y mapear intent → plantilla.

**Problemas**:
- Cobertura limitada: cada pregunta nueva fuera del catálogo no tiene dashboard, cae a tabla.
- Rigidez: una pregunta puede merecer mezcla (KPI + serie + mapa simultáneamente) que ninguna plantilla cubre exactamente.
- Branding inconsistente: cada plantilla acumula deuda visual.
- No aprovecha el 14B. El razonamiento del LLM queda subutilizado.

El enfoque generativo es **más costo de implementación inicial** pero **escala automáticamente** a cualquier dataset/pregunta sin nuevo código.

---

## Apéndice B — Métricas de éxito post-Sprint G

- **Cobertura**: % de respuestas con dashboard visible (target ≥ 70%).
- **Calidad subjetiva**: 20 dashboards muestreados, 3 evaluadores civiles puntúan utilidad 1-5 (target promedio ≥ 4.0).
- **Accesibilidad**: 0 violaciones axe-core AAA en modo HC.
- **Latencia**: P95 ≤ 60 s (incluye narrativa + spec + render).
- **Errores de spec inválido**: ≤ 2% (telemetría `invalid_dashboard_spec`).
- **Adopción**: % de usuarios que interactúan con al menos un chart (hover/click) por sesión (target ≥ 40%).
