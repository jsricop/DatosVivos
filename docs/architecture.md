# Arquitectura DatosVivos

Última actualización: **2026-07-10**. Refleja el estado tras el motor NL2SQL
generativo verificado (ADR-022), el pivote a home "panorama primero" (ADR-023),
la integración de portales por origen y el tablero Power BI público.

## Arquitectura de información — 3 niveles (ADR-023)

```
  Nivel 1  /          Panorama nacional — KPIs y gráficas en vivo
                      (GET /api/v1/stats/panorama, caché 5 min)
  Nivel 2  /tablero   Detalle por sector/entidad — Power BI publish-to-web
                      (alimentado por /api/v1/dashboard/*_decisor.csv)
  Nivel 3  /buscar    Dato puntual — lenguaje natural + chips
                      (motor NL2SQL verificado, pipeline abajo)
```

## Vista alta — pipeline del buscador (nivel 3)

```
                         ┌─────────────────────────────────┐
   Ciudadano             │  /buscar  (Next.js)             │
   ──────────────────────►  HeroSearch  +  QueryBuilderBar │
                         └────────────────┬────────────────┘
                                          │
        ┌─────────────────────────────────┴───────────────────────────┐
        │                                                             │
        ▼ texto libre                                                  ▼ chips marcados
┌────────────────────────────┐                          ┌────────────────────────────┐
│ POST /api/v1/chips/from-nl │                          │ POST /api/v1/query/chips   │
│   (Fase 2 — LLM mapper)    │                          │   (Fase 1 — filtro SQL)    │
│                            │                          │                            │
│  qwen2.5:3b + guardrail    │                          │  Postgres SELECT + score   │
│  → {tema, tipo, terr, ...} │                          │  → top-N candidatos + ELEGIDO  │
└────────┬───────────────────┘                          └────────────┬───────────────┘
         │ navega con chips                                          │
         ▼                                                           ▼
                  ┌──────────────────────────────────────────┐
                  │ POST /api/v1/query/chips/execute         │
                  │   (Fase B — motor SoQL/DuckDB)           │
                  │                                          │
                  │   dispatch source-aware                  │
                  │     ├─ socrata → build_soql + SodaClient │
                  │     └─ federated → build_duckdb_sql +    │
                  │                    DuckDB sobre CSV      │
                  │                                          │
                  │   Cuántos fast-path = Postgres row_count │
                  └─────────────┬────────────────────────────┘
                                │
                                ▼ ChipsExecuteResponse
                                │ {soql, columns_used, rows, error}
                                │
        ┌───────────────────────┼─────────────────────────────────┐
        │                       │                                 │
        ▼ render                ▼ verificación                    ▼ narrativa
┌─────────────────┐    ┌──────────────────┐         ┌─────────────────────────────┐
│ChipsResultPanel │    │  Audit visible   │         │ POST /api/v1/query/chips/   │
│ (Fase C)        │    │  toggle "Ver     │         │      explain                │
│                 │    │   consulta SoQL" │         │   (Fase D — narrativa LLM)  │
│  Cuántos→KPI    │    │                  │         │                             │
│  Comparar→Bar   │    └──────────────────┘         │ qwen2.5:7b + validator      │
│  Ranking→Bar    │                                 │ anti-alucinación censura    │
│  Tendencia→Line │                                 │ cifras no presentes en rows │
│  Mapa→Choropleth│                                 │                             │
│ (visx + d3-geo) │                                 └─────────────────────────────┘
└─────────────────┘
```

## ADR-017 — Arquitectura híbrida

**El LLM razona, el motor determinista ejecuta y verifica.**

- **Plano determinista** (verdad): chips → filtro SQL → SoQL/DuckDB → cifras de filas reales, nunca del LLM.
- **Plano IA** (razonamiento sobre substrato verificable):
  1. **NL→chips** (Fase 2): mapper LLM con guardrail post-LLM.
  2. **Selección de columnas** (`dataset_columns_curated`): clasificación LLM 3B previa.
  3. **Narrativa "Explicar"** (Fase D): sobre output ya verificado, validator censura cifras no presentes.

Ver `docs/adr/017-arquitectura-hibrida-ia-determinista.md`.

## Catálogo — capas y fuentes

> Cifras del diagrama al corte de su fecha (Hito R, 2026-06-08). El catálogo crece a
> diario: al 2026-07-10 son **25.192 datasets** de 6 portales de origen (datos.gov.co
> 12.101 · IGAC/Colombia en Mapas 6.622 · Bogotá 4.304 · Cali 1.236 · MEDATA 823 ·
> Valle 106). Conteo vivo: `GET /api/v1/stats/panorama`.

```
                  ┌──────────────────────┐
                  │  datasets (Postgres) │
                  │  23.854 filas        │
                  └──────────┬───────────┘
                             │
       ┌─────────────────────┼────────────────────────┐
       │ source_type=socrata │ source_type=federated  │
       │  (8.424)            │                        │
       │                     ├─ source_portal=        │
       │                     │  datos.gov.co (9.995)  │
       │                     │  ├─ federated_status=ok│
       │                     │  │  → CSV externo      │
       │                     │  │     (1.207)         │
       │                     │  └─ no_csv → solo      │
       │                     │     metadata (8.788)   │
       │                     │                        │
       │                     ├─ CKAN bogota (3.996)   │
       │                     ├─ CKAN cali (768)       │
       │                     ├─ CKAN valle (56)       │
       │                     └─ DCAT medellin (413)   │
       │                        (MEDATA, prot. nuevo) │
       │                                              │
       └──────────────────────────────────────────────┘
```

