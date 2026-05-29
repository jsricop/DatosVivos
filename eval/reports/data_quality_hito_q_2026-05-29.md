# Hito Q — Calidad de datos del catálogo DatosVivos

Fecha: 2026-05-29 · Branch: main · Commit cabeza: `f6c9869`

## Resumen ejecutivo

Validación columna-por-columna del catálogo local (`datasets`, `dataset_columns_curated`) contra la fuente autoritativa (Socrata Discovery + Views API) sobre el dominio completo `www.datos.gov.co`. Resultado:

| Capa | Filas auditadas | Columnas a 100% | Hallazgos reales |
|---|---:|---:|---|
| `datasets` nativos | 8.404 | 17/18 (94%) | Ninguno; description "mismatch" es artefacto del comparador |
| `datasets` federados | 9.995 | 17/18 (94%) | Ninguno; mismo artefacto |
| `dataset_columns_curated` nativos | 5.612 (76.774 filas) | nombres 100% / counts 66.4% | Diff de count es diseño (Socrata expande columnas de tipo location) |
| Views API spot-check | 200 random | 2/2 (100%) | `number_of_comments` y `total_times_rated` perfectos |

**Conclusión:** el catálogo es fidedigno. No hay extracción incorrecta. El único hueco previo (federados ignorados, 9.995 datasets) **fue cerrado en este hito** vía migración 009 + extensión del ETL para leer DCAT Common-Core_*.

## Trabajo ejecutado

| Paso | Resultado | Commit |
|---|---|---|
| Q.0 ETL refresh + snapshot pre-audit | 8.407 nativos congelados antes de medir | (snapshot DB) |
| Q.1 Harness `audit_data_quality.py` + run nativos | 17/18 columnas a 100% | `9d5e632` |
| Q.2 Views API spot-check 200 random | 100% en comments + rated | (inline script) |
| Q.5 Audit `dataset_columns_curated` vs Discovery | nombres 100%, count diff = sub-columnas location | (inline script) |
| Q.3 Migración 009 + ETL federados DCAT | 9.995 federados ingestados, 1.207 con `data_url` | `1a56c56` + `1bd14de` |
| Q.3 Re-run audit federados | 17/18 columnas a 100% | (re-run) |

## Métricas claves de cobertura

**Universo del dominio (Socrata Discovery `resultSetSize`):**
- `only=dataset`: 8.404 (nativos, todos en SODA).
- `only=federated_href`: ≥10.000 (capped por Discovery; el conteo real puede ser mayor).
- Total local post-Q.3: **18.402 datasets** en `datasets`.

**Federados con CSV accesible (`federated_status='ok'`):** 1.207 de 9.995 = 12,1%.
Los demás 8.788 declaran ser federados pero no exponen `metadata.access_points["text/csv"]`. Esos quedan descubribles en chips/búsqueda pero no consultables hasta que Reto F.4 (DuckDB sobre data_url) se complete y se elija una estrategia de fallback.

## Falsos positivos del audit (no son bugs)

1. **`description` mismatch en 10 nativos + 65 federados.** Causa: el comparador NFC-normaliza la fuente y luego trunca a 2000; el ETL trunca primero (raw) y guarda. NFC puede comprimir codepoints, así que truncar antes/después de normalizar da strings de longitud distinta cerca del límite. La data subyacente es idéntica. _Acción: ninguna; documentado._
2. **Diff de COUNT de columnas en 2.824 nativos (33,6%).** Causa: Socrata genera columnas auto-derivadas para campos tipo `location` (`_address`, `_city`, `_state`, `_zip`). El ETL las excluye porque no son columnas "reales" del dataset. _Acción: ninguna; comportamiento intencional._
3. **`metadata_updated_at` 1 mismatch.** Causa: lag entre la extracción ETL (14:18 UTC) y el SELECT del audit (15:37 UTC); Socrata actualizó la metadata en ese intervalo. _Acción: ninguna; es lag legítimo, no bug._

## Bug real cerrado en este hito

