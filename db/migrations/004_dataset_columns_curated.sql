-- Migration 004 — dataset_columns_curated (D.6 audit top-down)
--
-- Para cada columna de cada dataset no-admin, se anota su tipo semántico
-- (geo/fecha/metrica/dimension) y sub-tipo. Esto permite que el endpoint
-- POST /api/v1/query/chips/execute (Fase B futura) genere SoQL determinista
-- según el TIPO de chip marcado por el usuario.
--
-- Categorías:
--   semantic_type:    geo | fecha | metrica | dimension | exclude
--   semantic_subtype:
--     geo:        code | name | coord
--     fecha:      year | date | period
--     metrica:    count | currency | rate | generic
--     dimension:  demographic | administrative | educational | status | other
--     exclude:    id | url | text_long | other
--
-- confidence: high | medium | low
--   high   → match unívoco por nombre canónico o description literal
--   medium → match por keywords + data_type consistente
--   low    → solo data_type, sin signal de nombre/description
--
-- Aplicar:
--   psql "$DATABASE_URL" -f db/migrations/004_dataset_columns_curated.sql

BEGIN;

CREATE TABLE IF NOT EXISTS dataset_columns_curated (
    dataset_id        VARCHAR(20) NOT NULL,
    col_name          TEXT NOT NULL,
    socrata_data_type TEXT,
    socrata_description TEXT,
    semantic_type     VARCHAR(20) NOT NULL,
    semantic_subtype  VARCHAR(30),
    confidence        VARCHAR(10) NOT NULL,
    reason            TEXT,
    curated_at        TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (dataset_id, col_name),
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_dcc_dataset      ON dataset_columns_curated(dataset_id);
CREATE INDEX IF NOT EXISTS idx_dcc_semantic     ON dataset_columns_curated(semantic_type);
CREATE INDEX IF NOT EXISTS idx_dcc_confidence   ON dataset_columns_curated(confidence);

COMMIT;
