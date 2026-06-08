-- 023_curate_descentralizadas.sql
--
-- Hito R FU.2 extensión — clasificar las 14 entities descentralizadas que
-- concentran 7.728 federados de datos.gov.co sin curar.
--
-- Problema: entities `kind='descentralizada'` con divipola_municipio que es
-- SEDE FÍSICA (no jurisdicción de datos). Curar automáticamente por divipola
-- inventaría jurisdicción incorrecta (IGAC sede Bogotá publica datos del
-- país entero). Mig 022 los excluyó.
--
-- Esta migración aplica reglas EXPLÍCITAS por nombre de entity (no patrones
-- genéricos) para que sea evidente qué se está clasificando y por qué.
-- 14 entities = 7.728 datasets = +32% de cobertura global esperada.
--
-- Clasificación (basada en nombre + carácter de la entidad):
--   NACIONAL (cubre todo el país):
--     - Instituto Geográfico Agustín Codazzi (IGAC)         · 5.750
--     - XM Compañía de Expertos en Mercados                 ·   368
--     - Servicio Geológico Colombiano                       ·   129
--     - Autoridad Nacional de Licencias Ambientales         ·   102
--     - Parques Nacionales Naturales de Colombia            ·    26
--     - Fondo Adaptación                                    ·    26
--
--   DISTRITAL BOGOTÁ (DIVIPOLA 11001):
--     - Secretaría Distrital de Salud                       ·    69
--     - Secretaría Distrital de Ambiente                    ·    39
--     - Veeduría Distrital                                  ·    10
--     - Fundación Gilberto Alzate Avendaño                  ·     9
--
--   DEPARTAMENTAL/REGIONAL:
--     - Corp. Autónoma Regional de Cundinamarca → DIVIPOLA 25 · 1.047
--     - Corp. Autónoma Regional del Cauca       → DIVIPOLA 19 ·    56
--     - Instituto Amazónico SINCHI              → DIVIPOLA 91 ·    65
--     - Laboratorio SIG y SR Instituto SINCHI   → DIVIPOLA 91 ·    32
--
-- Idempotente: COALESCE no pisa valores ya curados.

BEGIN;

-- =============================================================================
-- Bucket NACIONAL (6 entities, 6.401 datasets)
-- =============================================================================
UPDATE datasets d SET
    cobertura_geografica   = COALESCE(d.cobertura_geografica, 'Nacional'),
    jurisdiccion_nivel     = COALESCE(d.jurisdiccion_nivel, 'nacional'),
    jurisdiccion_geo_codes = COALESCE(d.jurisdiccion_geo_codes, '[]'::jsonb),
    jurisdiccion_confidence = COALESCE(d.jurisdiccion_confidence, 'high'),
    jurisdiccion_inferred_at = COALESCE(d.jurisdiccion_inferred_at, NOW()),
    jurisdiccion_reason    = COALESCE(d.jurisdiccion_reason, 'descentralizada nacional por reconocimiento explícito (FU.2 ext)'),
    last_refreshed_at      = NOW()
FROM entities e
WHERE d.entity_id = e.entity_id
  AND d.source_portal = 'datos.gov.co'
  AND d.source_type = 'federated'
  AND e.kind = 'descentralizada'
  AND e.name IN (
      'Instituto Geográfico Agustín Codazzi',
      'XM Compañía de Expertos en Mercados',
      'Servicio Geológico Colombiano',
      'Autoridad Nacional de Licencias Ambientales',
      'Parques Nacionales Naturales de Colombia',
      'Fondo Adaptación'
  )
  AND (d.cobertura_geografica IS NULL OR d.jurisdiccion_nivel IS NULL OR d.jurisdiccion_geo_codes IS NULL);

-- =============================================================================
-- Bucket DISTRITAL BOGOTÁ (4 entities, 127 datasets)
-- =============================================================================
UPDATE datasets d SET
    cobertura_geografica   = COALESCE(d.cobertura_geografica, 'Municipal'),
    jurisdiccion_nivel     = COALESCE(d.jurisdiccion_nivel, 'distrito_capital'),
    jurisdiccion_geo_codes = COALESCE(d.jurisdiccion_geo_codes, '["11001"]'::jsonb),
    jurisdiccion_confidence = COALESCE(d.jurisdiccion_confidence, 'high'),
    jurisdiccion_inferred_at = COALESCE(d.jurisdiccion_inferred_at, NOW()),
    jurisdiccion_reason    = COALESCE(d.jurisdiccion_reason, 'descentralizada distrital Bogotá por reconocimiento explícito (FU.2 ext)'),
    last_refreshed_at      = NOW()
FROM entities e
WHERE d.entity_id = e.entity_id
  AND d.source_portal = 'datos.gov.co'
  AND d.source_type = 'federated'
  AND e.kind = 'descentralizada'
  AND e.name IN (
      'Secretaría Distrital de Salud',
      'Secretaría Distrital de Ambiente',
      'Veeduría Distrital',
      'Fundación Gilberto Alzate Avendaño'
  )
  AND (d.cobertura_geografica IS NULL OR d.jurisdiccion_nivel IS NULL OR d.jurisdiccion_geo_codes IS NULL);

