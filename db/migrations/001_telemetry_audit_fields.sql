-- Migration 001 — Telemetría enriquecida para audit top-down (Fase 0 / Paso 0.2).
--
-- Agrega campos para correlacionar retrieval y validators con el outcome de cada
-- query. Sin esto, las fases 1-3 del audit son ciegas — no podemos medir si una
-- mejora en retrieval reduce wrong_dataset, ni si el penalty geo introduce
-- regresiones en cobertura.
--
-- Aplicar manualmente o vía script de migración:
--   psql "$DATABASE_URL" -f db/migrations/001_telemetry_audit_fields.sql
--
-- Idempotente: usa IF NOT EXISTS en todos los ADD COLUMN.

BEGIN;

ALTER TABLE queries
    ADD COLUMN IF NOT EXISTS dataset_top1_id     VARCHAR(20),
    ADD COLUMN IF NOT EXISTS dataset_top1_score  NUMERIC(8, 4),
    ADD COLUMN IF NOT EXISTS geo_resolved        TEXT,
    ADD COLUMN IF NOT EXISTS geo_attribution_ok  BOOLEAN,
    ADD COLUMN IF NOT EXISTS dashboard_emitted   BOOLEAN,
    ADD COLUMN IF NOT EXISTS failure_type        VARCHAR(30),
    ADD COLUMN IF NOT EXISTS user_feedback       VARCHAR(20);

-- `failure_type`: null | 'no_rows' | 'wrong_dataset' | 'geo_mismatch'
--                 | 'hallucination' | 'timeout' | 'slow'
-- `user_feedback`: null | 'useful' | 'not_useful'

-- Índices para filtros típicos del eval harness y del dashboard /tablero.
CREATE INDEX IF NOT EXISTS idx_queries_top1       ON queries(dataset_top1_id);
CREATE INDEX IF NOT EXISTS idx_queries_failure    ON queries(failure_type) WHERE failure_type IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_queries_geo_ok     ON queries(geo_attribution_ok) WHERE geo_attribution_ok IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_queries_feedback   ON queries(user_feedback) WHERE user_feedback IS NOT NULL;

COMMIT;
