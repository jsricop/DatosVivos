-- 018_entities_divipola.sql
--
-- Quick win — promover DIVIPOLA-Mpio/Dpto del JSONB de `datasets.domain_metadata`
-- a columnas estructuradas en `entities`. Hoy el código está enterrado en el
-- blob; con columnas, los chips y el tablero pueden filtrar "entidades en
-- Antioquia" sin desempaquetar JSONB.
--
-- DIVIPOLA-Mpio describe DÓNDE-ESTÁ-EL-EDITOR (no la cobertura del dataset
-- — eso lo cubre `datasets.jurisdiccion_*`). Para cada entity tomamos la
-- MODA de sus datasets, asumiendo que una entidad tiene su sede en una
-- ubicación dominante.
--
-- Cobertura esperada: ~17.900 datasets traen DIVIPOLA-Mpio en domain_metadata
-- (la mayoría nacionales con sede Bogotá DIVIPOLA=11001).

BEGIN;

ALTER TABLE entities
    ADD COLUMN IF NOT EXISTS divipola_municipio    VARCHAR(10),
    ADD COLUMN IF NOT EXISTS divipola_departamento VARCHAR(5);

-- Backfill: para cada entity, MODA del DIVIPOLA de sus datasets.
WITH per_entity AS (
    SELECT
        d.entity_id,
        d.domain_metadata->>'Información-de-la-Entidad_DIVIPOLA-Municipio'    AS mpio,
        d.domain_metadata->>'Información-de-la-Entidad_DIVIPOLA-Departamento' AS dpto,
        COUNT(*) AS n
    FROM datasets d
    WHERE d.entity_id IS NOT NULL
      AND d.domain_metadata IS NOT NULL
      AND d.domain_metadata->>'Información-de-la-Entidad_DIVIPOLA-Municipio' IS NOT NULL
    GROUP BY d.entity_id, mpio, dpto
),
ranked AS (
    SELECT entity_id, mpio, dpto,
           ROW_NUMBER() OVER (PARTITION BY entity_id ORDER BY n DESC) AS rank
    FROM per_entity
),
top AS (
    SELECT entity_id, mpio, dpto FROM ranked WHERE rank = 1
)
UPDATE entities e
SET divipola_municipio = top.mpio,
    divipola_departamento = COALESCE(top.dpto, LEFT(top.mpio, 2))
FROM top
WHERE e.entity_id = top.entity_id
  AND e.divipola_municipio IS NULL;

CREATE INDEX IF NOT EXISTS idx_entities_divipola_mpio ON entities(divipola_municipio);
CREATE INDEX IF NOT EXISTS idx_entities_divipola_dpto ON entities(divipola_departamento);

COMMIT;