**Federados sin extraer.** El ETL hardcoded `only=dataset` en `DiscoveryClient.search`, excluyendo ≥10.000 datasets `federated_href` (MEDATA/Medellín y otros con portal propio que se publican vía DCAT en datos.gov.co). Sus 32 columnas estaban todas vacías.

**Solución (migración 009 + cambios en ETL):**
- Discovery client parametriza `only`.
- `_discovery_sweep` hace dos pasadas (nativos + federados).
- `_extract_discovery` detecta `resource.type=='federated_href'` y lee:
  - `Common-Core_Publisher` → `entity_raw`
  - `Common-Core_Theme` → `category`
  - `Common-Core_Update-Frequency` → `update_frequency` / `frecuencia_declarada`
  - `Common-Core_Spatial` → `cobertura_geografica`
  - `Common-Core_License` → `license`
  - `metadata.access_points["text/csv"]` → `data_url` + `data_format='csv'`
- `_needs_enrichment` skip federados (SODA `count(*)` no aplica).
- `_upsert_dataset` persiste `source_type`, `data_url`, `data_format`, `federated_status`.

Post-fix: 9.995 federados con 17/18 columnas a 100% match contra Socrata.

## Limitaciones conocidas

1. **Cap del Discovery a offset≈10.000.** Socrata corta paginación más allá. Si el universo real de federados supera 10.000, no los vemos por este endpoint. Fallback futuro: pasadas filtradas por `categories=` o `q=` para extender más allá del cap. _Fuera de alcance hoy._
2. **El sector DCAT no tiene equivalente.** Federados terminan con `sector=NULL` siempre (el estándar DCAT no define ese campo). _Aceptado como vacío con razón documentada._
3. **`license` de federados es URL no string.** Ej. `http://creativecommons.org/licenses/by-sa/4.0/legalcode` (federados) vs "Creative Commons Attribution | Share Alike 4.0 International" (nativos). Para el tablero ambas formas son legibles, pero la normalización a `license_id` (`CC_40_BY_SA`) sería un quick win futuro.

## Quick wins identificados (Q.4) — NO aplicados aquí

1. **Promover `Información-de-la-Entidad_DIVIPOLA-Municipio`** del JSONB a columna estructurada de `entities`. Es información del EDITOR, no de la cobertura del dataset → no debe ir a `jurisdiccion_geo_codes` (eso es cobertura). Va a `entities.divipola_municipio`. _Pendiente._
2. **Añadir `license_id`** (código corto) además del `license` (string). Aditivo, ayudaría a agregar por licencia en el tablero. _Pendiente._
3. **Decidir fuente única de engagement counts.** Hoy Discovery `resource.page_views.page_views_total` (cache, lag ~h-d) vs Views API `viewCount` (live). Para el tablero diario, Discovery sigue siendo suficiente — la diferencia siempre estuvo bajo el 5% que tolera el comparador. _Aceptado como tal; no se modifica._

## Reproducibilidad

```bash
# Re-correr audit completo
docker exec datosvivos-api-1 python -m scripts.audit_data_quality \
  --output /app/data/data_quality_<fecha>.md

# Re-correr audit de columnas técnicas
docker exec datosvivos-api-1 python -m scripts.audit_columns_curated \
  --output /app/data/columns_audit_<fecha>.md

# Snapshot manual del estado actual
docker exec datosvivos-postgres-1 psql -U dv -d datosvivos -c \
  "CREATE TABLE _audit_snapshot AS SELECT * FROM datasets;"
```

## Próximos pasos sugeridos

1. **Reto F.4** (Hito 2 del plan unificado): habilitar consulta sobre los 1.207 federados con `data_url` vía DuckDB. Sin esto, federados son descubribles pero no consultables.
2. **Cron diario en DevOps** ya monta el `etl_refresh_catalog --incremental` a las 05:00 UTC. Con el ETL ahora cubriendo federados, la pasada nocturna mantendrá los 18.402 frescos.
3. **Expandir seed de `entities`** para reducir los datasets que aún quedan con `entity_id=NULL` post-fix de resolver.
4. Quick wins Q.4 cuando haya ventana.
