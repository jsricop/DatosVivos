-- 022_curate_datos_gov_co_federated.sql
--
-- Hito R follow-up FU.2 — curar los 9.995 federados de datos.gov.co.
--
-- Audit 2026-06-08 reveló que el bucket `datos.gov.co + source_type=federated`
-- tenía 0% en license_id, jurisdiccion_*, cobertura_geografica, sector
-- mientras los nativos y los CKAN curados estaban al 99-100%.
--
-- Dos fuentes a explotar (verificadas en datos reales):
--
-- 1. `domain_metadata->>'Common-Core_License'` (99.4% disponible = 9.938 datasets).
--    Es URL Creative Commons en varios formatos. Normaliza al vocabulario
--    nativo (CC_40_BY, CC_40_BY_SA, CC0_10, etc.) — mismo que usa
--    license_id en los nativos y CKAN.
--
-- 2. `entities.divipola_municipio / .divipola_departamento` (95.2% federados
--    con entity_id resuelto + 96.4% entities con divipola = 7.369 curables).
--    Mapea entity → DIVIPOLA → jurisdiccion_nivel + jurisdiccion_geo_codes
--    + cobertura_geografica.
--
-- Sin tocar: 477 federados sin entity_id (huérfanos publishers no seedeados);
-- ~50 con license value basura (https://example.com/license-not-found).
--
-- Idempotente: COALESCE no pisa valores ya curados (por mig 020 o ETL).

BEGIN;

-- =============================================================================
-- Paso 1: license_id desde Common-Core_License normalizado
-- =============================================================================
UPDATE datasets d SET
    license_id = COALESCE(
        d.license_id,
        CASE
            -- by-sa 4.0 (Creative Commons Attribution Share-Alike 4.0)
            WHEN lower(d.domain_metadata->>'Common-Core_License') ~ 'by-sa.*4\.0' THEN 'CC_40_BY_SA'
            -- by-nd 4.0 (Attribution No-Derivatives)
            WHEN lower(d.domain_metadata->>'Common-Core_License') ~ 'by-nd.*4\.0' THEN 'CC_40_BY_ND'
            -- by 4.0 (Attribution simple) — excluye by-sa/by-nd/by-nc
            WHEN lower(d.domain_metadata->>'Common-Core_License') ~ 'creativecommons\.org/licenses/by/4\.0'
                 OR lower(d.domain_metadata->>'Common-Core_License') ~ 'creativecommons\.org/licenses/by/$'
                THEN 'CC_40_BY'
            -- CC0 (public domain dedication)
            WHEN lower(d.domain_metadata->>'Common-Core_License') ~ 'publicdomain/zero'
                 OR lower(d.domain_metadata->>'Common-Core_License') ~ 'cc0' THEN 'CC0_10'
            -- by-nc-* y otros restrictivos: no mapean al vocab nativo, NULL legítimo
            ELSE NULL
        END
    ),
    last_refreshed_at = NOW()
WHERE d.source_portal = 'datos.gov.co'
  AND d.source_type = 'federated'
  AND d.license_id IS NULL
  AND d.domain_metadata ? 'Common-Core_License';


-- =============================================================================
-- Paso 2: jurisdicción/cobertura desde entities.divipola
-- =============================================================================
-- 2a) Entidades MUNICIPALES (con divipola_municipio)
UPDATE datasets d SET
    cobertura_geografica   = COALESCE(d.cobertura_geografica, 'Municipal'),
    jurisdiccion_nivel     = COALESCE(d.jurisdiccion_nivel, 'municipal'),
    jurisdiccion_geo_codes = COALESCE(d.jurisdiccion_geo_codes, to_jsonb(ARRAY[e.divipola_municipio])),
    jurisdiccion_confidence = COALESCE(d.jurisdiccion_confidence, 'high'),
    jurisdiccion_inferred_at = COALESCE(d.jurisdiccion_inferred_at, NOW()),
    jurisdiccion_reason    = COALESCE(d.jurisdiccion_reason, 'entities.divipola_municipio JOIN (FU.2)'),
    last_refreshed_at      = NOW()
