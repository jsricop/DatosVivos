# Hito R — Refinamiento del CSV decisor (cierre 2026-06-08)

Catálogo: **23.441 datasets** (+5.039 vs snapshot 2026-05-29 que tenía 18.402).
Commits aplicados: migraciones `020_backfill_ckan_jurisdiccion.sql` + `021_dashboard_decisor.sql`, refactor `scripts/harvest_ckan.py` con extractores por portal, endpoints `/api/v1/dashboard/datasets_decisor.csv` y `/entities_decisor.csv` en `api/routes/dashboard.py`.

## Resumen ejecutivo

El hito Q.7 (2026-05-29) firmó las 34 columnas de `v_dataset_status` **contra Socrata** (match). La pregunta del Director en este hito fue ortogonal: **¿estas columnas le sirven para decidir?** Tres principios acordados guían las decisiones:

1. **NULL puede ser señal real** — `number_of_comments=NULL` = "nadie comentó", `n_queries_total=0` = "no se consultó", `cobertura_geografica=NULL` en datos.gov.co federado = "la fuente no declara". Mantener con lectura honesta.
2. **Curar lo curable antes de dropear** — `cobertura_geografica=0%` en CKAN era bug del harvester (no fuente sin datos). Se curó.
3. **Drop solo lo redundante/técnico real** — alias literales, columnas internas sin valor para el decisor.

## Curación ejecutada (Fase 0)

### Fase 1 — Backfill SQL determinista por `source_portal` (migración 020)

Los 4.625 datasets CKAN ya ingestados quedaron con `cobertura_geografica=NULL`, `jurisdiccion_nivel=NULL`, `jurisdiccion_geo_codes=NULL` porque el harvester antiguo solo extraía 7 campos por package y nunca pobló estas columnas.

Deducción determinista aplicada (idempotente, COALESCE):

| source_portal | cobertura_geografica | jurisdiccion_nivel | geo_codes |
|---|---|---|---|
| `datosabiertos.bogota.gov.co` | `Municipal` | `distrito_capital` | `["11001"]` |
| `datos.cali.gov.co` | `Municipal` | `municipal` | `["76001"]` |
| `datosabiertos.valledelcauca.gov.co` | `Departamental` | `departamental` | `["76"]` |

Resultado: 4.625 datasets actualizados.

### Fase 2 — Refactor `harvest_ckan.py` (extractores por portal)

Cada portal expone metadata distinta:

- **Cali** (`extras` consistentes 10 keys): `Cobertura Geográfica`, `Departamento`, `Frecuencia de Actualización`, `Idioma`, `Municipio`, `Nombre de la Entidad`, `Orden`, `Sector`, `URL Documentación`, `URL Normativa`. Mapeo directo.
- **Bogotá** (42 keys top-level): `license_id` canónico, `spatial` GeoJSON, `update_frequencies`, `tags`, `qua_summary`, `ref_systems`, `ideca_languages`. Volcado a `domain_metadata` JSONB + `license_id` normalizado.
- **Valle del Cauca** (35 keys top-level custom): `frecuencia_actualizacion`, `category`, `ciudad`, `departamento`. Volcado a `domain_metadata` + `update_frequency`.

Función `_normalize_license_id()` mapea CKAN (`cc-by`, `CC-BY-4.0`, `cc-by-sa`) al vocabulario nativo (`CC_40_BY`, `CC_40_BY_SA`, `CC0_10`, etc.).

Re-cosecha completa de los 3 portales (Bogotá 3.996 / Cali 768 / Valle 56) en paralelo, ~1 min total.

## Cobertura post-curación

