-- 013_ckan_harvest_source.sql
--
-- Reto F.5 — habilita harvesting de portales CKAN sub-nacionales
-- (Bogotá Datos Abiertos primero, luego Cali/Valle/otros).
--
-- Sólo añade `source_portal`. NO cambio el tipo de `dataset_id`:
-- el formato `bog-<16hex>` cabe en VARCHAR(20) existente (20 chars exactos),
-- y los views v_dataset_status / v_entity_summary dependen del column, lo
-- que obligaría a DROP+RECREATE. No vale la pena la cirugía hoy.
--
-- Aditivo, no-destructivo. Backfill 'datos.gov.co' a los existentes.

BEGIN;

ALTER TABLE datasets ADD COLUMN IF NOT EXISTS source_portal VARCHAR(80);
UPDATE datasets SET source_portal = 'datos.gov.co' WHERE source_portal IS NULL;

CREATE INDEX IF NOT EXISTS idx_datasets_source_portal ON datasets(source_portal);

COMMIT;
