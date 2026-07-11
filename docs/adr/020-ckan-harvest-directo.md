# ADR-020: Harvest CKAN directo de portales sub-nacionales

**Estado:** Aceptada
**Fecha:** 2026-05-29
**Contexto:** Auditoría Hito Q reveló que **datos.gov.co federa solo el 13% del catálogo de Bogotá Datos Abiertos** (276 de 2.112), 70% de Cali (468/663), 99% de Medellín (410/414), 100% de Valle (50/50). El gap más grande es Bogotá (~1.836 datasets faltantes), la plataforma sub-nacional más grande del país.

## Decisión

**Construimos un harvester CKAN genérico (`scripts/harvest_ckan.py`) que va directo a los portales municipales/departamentales y inserta los datasets con CSV en nuestro catálogo como `source_type='federated'`, marcados con `source_portal=<host>`.** Saltamos el paso intermedio de datos.gov.co.

Portales soportados (al 2026-05-29):
- `bogota` → `datosabiertos.bogota.gov.co` (id prefix `bog-`)
- `cali`   → `datos.cali.gov.co` (id prefix `cal-`)
- `valle`  → `datosabiertos.valledelcauca.gov.co` (id prefix `val-`)

## Razones

1. **Federación parcial es problema editorial.** datos.gov.co tiene una política de federación que el equipo central decide; no podemos esperar a que ellos prioricen lo que necesitamos.
2. **CKAN es estándar.** Todos los portales sub-nacionales colombianos serios usan CKAN (los que no usan Socrata). Mismo endpoint `/api/3/action/package_search`, misma estructura de resources.
3. **La pieza ya estaba construida.** Reto F.4.2 ya tenía el resolver CKAN para Cali (URLs page-style). Reusarlo para harvest fue marginal.
4. **Más datos = más relevancia para el ciudadano.** Pasamos de 18.402 a 23.027 datasets totales (+25%). De ~9.611 a ~14.232 consultables como tabla.

## Alternativas consideradas

1. **Esperar a que datos.gov.co complete la federación.** Sin garantías de fecha. Rechazado.
2. **Pedir a MinTIC que federe.** Trabajo institucional largo, no técnico. Lo dejamos como propuesta separada.
3. **Solo cosechar Bogotá** (el gap mayor). Rechazado — el harvester multi-portal sale del mismo trabajo y cubre Cali extendido + Valle + futuros.
4. **Construir un harvester DCAT-US generic.** Sobre-engineering — CKAN cubre el 95% de los portales colombianos con catálogo abierto.

## Limitaciones aceptadas

- **Solo extraemos resources con `format='CSV'`.** Resources de tipo Esri REST, WMS, WFS, SHP, GeoJSON, XLSX no se ingestan. Bogotá tiene un 50% de resources geo-servicios (catastro Bogotá) que requeriría un adaptador separado.
- **No re-harvesteamos automáticamente.** El cron diario está delegado a DevOps (no implementado al cierre de sesión).
- **Publishers sub-distritales** del CKAN no están en `entities`. Migración 014 + 016 sembró 30 publishers municipales (Cali + Valle), pero hay decenas más con menos de 10 datasets cada uno.
- **`dataset_id` formato `<prefix><16hex>`** (20 chars) cabe en VARCHAR(20) existente. Sin cambio de schema en `datasets` PK.
- **CKAN resources puede tener URLs page-style** (no termina en `.csv`). El executor F.4.2 resuelve con `resource_show` al query-time.

## Consecuencias

**Positivas:**
- 4.625 datasets nuevos sub-nacionales en el catálogo (Bogotá 3.801 + Cali 768 + Valle 56).
- Todos consultables como tabla (62% del catálogo total ahora consultable).
- El tablero PowerBI ahora muestra cobertura del catálogo distrital de Bogotá, no solo lo que datos.gov.co eligió federar.

**Negativas:**
- Mantenimiento incremental: cada portal puede romper su API CKAN (cambios de versión, deprecaciones).
- Dependencia de disponibilidad de los portales municipales (que históricamente tienen menor SLA que datos.gov.co).
- Resources duplicados: si datos.gov.co federa el mismo recurso después, podríamos tener duplicado con dos `dataset_id` distintos. Hoy no hemos visto colisiones masivas (los IDs Socrata son `xxxx-yyyy`, los nuestros `bog-<hex>` etc., así que no se chocan por PK, pero podrían apuntar al mismo CSV físicamente).

## Referencias

- ADR-017 (motor determinista), ADR-019 (DuckDB sobre CSVs).
- `scripts/harvest_ckan.py`, `db/migrations/013_ckan_harvest_source.sql`.
- Reto F.5 en `merry-puzzling-pie.md`.
- Datos sample auditados en `eval/reports/data_quality_hito_q_2026-05-29.md`.