FROM entities e
WHERE d.entity_id = e.entity_id
  AND d.source_portal = 'datos.gov.co'
  AND d.source_type = 'federated'
  AND e.divipola_municipio IS NOT NULL
  AND e.kind = 'territorial'
  AND (d.cobertura_geografica IS NULL OR d.jurisdiccion_nivel IS NULL OR d.jurisdiccion_geo_codes IS NULL);

-- 2b) Entidades DEPARTAMENTALES (con divipola_departamento pero sin divipola_municipio o explícitamente departamental)
--     Convención: si divipola_municipio termina en '000', es la gobernación → departamental
UPDATE datasets d SET
    cobertura_geografica   = COALESCE(d.cobertura_geografica, 'Departamental'),
    jurisdiccion_nivel     = COALESCE(d.jurisdiccion_nivel, 'departamental'),
    jurisdiccion_geo_codes = COALESCE(d.jurisdiccion_geo_codes, to_jsonb(ARRAY[e.divipola_departamento])),
    jurisdiccion_confidence = COALESCE(d.jurisdiccion_confidence, 'high'),
    jurisdiccion_inferred_at = COALESCE(d.jurisdiccion_inferred_at, NOW()),
    jurisdiccion_reason    = COALESCE(d.jurisdiccion_reason, 'entities.divipola_departamento JOIN (FU.2)'),
    last_refreshed_at      = NOW()
FROM entities e
WHERE d.entity_id = e.entity_id
  AND d.source_portal = 'datos.gov.co'
  AND d.source_type = 'federated'
  AND e.divipola_departamento IS NOT NULL
  AND e.divipola_municipio IS NULL
  AND (d.cobertura_geografica IS NULL OR d.jurisdiccion_nivel IS NULL OR d.jurisdiccion_geo_codes IS NULL);

-- 2c) Entidades NACIONALES
UPDATE datasets d SET
    cobertura_geografica   = COALESCE(d.cobertura_geografica, 'Nacional'),
    jurisdiccion_nivel     = COALESCE(d.jurisdiccion_nivel, 'nacional'),
    jurisdiccion_geo_codes = COALESCE(d.jurisdiccion_geo_codes, '[]'::jsonb),
    jurisdiccion_confidence = COALESCE(d.jurisdiccion_confidence, 'high'),
    jurisdiccion_inferred_at = COALESCE(d.jurisdiccion_inferred_at, NOW()),
    jurisdiccion_reason    = COALESCE(d.jurisdiccion_reason, 'entity kind=nacional (FU.2)'),
    last_refreshed_at      = NOW()
FROM entities e
WHERE d.entity_id = e.entity_id
  AND d.source_portal = 'datos.gov.co'
  AND d.source_type = 'federated'
  AND e.kind = 'nacional'
  AND (d.cobertura_geografica IS NULL OR d.jurisdiccion_nivel IS NULL OR d.jurisdiccion_geo_codes IS NULL);

COMMIT;


-- =============================================================================
-- Verificación inmediata
-- =============================================================================
SELECT
  source_portal,
  COUNT(*) AS n,
  ROUND(100.0*COUNT(license_id)/COUNT(*),1) AS pct_license_id,
  ROUND(100.0*COUNT(cobertura_geografica)/COUNT(*),1) AS pct_cob,
  ROUND(100.0*COUNT(jurisdiccion_nivel)/COUNT(*),1) AS pct_jur
FROM datasets
WHERE source_type = 'federated'
GROUP BY 1 ORDER BY 2 DESC;

-- Cobertura global post-FU.2
SELECT
  COUNT(*) AS total,
  ROUND(100.0*COUNT(license_id)/COUNT(*),1) AS pct_license_id,
  ROUND(100.0*COUNT(cobertura_geografica)/COUNT(*),1) AS pct_cob,
  ROUND(100.0*COUNT(jurisdiccion_nivel)/COUNT(*),1) AS pct_jur
FROM datasets;