**Cobertura curatorial (Hito R + follow-ups):**
- `entity_id` 99.6%, `cobertura_geografica` 95.5%, `jurisdiccion_nivel` 95.4%,
  `license_id` 94.7%, `update_frequency` 58.6% (CKAN Bogotá/Cali/Valle 97-100%,
  datos.gov.co federados solo los DCAT ISO 8601).

## Tablero PowerBI — vistas paralelas decisor (Hito R)

Dos versiones del CSV servidas por `api/routes/dashboard.py`:

- **Legacy** `/api/v1/dashboard/datasets.csv` y `/entities.csv` →
  `v_dataset_status` (34 cols) y `v_entity_summary` (11 cols).
- **Decisor** `/api/v1/dashboard/datasets_decisor.csv` y
  `/entities_decisor.csv` → `v_dataset_status_decisor` (29 cols, -26% tamaño)
  y `v_entity_summary_decisor` (14 cols, +3 derivadas: `pct_verdes`,
  `n_datasets_directos`, `n_datasets_federados`).

Drop en decisor: alias literales (`view_count`, `data_updated_at`,
`frecuencia_declarada`), técnicos (`api_url`), telemetría ETL
(`last_refreshed_at` → header HTTP `Last-Modified`).

Coexisten 2-4 semanas para migrar el `.pbix` del Director sin romper
queries M.

## Ingestión — ETL y harvesting

- **`scripts/etl_refresh_catalog.py`** (diario 05:00 UTC):
  - Pasada 1 (Discovery): nativos + federated_href de datos.gov.co.
  - Pasada 2 (SODA + Metadata): row_count (incremental), engagement,
    license_id, comments, ratings.
- **`scripts/harvest_ckan.py --portal bogota|cali|valle`** (semanal):
  - `/api/3/action/package_search` paginado.
  - Extractores por portal con licencia/sector/frecuencia (Hito R):
    Cali → 10 keys de `extras` consistentes;
    Bogotá → 42 keys top-level + GeoJSON `spatial`;
    Valle → 35 keys custom (`frecuencia_actualizacion`, `categoría`).
- **`scripts/harvest_dcat.py --portal medellin`** (Hito R FU.1):
  - DCAT JSON-LD (Project Open Data v1.1) en `/data.json`.
  - 413 datasets MEDATA, mapeo: `identifier`/`title`/`license` (URL CC) /
    `accrualPeriodicity` (R/P* ISO 8601) / `theme[0]` / `publisher.name`.

## Motor de consulta — flujo source-aware

```python
# api/routes/chips.py — query_chips_execute()
if source_type == "federated":
    if federated_status != "ok":
        return error "Solo descubrible"
    cols = duckdb.describe_csv(data_url)   # via httpfs o cache disk
    sql = build_duckdb_sql(tipo, cols, data_url)
    rows = duckdb.execute_csv(data_url, sql)
elif source_type == "socrata":
    if tipo == "Cuántos" and row_count is not None:
        return row_count  # fast-path, sin SODA
    cols = SELECT * FROM dataset_columns_curated WHERE dataset_id=...
    soql = build_soql(tipo, cols)
    rows = SodaClient.query(dataset_id, soql)
```

## Verificación y observabilidad

- **`eval/run_eval_chips.py`** + `eval/golden_chips.yaml` (18 casos · 18/18 pass).
- **`chips_telemetry`** (Migración 019): elapsed_ms, row_count, soql_chars,
  hallucinated, error por endpoint. NL queries hasheadas para privacidad.
- **Tablero PowerBI**: `v_dataset_status` → `/api/v1/dashboard/datasets.csv`,
  34 columnas certificadas vs Socrata.

## Tooling externo

- **DuckDB** ≥1.0 con `httpfs` para CSVs federados.
- **DuckDB cache disk-backed**: `/app/data/csv_cache/`, TTL 24h, cap 200 MB.
- **Cloudflare Tunnel + nginx**: expone `datosvivos.co` a internet, sin
  abrir puertos en la VM.

## Bodega local Parquet (farmeo, 2026-07-12)

```
  ETL diario ──► regla de cola (farm_datasets --daily)
                   │  refresca fuentes cambiadas · entra-uno-sale-uno
                   ▼
  data/lake/{id}.parquet  ◄── manifest: dataset_snapshots (migración 027)
                   ▲
  /query/chips/execute ── snapshot FRESCO → DuckDB sobre Parquet local (ms)
                        └─ fuente cambió / no está → camino VIVO (SODA/CSV)
```

Prioridad determinista (valor por GB), presupuesto de disco con caps por dataset
(bytes + tiempo + pre-chequeo con conteos vivos), solo tabulares, advisory lock.

## Referencias

- ADR-017 IA razona / motor verifica.
- ADR-018 UI transparencia (Ver SoQL).
- ADR-019 DuckDB para federados.
- ADR-020 CKAN harvest directo.
- ADR-022 motor NL2SQL generativo verificado (3 capas).
- ADR-023 home panorama para tomadores de decisiones.
- `eval/reports/data_quality_hito_q_2026-05-29.md` (audit cierre).