-- =============================================================================
-- Bucket DEPARTAMENTAL/REGIONAL — Cundinamarca (DIVIPOLA 25)
-- =============================================================================
UPDATE datasets d SET
    cobertura_geografica   = COALESCE(d.cobertura_geografica, 'Departamental'),
    jurisdiccion_nivel     = COALESCE(d.jurisdiccion_nivel, 'departamental'),
    jurisdiccion_geo_codes = COALESCE(d.jurisdiccion_geo_codes, '["25"]'::jsonb),
    jurisdiccion_confidence = COALESCE(d.jurisdiccion_confidence, 'high'),
    jurisdiccion_inferred_at = COALESCE(d.jurisdiccion_inferred_at, NOW()),
    jurisdiccion_reason    = COALESCE(d.jurisdiccion_reason, 'CAR Cundinamarca (FU.2 ext)'),
    last_refreshed_at      = NOW()
FROM entities e
WHERE d.entity_id = e.entity_id
  AND d.source_portal = 'datos.gov.co'
  AND d.source_type = 'federated'
  AND e.kind = 'descentralizada'
  AND e.name = 'Corporación Autónoma Regional de Cundinamarca'
  AND (d.cobertura_geografica IS NULL OR d.jurisdiccion_nivel IS NULL OR d.jurisdiccion_geo_codes IS NULL);

-- =============================================================================
-- Bucket DEPARTAMENTAL/REGIONAL — Cauca (DIVIPOLA 19)
-- =============================================================================
UPDATE datasets d SET
    cobertura_geografica   = COALESCE(d.cobertura_geografica, 'Departamental'),
    jurisdiccion_nivel     = COALESCE(d.jurisdiccion_nivel, 'departamental'),
    jurisdiccion_geo_codes = COALESCE(d.jurisdiccion_geo_codes, '["19"]'::jsonb),
    jurisdiccion_confidence = COALESCE(d.jurisdiccion_confidence, 'high'),
    jurisdiccion_inferred_at = COALESCE(d.jurisdiccion_inferred_at, NOW()),
    jurisdiccion_reason    = COALESCE(d.jurisdiccion_reason, 'CAR Cauca (FU.2 ext)'),
    last_refreshed_at      = NOW()
FROM entities e
WHERE d.entity_id = e.entity_id
  AND d.source_portal = 'datos.gov.co'
  AND d.source_type = 'federated'
  AND e.kind = 'descentralizada'
  AND e.name = 'Corporación Autónoma Regional del Cauca'
  AND (d.cobertura_geografica IS NULL OR d.jurisdiccion_nivel IS NULL OR d.jurisdiccion_geo_codes IS NULL);

-- =============================================================================
-- Bucket DEPARTAMENTAL/REGIONAL — Amazonia (Instituto SINCHI, DIVIPOLA 91)
-- =============================================================================
UPDATE datasets d SET
    cobertura_geografica   = COALESCE(d.cobertura_geografica, 'Departamental'),
    jurisdiccion_nivel     = COALESCE(d.jurisdiccion_nivel, 'departamental'),
    jurisdiccion_geo_codes = COALESCE(d.jurisdiccion_geo_codes, '["91"]'::jsonb),
    jurisdiccion_confidence = COALESCE(d.jurisdiccion_confidence, 'high'),
    jurisdiccion_inferred_at = COALESCE(d.jurisdiccion_inferred_at, NOW()),
    jurisdiccion_reason    = COALESCE(d.jurisdiccion_reason, 'SINCHI Amazonas (FU.2 ext)'),
    last_refreshed_at      = NOW()
FROM entities e
WHERE d.entity_id = e.entity_id
  AND d.source_portal = 'datos.gov.co'
  AND d.source_type = 'federated'
  AND e.kind = 'descentralizada'
  AND e.name IN (
      'Instituto Amazónico de Investigaciones Científicas',
      'Laboratorio SIG y SR - Instituto SINCHI'
  )
  AND (d.cobertura_geografica IS NULL OR d.jurisdiccion_nivel IS NULL OR d.jurisdiccion_geo_codes IS NULL);

COMMIT;

-- =============================================================================
-- Verificación post-migración
-- =============================================================================
SELECT
  source_type,
  COUNT(*) AS n,
  ROUND(100.0*COUNT(jurisdiccion_nivel)/COUNT(*),1) AS pct_jur,
  ROUND(100.0*COUNT(cobertura_geografica)/COUNT(*),1) AS pct_cob
FROM datasets GROUP BY 1;

SELECT
  COUNT(*) AS total,
  ROUND(100.0*COUNT(jurisdiccion_nivel)/COUNT(*),1) AS pct_jur_global,
  ROUND(100.0*COUNT(cobertura_geografica)/COUNT(*),1) AS pct_cob_global
FROM datasets;
