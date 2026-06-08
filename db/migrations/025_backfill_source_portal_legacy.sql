-- 025_backfill_source_portal_legacy.sql
--
-- Hito R follow-up — los 219 datasets con `source_portal IS NULL` son
-- legacy del ETL pre-Hito Q (cuando `source_portal` no se poblaba para
-- nativos/federados de datos.gov.co). Verificado: 219/219 tienen
-- `socrata_url` apuntando a `https://www.datos.gov.co/d/{id}`.
--
-- Backfill determinista: source_portal='datos.gov.co' para todos los que
-- tengan socrata_url apuntando a ese dominio. Después se re-aplican las
-- curaciones 022 (license_id desde Common-Core_License) y 024 (publishers
-- huérfanos) — idempotentes con COALESCE, no rompen lo curado.
--
-- Aporta también: cobertura/jurisdicción heredada de 022/023 según
-- entity_kind, ya que ahora forman parte del bucket datos.gov.co.

BEGIN;

UPDATE datasets SET
    source_portal = 'datos.gov.co',
    last_refreshed_at = NOW()
WHERE source_portal IS NULL
  AND socrata_url LIKE 'https://www.datos.gov.co/%';

COMMIT;

-- Verificación
SELECT
  COUNT(*) FILTER (WHERE source_portal IS NULL) AS aun_sin_portal,
  COUNT(*) FILTER (WHERE source_portal = 'datos.gov.co') AS en_datos_gov_co
FROM datasets;
