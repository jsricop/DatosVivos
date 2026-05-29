-- 015_backfill_jurisdiccion_nulls.sql
--
-- Bug 4 — 24 nativos subnacionales con jurisdiccion_nivel=NULL detectados
-- en el audit Q.7.c. Backfill por regla a partir de:
--   * entity_raw (Gobernación/Corporación Autónoma → departamental),
--   * DIVIPOLA-Municipio (= 11001 → distrito_capital; otro → municipal).
--
-- Los 3 "sospechosos" (INS, ANM, DNP con DIVIPOLA fuera de 11001) NO
-- entran al backfill — son nacionales correctos (sede del archivo
-- generador ≠ jurisdicción de la entidad). Se preservan tal cual.
--
-- Idempotente (solo toca rows con NULL).

BEGIN;

UPDATE datasets SET jurisdiccion_nivel =
    CASE
        WHEN domain_metadata->>'Información-de-la-Entidad_DIVIPOLA-Municipio' = '11001'
            THEN 'distrito_capital'
        WHEN entity_raw ILIKE '%gobernación%' OR entity_raw ILIKE '%gobernacion%'
            THEN 'departamental'
        WHEN entity_raw ILIKE '%corporación autónoma%' OR entity_raw ILIKE '%corporacion autonoma%'
            THEN 'departamental'
        WHEN domain_metadata->>'Información-de-la-Entidad_DIVIPOLA-Municipio' IS NOT NULL
            THEN 'municipal'
        ELSE 'nacional'
    END
WHERE source_type = 'socrata'
  AND jurisdiccion_nivel IS NULL;

COMMIT;
