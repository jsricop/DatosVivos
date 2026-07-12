# Diccionario de datos

> Esquema al corte del **2026-07-10**. La fuente única del tablero Power BI, del
> panorama web y de los CSV públicos es la vista `v_dataset_status_decisor`.

## Variables seleccionadas — vista `v_dataset_status_decisor` (29 columnas)

Una fila por dataset del catálogo integrado. Es el producto curado del pipeline
(ver [marco metodológico](marco_metodologico.md), fase 2).

### Identidad y publicador

| Columna | Tipo | Descripción |
|---|---|---|
| `dataset_id` | texto | Identificador único (4x4 Socrata o sintético del harvest) |
| `dataset_name` | texto | Título del dataset |
| `entity_id` | entero | FK a la entidad publicadora (puede ser nulo si no hay match) |
| `entity_name` | texto | Nombre canónico de la entidad |
| `entity_abbrev` | texto | Sigla de la entidad (cobertura parcial) |
| `category` | texto | Tema/categoría declarada |
| `sector` | texto | Sector administrativo (100 % en nativos y CKAN; nulo en federados de datos.gov.co) |

### Frescura (el semáforo)

| Columna | Tipo | Descripción |
|---|---|---|
| `rows_updated_at` | fecha | Última actualización DEL DATO (no de la metadata) |
| `update_frequency` | texto | Frecuencia de actualización declarada por la entidad |
| `frequency_days` | entero | Frecuencia convertida a días (nulo si no se puede interpretar) |
| `days_since_update` | entero | Días desde la última actualización |
| `status` | texto | **Semáforo**: `verde` (≤ frecuencia declarada) · `amarillo` (≤ 2×) · `rojo` (> 2×) · `desconocido` (sin fecha) |
| `metadata_updated_at` | fecha | Última actualización de la metadata |
| `publication_date` | fecha | Fecha de publicación |

### Uso y tamaño

| Columna | Tipo | Descripción |
|---|---|---|
| `row_count` | entero | Filas del dataset (solo nativos; nulo en federados) |
| `download_count` | entero | Descargas acumuladas (nulo = la fuente no lo reporta, típico en federados) |
| `page_views_total` / `page_views_last_week` / `page_views_last_month` | entero | Vistas de la página del dataset |
| `number_of_comments` / `total_times_rated` | entero | Señales sociales (nulo = sin interacción) |

### Acceso, procedencia y territorio

| Columna | Tipo | Descripción |
|---|---|---|
| `acceso_datos` | texto | `directo` (consulta inmediata vía API SODA) · `requiere_herramienta` (archivo externo descargable) · `solo_metadatos` (no tabular: mapas, geoservicios, documentos) |
| `es_federado` | texto | `sí` / `no` — si llegó por federación o es nativo Socrata |
| `provenance` | texto | `official` / `community` |
| `license_id` | texto | Licencia (vocabulario controlado) |
| `cobertura_geografica` | texto | Municipal / Departamental / Nacional |
| `jurisdiccion_nivel` | texto | `nacional` · `departamental` · `municipal` · `distrito_capital` · `multi` · `desconocido` |
| `quality_flag` | texto | Nulo/`ok` = dato temático · `admin_only` = reporte administrativo Ley 1712 (clasificación automática continua) |
| `socrata_url` | texto | Enlace a la página pública del dataset en su portal |

## Tabla base `datasets` (columnas adicionales relevantes)

La tabla núcleo tiene 42 columnas; las que agregan a la vista:

| Columna | Descripción |
|---|---|
| `jurisdiccion_geo_codes` | Códigos DIVIPOLA (JSONB): `"11"` = departamento, `"05001"` = municipio. Base del mapa por departamento |
| `jurisdiccion_confidence` / `jurisdiccion_reason` | Confianza y justificación de la inferencia territorial |
| `source_type` | `socrata` (nativo) / `federated` |
| `source_portal` | Portal del que se cosechó (datos.gov.co, CKAN territoriales, MEDATA) |
| `data_url` / `data_format` | URL y formato del archivo externo (federados con CSV) |
| `api_url` | Endpoint JSON SODA (nativos) |

## Tabla `entities`

| Columna | Descripción |
|---|---|
| `entity_id`, `name`, `abbrev` | Identidad canónica de la entidad publicadora |
| `kind` | `nacional` · `territorial` · `descentralizada` |
| `divipola_departamento` / `divipola_municipio` | Sede del publicador (moda del DIVIPOLA de sus datasets) |

## API pública de estadísticas (contratos JSON)

- **`GET /api/v1/stats/catalog`** — inventario bruto: total, nativos/federados, acceso,
  útiles/administrativos.
- **`GET /api/v1/stats/panorama`** — el panorama de la home: total, `n_entidades`,
  `composicion` (temáticos/administrativos), `semaforo` (4 estados), `acceso`
  (3 modos), `por_sector` (top 10 con datasets y entidades), `por_departamento`
  (DIVIPOLA con nombre), `por_portal` (6 portales de origen), `nacional_sin_geo`,
  `generated_at`. Caché de 5 minutos.
- **`GET /api/v1/dashboard/datasets_decisor.csv`** y **`/entities_decisor.csv`** —
  exportes completos de las vistas para el tablero Power BI (públicos).

## Tabla `dataset_snapshots` (manifest de la bodega Parquet)

Una fila por dataset farmeado a la bodega local (migración 027). Es el checkpoint del
farmeo (reanudable) y la fuente de la decisión bodega-vs-vivo del buscador.

| Columna | Descripción |
|---|---|
| `dataset_id` | PK, referencia al catálogo |
| `status` | `downloaded` · `too_big` (no cabe, skip permanente) · `failed` · `evicted` (rotado por la cola) |
| `priority_score` | Valor-por-GB al momento de puntuar (uso real + engagement + frescura ÷ tamaño) |
| `bytes` / `rows` | Tamaño REAL del Parquet y filas |
| `parquet_path` | Ruta del archivo en la bodega (`data/lake/`) |
| `source_updated_at` | `rows_updated_at` del catálogo al descargar — si difiere del actual, el snapshot está viejo y el buscador va al dato vivo |
| `downloaded_at` / `last_scored_at` / `error` | Trazabilidad |

## Vista `v_entity_summary_decisor` (14 columnas, una por entidad)

`n_datasets`, `n_datasets_directos`, `n_datasets_federados`, semáforo agregado
(`datasets_verdes/amarillos/rojos/sin_fecha`), **`pct_verdes`** (indicador de
cumplimiento por entidad) y telemetría de consultas (`n_queries_30d`, `n_queries_total`,
`last_access_at`).
