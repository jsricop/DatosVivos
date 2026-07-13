-- 028 — Filtros de valor sobre la bodega (ADR-024): perfil de columnas
-- filtrables de cada Parquet descargado. Tabla LATERAL nueva: no toca
-- tablas ni vistas existentes.
--
-- Cada fila = un VALOR real de una columna de baja cardinalidad (kind
-- 'valor') o un AÑO presente en una columna fecha (kind 'anio'), con su
-- conteo. El perfil lo escribe scripts/profile_filter_values.py leyendo
-- el Parquet con DuckDB; los endpoints solo aplican filtros cuyos
-- (col, value) EXISTEN aquí — el LLM elige entre valores reales, nunca
-- escribe SQL.
--
-- Aplicar: cat db/migrations/028_dataset_filter_values.sql | docker exec -i datosvivos-postgres-1 psql -U dv -d datosvivos

BEGIN;

CREATE TABLE IF NOT EXISTS dataset_filter_values (
    dataset_id   VARCHAR(40) NOT NULL,
    col_name     TEXT        NOT NULL,
    kind         VARCHAR(10) NOT NULL,               -- valor | anio
    value        TEXT        NOT NULL,               -- valor EXACTO como está en el dato
    n            BIGINT,                             -- filas con ese valor
    profiled_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (dataset_id, col_name, value)
);

CREATE INDEX IF NOT EXISTS idx_dfv_dataset ON dataset_filter_values(dataset_id);

COMMIT;
