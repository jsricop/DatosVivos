# Hito R + 4 follow-ups — cierre consolidado 2026-06-08

Catálogo final: **23.854 datasets** (+5.452 vs 2026-05-29 snapshot de 18.402).

## Resumen ejecutivo

Día completo de trabajo sobre la calidad del catálogo. Empezando con la
pregunta del Director ("¿qué columnas sirven realmente al tablero?"), el
audit reveló que las vistas del PowerBI tenían 3 problemas conceptuales
distintos: (1) duplicados literales del ETL, (2) NULL legítimo confundido
con bug, (3) bugs reales de cobertura en federados. Las 7 migraciones de
hoy (020-024 + refactor harvesters + endpoints + header HTTP) cierran los
tres frentes:

- **Vistas paralelas `_decisor`** (29 cols vs 34 originales) coexisten con
  las viejas para migración gradual del .pbix sin downtime.
- **Curación CKAN** (Bogotá/Cali/Valle): 4.820 datasets cosechados con
  refactor por-portal (extras Cali, top-level Bogotá+Valle). Cobertura
  license_id/update_frequency/sector subió de 0% a 97-100%.
- **Nuevo portal MEDATA** (DCAT JSON-LD): 413 datasets de Medellín
  agregados al catálogo, **100% en TODAS las 7 cols curatorias**.
- **Curación datos.gov.co federados**: license_id desde
  `Common-Core_License` (94.7% global), jurisdicción desde
  `entities.divipola` (territoriales + nacionales) y reglas explícitas
  para las 14 entities descentralizadas core.
- **Seedeado de 38 publishers huérfanos** (38 Bogotá distritales + Cali +
  2 nacionales) → `entity_id` global 92.3% → 99.6%.

## Cobertura final por columna (global, 23.854 datasets)

| Columna | Inicio sesión | Fin sesión | Δ |
|---|---:|---:|---:|
| `entity_id` | 90.7% federados | **99.6%** | +9 pts |
| `cobertura_geografica` | 36% global (0% federados) | **95.5%** | +59 pts |
| `jurisdiccion_nivel` | 36% global (0% federados) | **95.4%** | +59 pts |
| `license_id` | 0% federados | **94.7%** | +95 pts |
| `update_frequency` | 38% global | **58.6%** | +21 pts |
| `sector` | 28% global | **56.6%** | +29 pts |

## Cobertura por portal (final)

| Portal | n | entity | cobertura | jurisdic | license_id | freq | sector |
|---|---:|---:|---:|---:|---:|---:|---:|
| datos.gov.co (Socrata + fed) | 18.402 | 99.7% | 94.3% | 94.3% | 95.0% | 48.1% | 45.6% |
| CKAN Bogotá | 3.996 | 99.9% | 100% | 100% | 97.3% | 97.2% | 97.2% |
| CKAN Cali | 768 | 97.7% | 100% | 100% | 98.2% | 100% | 100% |
| **DCAT MEDATA** | 413 | **100%** | **100%** | **100%** | **100%** | **100%** | **100%** |
| CKAN Valle | 56 | 98.2% | 100% | 100% | 100% | 100% | 98.2% |
| (sin portal — legacy) | 219 | 96.3% | 91.3% | 83.6% | 6.8% | 7.8% | 0.9% |

MEDATA es el **gold standard**: protocolo DCAT JSON-LD muy limpio, todos
los campos curatorios al 100%.

## Migraciones aplicadas (orden cronológico)

| # | Migración | Efecto |
|---|---|---|
| 020 | `backfill_ckan_jurisdiccion.sql` | Cobertura/jurisdicción Bogotá/Cali/Valle por `source_portal` default (4.625 UPDATE) |
| 021 | `dashboard_decisor.sql` | Vistas `v_dataset_status_decisor` (29 cols) y `v_entity_summary_decisor` (14 cols) |
| 022 | `curate_datos_gov_co_federated.sql` | license_id desde Common-Core_License (9.938) + jurisdicción para territoriales (576) y nacionales (209) |
| 023 | `curate_descentralizadas.sql` | 14 entities core → 7.728 datasets curados (IGAC, XM, SGC, ANLA, CAR Cundi/Cauca, SINCHI, Sec.Distritales) |
| 024 | `seed_orphan_publishers.sql` | 41 publishers nuevos en `entities` + 1.734 entity_id resueltos + 612 jurisdicciones curadas |

## Refactors de código

