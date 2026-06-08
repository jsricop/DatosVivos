-- 024_seed_orphan_publishers.sql
--
-- Hito R follow-up — seedear los publishers federados huérfanos (entity_id
-- NULL) para que el tablero pueda agruparlos por entidad y se cure su
-- jurisdicción.
--
-- Diagnóstico previo: ~1.806 datasets federados sin entity_id. Distribución
-- por análisis de nombre:
--   - 38 publishers Bogotá distritales (1.215 datasets) — Secretarías, Institutos,
--     Departamentos Administrativos, Subredes de Salud, UAEs distritales.
--   - 1 publisher Cali (342 datasets) — Alcaldía Municipal de Santiago de Cali.
--   - 27 publishers en "otros", de los cuales:
--       * mayoría también Bogotá distrital (Subred, IPES, IDU, IDEP, Caja
--         Vivienda Popular, Terminal Transporte, Oficina Transparencia,
--         Departamentos Administrativos, Unidades Administrativas Especiales)
--       * 2 nacionales (INSTITUTO NACIONAL DE VIAS, "Servicio Geologico
--         Colombiano" con typo)
--       * 3 basura (Esri, ArcGIS Hub, {{source}}) — se ignoran.
--
-- Estrategia:
--   Paso A: INSERT entities nuevas (Bogotá distrital, Cali municipal, nacionales).
--   Paso B: UPDATE datasets SET entity_id = (lookup) WHERE entity_raw match.
--   Paso C: UPDATE datasets SET cobertura/jurisdicción desde la nueva entity.
--
-- Idempotente: NOT EXISTS / COALESCE.

BEGIN;

-- =============================================================================
-- Paso A — INSERT entities huérfanas
-- =============================================================================

-- A.1 Bogotá distrital (descentralizadas + secretarías distritales)
INSERT INTO entities (name, kind, divipola_municipio, divipola_departamento)
SELECT DISTINCT entity_raw, 'descentralizada', '11001', '11'
FROM datasets d
WHERE d.source_type = 'federated'
  AND d.entity_id IS NULL
  AND d.entity_raw IS NOT NULL
  AND d.entity_raw ~* 'distrital|bogot|capital|transmilenio|^IDE\b|FONCEP|UAEGRTD|Subred Integrada|IPES|IDU|IDEP|Caja de la Vivienda|Terminal de Transporte|Secretar.+del Distrito|Oficina para la Transparencia|Unidad Administrativa Especial|Departamento Administrativo|Jardín Botánico|Lotería de Bogotá|Universidad Distrital'
  AND NOT EXISTS (SELECT 1 FROM entities e WHERE lower(trim(e.name)) = lower(trim(d.entity_raw)));

-- A.2 Cali municipal
INSERT INTO entities (name, kind, divipola_municipio, divipola_departamento)
SELECT DISTINCT entity_raw, 'territorial', '76001', '76'
FROM datasets d
WHERE d.source_type = 'federated'
  AND d.entity_id IS NULL
  AND d.entity_raw IS NOT NULL
  AND d.entity_raw ~* 'cali|santiago de cali'
  AND NOT EXISTS (SELECT 1 FROM entities e WHERE lower(trim(e.name)) = lower(trim(d.entity_raw)));

-- A.3 Nacionales (INVÍAS typo'd + SGC typo'd)
--     "INSTITUTO NACIONAL DE VIAS" y "Servicio Geologico Colombiano" (sin tilde)
INSERT INTO entities (name, kind)
SELECT DISTINCT entity_raw, 'nacional'
FROM datasets d
WHERE d.source_type = 'federated'
  AND d.entity_id IS NULL
  AND d.entity_raw IS NOT NULL
  AND (d.entity_raw ~* 'INSTITUTO NACIONAL DE VIAS' OR d.entity_raw = 'Servicio Geologico Colombiano')
  AND NOT EXISTS (SELECT 1 FROM entities e WHERE lower(trim(e.name)) = lower(trim(d.entity_raw)));


-- =============================================================================
-- Paso B — resolver entity_id en datasets huérfanos
-- =============================================================================
UPDATE datasets d SET
    entity_id = e.entity_id,
    last_refreshed_at = NOW()
FROM entities e
WHERE d.entity_id IS NULL
  AND d.entity_raw IS NOT NULL
  AND lower(trim(d.entity_raw)) = lower(trim(e.name));


-- =============================================================================
-- Paso C — curar jurisdicción para los recién resueltos
-- =============================================================================

-- C.1 Distrital Bogotá (entity con divipola_municipio = 11001)
UPDATE datasets d SET
    cobertura_geografica   = COALESCE(d.cobertura_geografica, 'Municipal'),
    jurisdiccion_nivel     = COALESCE(d.jurisdiccion_nivel, 'distrito_capital'),
    jurisdiccion_geo_codes = COALESCE(d.jurisdiccion_geo_codes, '["11001"]'::jsonb),
    jurisdiccion_confidence = COALESCE(d.jurisdiccion_confidence, 'high'),
    jurisdiccion_inferred_at = COALESCE(d.jurisdiccion_inferred_at, NOW()),
    jurisdiccion_reason    = COALESCE(d.jurisdiccion_reason, 'publisher Bogotá distrital seedeado (FU.2 huérfanos)'),
    last_refreshed_at      = NOW()
FROM entities e
WHERE d.entity_id = e.entity_id
  AND d.source_type = 'federated'
  AND e.divipola_municipio = '11001'
  AND (d.cobertura_geografica IS NULL OR d.jurisdiccion_nivel IS NULL OR d.jurisdiccion_geo_codes IS NULL);

-- C.2 Cali municipal (entity con divipola_municipio = 76001)
UPDATE datasets d SET
    cobertura_geografica   = COALESCE(d.cobertura_geografica, 'Municipal'),
    jurisdiccion_nivel     = COALESCE(d.jurisdiccion_nivel, 'municipal'),
    jurisdiccion_geo_codes = COALESCE(d.jurisdiccion_geo_codes, '["76001"]'::jsonb),
    jurisdiccion_confidence = COALESCE(d.jurisdiccion_confidence, 'high'),
    jurisdiccion_inferred_at = COALESCE(d.jurisdiccion_inferred_at, NOW()),
    jurisdiccion_reason    = COALESCE(d.jurisdiccion_reason, 'publisher Cali municipal seedeado (FU.2 huérfanos)'),
    last_refreshed_at      = NOW()
FROM entities e
WHERE d.entity_id = e.entity_id
  AND d.source_type = 'federated'
  AND e.divipola_municipio = '76001'
  AND (d.cobertura_geografica IS NULL OR d.jurisdiccion_nivel IS NULL OR d.jurisdiccion_geo_codes IS NULL);

-- C.3 Nacionales (entity kind='nacional' seedeada)
UPDATE datasets d SET
    cobertura_geografica   = COALESCE(d.cobertura_geografica, 'Nacional'),
    jurisdiccion_nivel     = COALESCE(d.jurisdiccion_nivel, 'nacional'),
    jurisdiccion_geo_codes = COALESCE(d.jurisdiccion_geo_codes, '[]'::jsonb),
    jurisdiccion_confidence = COALESCE(d.jurisdiccion_confidence, 'high'),
    jurisdiccion_inferred_at = COALESCE(d.jurisdiccion_inferred_at, NOW()),
    jurisdiccion_reason    = COALESCE(d.jurisdiccion_reason, 'publisher nacional seedeado (FU.2 huérfanos)'),
    last_refreshed_at      = NOW()
FROM entities e
WHERE d.entity_id = e.entity_id
  AND d.source_type = 'federated'
  AND e.kind = 'nacional'
  AND (d.cobertura_geografica IS NULL OR d.jurisdiccion_nivel IS NULL OR d.jurisdiccion_geo_codes IS NULL);

COMMIT;


-- =============================================================================
-- Verificación
-- =============================================================================
SELECT
  COUNT(*) AS total,
  ROUND(100.0*COUNT(entity_id)/COUNT(*),1) AS pct_entity,
  ROUND(100.0*COUNT(jurisdiccion_nivel)/COUNT(*),1) AS pct_jur,
  ROUND(100.0*COUNT(cobertura_geografica)/COUNT(*),1) AS pct_cob,
  ROUND(100.0*COUNT(license_id)/COUNT(*),1) AS pct_license_id
FROM datasets;

-- Publishers que quedaron sin resolver (descartados o no matchearon)
SELECT entity_raw, COUNT(*) AS n
FROM datasets WHERE source_type='federated' AND entity_id IS NULL AND entity_raw IS NOT NULL
GROUP BY 1 ORDER BY 2 DESC LIMIT 10;