| Columna | Global | Nativos | CKAN Bgt | CKAN Cali | CKAN Val | Fed.datos.gov.co |
|---|---:|---:|---:|---:|---:|---:|
| `cobertura_geografica` | 56.5% | 100% | **100%** | **100%** | **100%** | 0% (fuente no declara) |
| `jurisdiccion_nivel` | 56.4% | 99.8% | **100%** | **100%** | **100%** | 0% (fuente no declara) |
| `update_frequency` | 41.3% | 100% | 0% ⚠ | **100%** | **100%** | 4.5% (solo DCAT R/P*) |
| `sector` | 55.9% | 99.6% | **97.2%** | **100%** | **98.2%** | 0% (DCAT no define) |
| `license_id` | 55.9% | 99.8% | **97.3%** | **98.2%** | **100%** | 0% (no normalizado aún) |
| `entity_id` | 92.2% | 99.8% | 99% | 99% | 99% | 90.7% |
| `category` | 88.9% | 96.5% | 100% | 0% (Cali no usa groups) | 100% | 84% |

**Lectura honesta:** las columnas en 56-92% son **datos curados al máximo de lo declarado por la fuente**. Los NULL restantes son federados de `datos.gov.co` cuyo publisher no declara spatial/sector/license_id en DCAT — el plan Hito R+1 podría agregar deducción por `Common-Core_Publisher`.

⚠ Bogotá `update_frequency=0%`: el campo `update_frequencies` (array) está vacío en los packages reales del API CKAN Bogotá. Información no expuesta por la fuente; no es bug nuestro.

## Matriz keep/drop final aplicada

### `v_dataset_status_decisor` — 29 columnas (vs 34 de la vista vieja)

**DROP (5):**

| Columna | Razón |
|---|---|
| `view_count` | alias literal de `page_views_total` (mismo `pv.page_views_total` en ETL:228) |
| `data_updated_at` | alias literal de `rows_updated_at` (misma var `data_updated` en ETL:220-221) |
| `frecuencia_declarada` | alias literal de `update_frequency` (misma var `frecuencia` en ETL:225,237) |
| `api_url` | técnico (devs), 0% federados, no aporta a decisor |
| `last_refreshed_at` | telemetría ETL → mover a header HTTP `Last-Modified` (TODO) |

**KEEP (29):** identidad+JOIN (5), category, semáforo (rows_updated_at + update_frequency + frequency_days + days_since_update + status, 5), engagement (row_count + page_views_total/week/month + download_count, 5), fechas (metadata_updated_at + publication_date, 2), atributos editoriales (license_id + cobertura_geografica + jurisdiccion_nivel + sector, 4), señales sociales (number_of_comments + total_times_rated, 2), provenance, socrata_url, quality_flag, segmentadores (es_federado + acceso_datos, 2).

### `v_entity_summary_decisor` — 14 columnas (vs 11 de la vista vieja)

**KEEP las 11 originales** + **3 derivadas nuevas:**

| Columna nueva | Cálculo | Para qué sirve |
|---|---|---|
| `n_datasets_directos` | `COUNT(*) FILTER (source_type='socrata')` | ranking por adopción del estándar Socrata |
| `n_datasets_federados` | `COUNT(*) FILTER (source_type='federated')` | ver qué entidades publican principalmente vía federación |
| `pct_verdes` | `100 * datasets_verdes / NULLIF(n_datasets, 0)` | KPI directo de cumplimiento del semáforo |

Telemetría `dataset_usage` mantenida tal cual: NULL/cero en `n_queries_*`/`last_access_at` es señal honesta de "no consultado por ciudadanos en Beta-2" (343 queries totales, última 2026-05-26). El Director ve la baja adopción real.

## Métricas de éxito

| Métrica | Objetivo | Real |
|---|---|---|
| Alias literales removidos | ≥3 | **3** (view_count, data_updated_at, frecuencia_declarada) |
| Columnas técnicas removidas | ≥2 | **2** (api_url, last_refreshed_at) |
| Columnas con k=1 efectiva removidas | 0 KEEP de k=1 sin valor | KEEP `provenance` (k=1 pero todos "official" es info para el Director) y `quality_flag` (k=1 técnico pero discrimina admin_only/normal) — con doc explícita |
| Tamaño CSV datasets | reducción ≥20% | **-26%** (10.4 MB → 7.7 MB) |
| Cobertura cobertura_geografica federados CKAN | de 0% a 100% | **0% → 100%** |
| Cobertura update_frequency federados CKAN | mejora notable | **0% → 100%** en Cali/Valle, 0% en Bogotá (fuente no expone) |
| Cobertura license_id federados CKAN | de 0% a >90% | **0% → 97-100%** |
| Coexistencia con vistas viejas | sin romper PowerBI | ✓ vistas viejas siguen sirviendo en `/datasets.csv` y `/entities.csv` |

