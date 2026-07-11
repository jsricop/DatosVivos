-- 027 — Bodega local de datasets (farmeo): manifest de snapshots Parquet.
-- Tabla LATERAL nueva: no toca tablas ni vistas existentes.
-- Aplicar: cat db/migrations/027_dataset_snapshots.sql | docker exec -i datosvivos-postgres-1 psql -U dv -d datosvivos

BEGIN;

CREATE TABLE IF NOT EXISTS dataset_snapshots (
    dataset_id        VARCHAR(40) PRIMARY KEY,
    status            VARCHAR(20) NOT NULL,          -- downloaded | failed | evicted | too_big
    priority_score    NUMERIC,                       -- valor-por-GB al momento de puntuar
    bytes             BIGINT,                        -- tamaño REAL del parquet
    rows              BIGINT,
    parquet_path      TEXT,
    source_kind       VARCHAR(20),                   -- socrata | federated
    source_updated_at TIMESTAMPTZ,                   -- rows_updated_at del catálogo al bajar
    downloaded_at     TIMESTAMPTZ,
    last_scored_at    TIMESTAMPTZ,
    error             TEXT
);

CREATE INDEX IF NOT EXISTS idx_snapshots_status   ON dataset_snapshots(status);
CREATE INDEX IF NOT EXISTS idx_snapshots_priority ON dataset_snapshots(priority_score DESC NULLS LAST);

COMMIT;
