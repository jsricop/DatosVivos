-- 013_ckan_harvest_source.sql
--
-- Reto F.5 — habilita harvesting de portales CKAN sub-nacionales
-- (Bogotá Datos Abiertos primero, luego Cali/Valle/otros). Cambios:
--
-- 1) `datasets.source_portal` nuevo: dominio del portal de origen.
--    - NULL/'datos.gov.co' para nativos Socrata y federados via datos.gov.co.
--    - 'datosabiertos.bogota.gov.co' para harvesting CKAN Bogotá.
--    - 'datos.cali.gov.co' para Cali, etc.
--
-- 2) `datasets.dataset_id` VARCHAR(20) → VARCHAR(40). Las IDs CKAN son
--    UUIDs (36 chars); usamos prefijo + 16 chars (`bog-<16hex>`) que
--    cabe en 20+pero limpio. Subimos a 40 por seguridad futura.
--
-- 3) FKs (`dataset_tags.dataset_id`, `dataset_columns_curated.dataset_id`)
--    también suben a VARCHAR(40) para mantener compatibilidad de tipo.
--
-- Aditivo, no-destructivo. Backfill datos.gov.co a los existentes.

BEGIN;

-- 1) source_portal
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS source_portal VARCHAR(80);
UPDATE datasets SET source_portal = 'datos.gov.co' WHERE source_portal IS NULL;

-- 2) Extender dataset_id y sus FKs
ALTER TABLE datasets ALTER COLUMN dataset_id TYPE VARCHAR(40);
ALTER TABLE dataset_tags ALTER COLUMN dataset_id TYPE VARCHAR(40);
ALTER TABLE dataset_columns_curated ALTER COLUMN dataset_id TYPE VARCHAR(40);

CREATE INDEX IF NOT EXISTS idx_datasets_source_portal ON datasets(source_portal);

COMMIT;