- `scripts/harvest_ckan.py` — extractores por portal:
  - Cali: 10 keys de `extras` (Cobertura/Frecuencia/Sector/Orden/...)
  - Bogotá: 42 keys top-level + GeoJSON spatial + qua_summary
  - Valle: 35 keys custom (frecuencia_actualizacion, ciudad, departamento)
  - `_normalize_license_id`: CKAN (`cc-by-sa`) → vocab nativo (`CC_40_BY_SA`)
- `scripts/harvest_dcat.py` (NUEVO) — protocolo DCAT JSON-LD para MEDATA.
- `api/routes/dashboard.py` — whitelist `_VIEWS` extendida + header HTTP
  `Last-Modified` desde `MAX(last_refreshed_at)`.

## Endpoints públicos finales

| URL | View | Tamaño | Filas | Cols |
|---|---|---:|---:|---:|
| `/api/v1/dashboard/datasets.csv` (legacy) | `v_dataset_status` | ~11 MB | 23.854 | 34 |
| `/api/v1/dashboard/entities.csv` (legacy) | `v_entity_summary` | ~94 KB | 1.379 | 11 |
| **`/api/v1/dashboard/datasets_decisor.csv`** | `v_dataset_status_decisor` | **8.5 MB** | 23.854 | **29** |
| **`/api/v1/dashboard/entities_decisor.csv`** | `v_entity_summary_decisor` | ~98 KB | 1.379 | **14** |
| `/api/v1/dashboard/top.csv` (sin cambios) | `v_top_datasets` | <1 KB | 10 | 6 |

Header `Last-Modified` activo en todas las respuestas — Power BI puede
detectar frescura sin columna en el CSV.

## Lo que queda sin curar (NULL legítimo)

- **219 federados sin source_portal** (legacy de carga anterior): 91% con
  cobertura pero solo 7% con license_id/freq/sector. Diagnosticar fuente
  origen → posible re-cosecha o etiquetar.
- **~70 datasets con publisher genérico** ("Esri Colombia", `{{source}}`,
  Secretarías sin contexto inequívoco): NULL honesto, no inventar.
- **datos.gov.co federados `update_frequency` 48%**: la fuente no declara
  frecuencia para la mayoría (Common-Core_Update-Frequency solo 4.5%).
  NULL = "publisher no declara", no bug.

## Commits del día (en orden)

1. `feat(catalog): backfill jurisdicción/cobertura CKAN por source_portal` (mig 020)
2. `refactor(harvest): extractores por portal CKAN — license_id + sector + freq`
3. `feat(dashboard): vistas paralelas _decisor + endpoints CSV` (mig 021)
4. `docs(eval): reportes Hito R — inventario CKAN + audit drift + decisor`
5. `feat(harvest): cosechar MEDATA Medellín vía DCAT JSON-LD`
6. `feat(catalog): curación parcial federados datos.gov.co` (mig 022)
7. `feat(dashboard): header HTTP Last-Modified con MAX(last_refreshed_at)`
8. `fix(harvest): aceptar update_frequencies como string (Bogotá)`
9. `feat(catalog): clasificar descentralizadas + seedear publishers huérfanos` (mig 023+024)
10. `chore(ops): make harvest-medellin para MEDATA (DCAT)`

Todos pushed a `develop` y mergeados a `main` con `--no-ff`.

## Migración del .pbix de PowerBI (responsabilidad del Director)

1. Cambiar origen del modelo M de `/datasets.csv` → `/datasets_decisor.csv`
   y `/entities.csv` → `/entities_decisor.csv`.
2. Reescribir queries M que referencian columnas dropeadas:
   - `view_count` → `page_views_total`
   - `data_updated_at` → `rows_updated_at`
   - `frecuencia_declarada` → `update_frequency`
   - `api_url` → eliminar
   - `last_refreshed_at` → leer del header HTTP `Last-Modified` o quitar
3. Aprovechar las 3 nuevas columnas de `entities_decisor`:
   - `pct_verdes` para ranking de cumplimiento
   - `n_datasets_directos` / `n_datasets_federados` para split publicación

## Próximos pasos sugeridos (no aplicados)

- Investigar los 219 federados sin source_portal (legacy).
- Curar `update_frequency` para datos.gov.co federados — extracción más
  agresiva del payload Discovery o solicitar al MinTIC poblar el campo.
- Considerar agregar más portales DCAT: SINCHI Amazonas, ESRI Hub Catastro,
  portales departamentales (Antioquia, Atlántico).
- Dashboard de salud del catálogo: vista que muestre cobertura % por
  columna y portal, evolución temporal.
