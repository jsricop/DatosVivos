-- 017_license_id_dual.sql
--
-- Quick win — exponer el código de licencia (`CC_40_BY_SA`,
-- `Public_Domain`, etc.) además del nombre completo. El código viene de
-- Views API (`licenseId`) y permite agregaciones limpias en el tablero
-- (un valor por familia de licencia) que el string libre no permite.
--
-- Discovery API ya devuelve `metadata.license` (string completo, ya en
-- `datasets.license`). Views API expone `licenseId` que vamos a guardar
-- aparte en `datasets.license_id`. El ETL pasada 2 (`_enrich_one`) lo
-- captura cuando ya está llamando Metadata API para comments/rating.

BEGIN;

ALTER TABLE datasets ADD COLUMN IF NOT EXISTS license_id VARCHAR(80);

CREATE INDEX IF NOT EXISTS idx_datasets_license_id ON datasets(license_id);

COMMIT;
