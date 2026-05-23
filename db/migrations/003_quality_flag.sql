-- Migration 003 — quality_flag para filtrar datasets que ensucian los chips.
--
-- Hoy 33% del catálogo (2.779 datasets) son obligaciones de Ley 1712:
-- esquemas de publicación, índices de información clasificada, registros de
-- activos. No contienen datos útiles para consulta ciudadana. Marcarlos para
-- ocultar del subset por default.
--
-- Estados:
--   NULL o 'ok'         → dataset útil, default
--   'admin_only'        → Ley 1712 / ITA / similar
--   'no_rows'           → row_count=0
--   'stale'             → rows_updated_at < NOW() - 3 years
--   'duplicate'         → reservado para detección futura
--
-- Aplicar:
--   psql "$DATABASE_URL" -f db/migrations/003_quality_flag.sql

BEGIN;

ALTER TABLE datasets
    ADD COLUMN IF NOT EXISTS quality_flag VARCHAR(20),
    ADD COLUMN IF NOT EXISTS quality_flag_at TIMESTAMPTZ;

-- Index parcial: solo registros con flag no-null. La inmensa mayoría queda
-- NULL (= ok) y no necesita estar en el índice.
CREATE INDEX IF NOT EXISTS idx_datasets_quality_flag
    ON datasets(quality_flag) WHERE quality_flag IS NOT NULL;

COMMIT;