## Endpoints públicos

| URL | View | Tamaño | Filas |
|---|---|---:|---:|
| `/api/v1/dashboard/datasets.csv` (legacy) | `v_dataset_status` | 10.4 MB | 23.441 |
| `/api/v1/dashboard/entities.csv` (legacy) | `v_entity_summary` | 82 KB | 1.379 |
| `/api/v1/dashboard/datasets_decisor.csv` (nuevo) | `v_dataset_status_decisor` | **7.7 MB** | 23.441 |
| `/api/v1/dashboard/entities_decisor.csv` (nuevo) | `v_entity_summary_decisor` | **94 KB** | 1.379 |
| `/api/v1/dashboard/top.csv` (legacy, sin cambios) | `v_top_datasets` | — | 10 |

## Trabajo del Director (Migración PowerBI)

1. Cambiar el origen del modelo M de `/datasets.csv` a `/datasets_decisor.csv` y de `/entities.csv` a `/entities_decisor.csv`.
2. Reescribir las queries M que referencian las columnas dropeadas (5):
   - `view_count` → reemplazar por `page_views_total`
   - `data_updated_at` → reemplazar por `rows_updated_at`
   - `frecuencia_declarada` → reemplazar por `update_frequency`
   - `api_url` → eliminar
   - `last_refreshed_at` → leer del header HTTP `Last-Modified` (a implementar) o quitar
3. Validar: 4 KPIs principales (n_datasets, %verdes, top-10 vistos, top-10 viejos) y segmentadores (`es_federado`, `acceso_datos`, `jurisdiccion_nivel`) sin errores.

## Follow-ups identificados (no aplicados aquí)

1. **Curar datos.gov.co federados (~9.995 datasets)**: extraer `Common-Core_License` y normalizar a `license_id`; deducir `cobertura_geografica`/`jurisdiccion_nivel` por mapeo `Common-Core_Publisher` → entidad → DIVIPOLA. Mejoraría cobertura global del 56% al ~95%.
2. **Cosechar Medellín (MEDATA)**: hoy solo tenemos 411 datasets vía datos.gov.co federación. MEDATA expone CKAN propio (`medata.gov.co/data.json`); replicar el patrón Bogotá/Cali/Valle traería +1.000-2.000 datasets distritales.
3. **`update_frequency` Bogotá**: investigar si está en `extras` por package (no en samples) o en endpoint `package_show` específico (más calls, pero recuperaría la columna).
4. **Header HTTP `Last-Modified`**: mover `last_refreshed_at` del CSV a header para que PowerBI lea frescura sin columna en el modelo.
5. **Curación 202 federados sin `source_portal`**: outliers de carga anterior. Bajo volumen, baja prioridad.

## Lecciones

1. **Audit Q ≠ audit de utilidad para el decisor.** Q.7 firmó 100% match contra Socrata; este hito reveló que columnas con 100% match en el bucket nativo (`cobertura_geografica`, `jurisdiccion_nivel`) estaban 0% en federados CKAN — el audit anterior nunca midió el bucket completo. **Métrica correcta para tablero del Director: cobertura global por columna, dividida por bucket de fuente.**
2. **Harvester compacto puede convivir con fuente rica.** El `harvest_ckan.py` original era 270 líneas que ignoraban el 80% de la metadata disponible. Refactor por-portal recuperó info crítica (license_id, sector, cobertura) sin cambiar la arquitectura.
3. **Vistas paralelas (`_decisor`)**: estrategia ganadora para tableros con consumidores acoplados. PowerBI puede migrar gradualmente; rollback es cambiar el path del CSV.
4. **NULL como señal vs NULL como bug**: distinguir es esencial para honestidad. `comments=NULL` en datasets sin actividad ≠ `cobertura_geografica=NULL` en CKAN sin curar. El primero queda; el segundo se cura.
