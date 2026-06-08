-- 020_backfill_ckan_jurisdiccion.sql
--
-- Hito R — Fase 1: deducción determinista de cobertura/jurisdicción para los
-- 4.625 datasets cosechados vía CKAN harvest (Bogotá/Cali/Valle).
--
-- Problema: el harvester actual (scripts/harvest_ckan.py) extrae solo 7
-- campos por package CKAN. Los datasets quedaron con domain_metadata=NULL,
-- cobertura_geografica=NULL, jurisdiccion_nivel=NULL, jurisdiccion_geo_codes=NULL,
-- update_frequency=NULL, sector=NULL → cobertura 0% en el tablero.
--
-- Esta migración hace la deducción mínima determinista por source_portal,
-- garantizando cobertura ≥99% en las 3 columnas espacial/jurisdicción para
-- los CKAN ya ingestados. NO requiere re-cosechar.
--
-- Fase 2 (separada, refactor harvest_ckan.py) extraerá los campos restantes
-- (license_id, update_frequency, sector, qua_summary) desde las APIs CKAN
-- ricas en metadata.
--
-- Reglas:
--   Bogotá  → cobertura=Municipal, jurisdiccion=distrito_capital, codes=["11001"]
--   Cali    → cobertura=Municipal, jurisdiccion=municipal,        codes=["76001"]
--   Valle   → cobertura=Departamental, jurisdiccion=departamental, codes=["76"]
--
-- Idempotente: solo actualiza filas con valor NULL. Re-ejecutar es no-op.

BEGIN;

-- Bogotá D.C. (DIVIPOLA 11001)
UPDATE datasets SET
    cobertura_geografica   = COALESCE(cobertura_geografica, 'Municipal'),
    jurisdiccion_nivel     = COALESCE(jurisdiccion_nivel, 'distrito_capital'),
    jurisdiccion_geo_codes = COALESCE(jurisdiccion_geo_codes, '["11001"]'::jsonb),
    jurisdiccion_confidence = COALESCE(jurisdiccion_confidence, 'high'),
    jurisdiccion_inferred_at = COALESCE(jurisdiccion_inferred_at, NOW()),
    jurisdiccion_reason    = COALESCE(jurisdiccion_reason, 'CKAN Bogotá: deducción determinista por source_portal'),
    last_refreshed_at      = NOW()
WHERE source_portal = 'datosabiertos.bogota.gov.co'
  AND (cobertura_geografica IS NULL OR jurisdiccion_nivel IS NULL OR jurisdiccion_geo_codes IS NULL);

-- Cali (DIVIPOLA 76001)
UPDATE datasets SET
    cobertura_geografica   = COALESCE(cobertura_geografica, 'Municipal'),
    jurisdiccion_nivel     = COALESCE(jurisdiccion_nivel, 'municipal'),
    jurisdiccion_geo_codes = COALESCE(jurisdiccion_geo_codes, '["76001"]'::jsonb),
    jurisdiccion_confidence = COALESCE(jurisdiccion_confidence, 'high'),
    jurisdiccion_inferred_at = COALESCE(jurisdiccion_inferred_at, NOW()),
    jurisdiccion_reason    = COALESCE(jurisdiccion_reason, 'CKAN Cali: deducción determinista por source_portal'),
    last_refreshed_at      = NOW()
WHERE source_portal = 'datos.cali.gov.co'
  AND (cobertura_geografica IS NULL OR jurisdiccion_nivel IS NULL OR jurisdiccion_geo_codes IS NULL);

-- Valle del Cauca (DIVIPOLA 76 - departamento)
UPDATE datasets SET
    cobertura_geografica   = COALESCE(cobertura_geografica, 'Departamental'),
    jurisdiccion_nivel     = COALESCE(jurisdiccion_nivel, 'departamental'),
    jurisdiccion_geo_codes = COALESCE(jurisdiccion_geo_codes, '["76"]'::jsonb),
    jurisdiccion_confidence = COALESCE(jurisdiccion_confidence, 'high'),
    jurisdiccion_inferred_at = COALESCE(jurisdiccion_inferred_at, NOW()),
    jurisdiccion_reason    = COALESCE(jurisdiccion_reason, 'CKAN Valle del Cauca: deducción determinista por source_portal'),
    last_refreshed_at      = NOW()
WHERE source_portal = 'datosabiertos.valledelcauca.gov.co'
  AND (cobertura_geografica IS NULL OR jurisdiccion_nivel IS NULL OR jurisdiccion_geo_codes IS NULL);

COMMIT;

-- Verificación inmediata
SELECT source_portal,
       COUNT(*) AS n,
       ROUND(100.0*COUNT(cobertura_geografica)/COUNT(*),1) AS pct_cob_geo,
       ROUND(100.0*COUNT(jurisdiccion_nivel)/COUNT(*),1) AS pct_jur_nivel,
       ROUND(100.0*COUNT(jurisdiccion_geo_codes)/COUNT(*),1) AS pct_jur_codes
FROM datasets
WHERE source_type = 'federated'
GROUP BY 1
ORDER BY 2 DESC;
