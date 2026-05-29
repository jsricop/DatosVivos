-- 009_federated_source.sql
--
-- Hito Q.3 — agrega columnas para soportar federated_href (datasets cuya
-- atribución es URL externa, ej. MEDATA/Medellín). Aditivo, no rompe
-- nativos. Idempotente.
--
-- - source_type   : 'socrata' (default, nativos en SODA) | 'federated' (URL externa).
-- - data_url      : URL del CSV/JSON real para federados (NULL para nativos).
-- - data_format   : csv | json | xls | otro.
-- - federated_status: ok | no_csv | unreachable (para degradación en Hito 2 F.5).

BEGIN;

ALTER TABLE datasets ADD COLUMN IF NOT EXISTS source_type VARCHAR(20);
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS data_url TEXT;
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS data_format VARCHAR(20);
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS federated_status VARCHAR(20);

UPDATE datasets SET source_type = 'socrata' WHERE source_type IS NULL;
ALTER TABLE datasets ALTER COLUMN source_type SET DEFAULT 'socrata';
ALTER TABLE datasets ALTER COLUMN source_type SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_datasets_source_type ON datasets(source_type);

COMMIT;
