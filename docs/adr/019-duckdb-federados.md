# ADR-019: DuckDB sobre CSVs externos para datasets federados

**Estado:** Aceptada
**Fecha:** 2026-05-29
**Contexto:** Reto F.4 cerrado. ~10.000 datasets en datos.gov.co son `federated_href` (atribución es URL externa, no SODA). Mas ~3.800 datasets de Bogotá CKAN harvested directamente. Total: ~14.000 datasets cuya consulta NO puede ir por SODA.

## Decisión

**Para datasets cuya `source_type='federated'` y tienen un CSV externo declarado (`data_url`), usamos DuckDB con la extensión `httpfs` para ejecutar SQL directamente sobre el CSV remoto.** El motor de consulta de Fase B se hace **source-aware**: dispatch por `source_type` a SoQL (nativos) o DuckDB (federados).

## Razones

1. **Misma capa, distinto motor.** El templating SQL es paralelo al SoQL (mismo contrato de 5 TIPOs, columnas curadas, validación pre-ejecución). La diferencia es:
   - **Nativos:** `SELECT ... FROM resource ?$query=...` contra SODA.
   - **Federados:** `SELECT ... FROM read_csv_auto('url')` contra DuckDB embebido.
2. **Sin dependencias adicionales en runtime.** DuckDB se distribuye como un wheel pequeño (~30 MB) y corre embebido en el mismo proceso de FastAPI. `httpfs` se carga al inicializar la conexión.
3. **Soporta agregaciones server-side.** A diferencia de descargar el CSV con pandas y agregar en Python, DuckDB hace `GROUP BY` / `count(*)` directamente en streaming, sin cargar todo en memoria.
4. **Curación de columnas en vuelo.** No tenemos `dataset_columns_curated` para federados (la curación corre solo sobre nativos). Antes de cada query corremos `DESCRIBE SELECT * FROM read_csv_auto LIMIT 0` para obtener el schema, y aplicamos `classify_column` (compartido con el path nativo). Decide `semantic_type` por nombre + tipo.

## Alternativas consideradas

1. **Descargar el CSV, parsear con pandas, agregar.** Funciona para datasets pequeños; explota con archivos de >100 MB. Memoria del contenedor (4 GB) se llena fácil. DuckDB streaming evita el problema.
2. **Cargar CSVs a Postgres.** Sería ideal para latencias <100ms, pero almacenar 14.000 tablas externas (algunos > 100 MB) requeriría replicación + cron. Operativamente caro.
3. **OData del portal.** Verificamos en mayo 2026: Socrata OData ignora `$apply`, así que no agrega server-side. Inaceptable.
4. **Esperar a que datos.gov.co habilite SODA para federados.** Decisión externa fuera de nuestro control.

## Limitaciones aceptadas

- **Primera query lenta** (3-13s por dataset, hace download + parse). Mitigado con cache disk-backed (`ai_engine/csv_cache.py`) TTL 24h.
- **CSV mal-codificados.** Fallback cascada: utf-8 → latin-1 → utf-16. Si el archivo es UTF-32 o ISO-8859-x, falla con error legible.
- **URLs CKAN-page-style** (Cali) requieren resolver via `/api/3/action/resource_show` antes de pasarlas a DuckDB. Implementado en `resolve_data_url`.
- **CSVs > 200 MB** no se cachean (cap por archivo); cada query los re-descarga via httpfs. Aceptado — son < 5% del catálogo.

## Consecuencias

**Positivas:**
- ~5.000 datasets federados consultables hoy con cifra real (mismo flujo de chips que nativos).
- Cero cambios en el frontend — el response shape es idéntico al de SoQL.
- DuckDB tiene `try_cast` que limpia automáticamente CSVs sucios donde una columna debería ser número pero llega como texto con basura.

**Negativas:**
- Dependencia nueva (`duckdb>=1.0`) en `requirements.api.txt`.
- Footprint de cache: ~450 MB max para todo el universo federado (estimado, cap 200 MB por archivo). Aceptado.

## Referencias

- ADR-017 (motor determinista).
- `ai_engine/duckdb_executor.py`, `duckdb_templates.py`, `csv_cache.py`.
- Migración 009 (`source_type`, `data_url`, `federated_status`).
- Reto F.4 / F.4 fase 2 / F.5 en `merry-puzzling-pie.md`.
