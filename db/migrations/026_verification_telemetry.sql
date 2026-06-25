-- Migration 026 — Telemetría del verificador de consulta (ADR-022 Fase 3).
--
-- Instrumenta el bucle de generación+verificación del path generativo: cuántas
-- reparaciones necesitó cada consulta, si pasó la verificación, y en qué capa
-- falló. Sin esto no podemos vigilar la distribución de reparaciones (para
-- ajustar QUERY_MAX_REPAIRS / el costo LLM) ni medir la tasa de no-verificadas.
--
-- Aplicar:
--   psql "$DATABASE_URL" -f db/migrations/026_verification_telemetry.sql
--
-- Idempotente: IF NOT EXISTS en todos los ADD COLUMN.

BEGIN;

ALTER TABLE queries
    ADD COLUMN IF NOT EXISTS verification_repairs       INTEGER,
    ADD COLUMN IF NOT EXISTS verification_passed        BOOLEAN,
    ADD COLUMN IF NOT EXISTS verification_layer_failed  VARCHAR(20);

-- `verification_layer_failed`: null | 'syntax' | 'execution' | 'semantic'
-- `verification_passed`: true (verificada) | false (ejecutada sin verificar o degradada)

CREATE INDEX IF NOT EXISTS idx_queries_verif_passed
    ON queries(verification_passed) WHERE verification_passed IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_queries_verif_layer
    ON queries(verification_layer_failed) WHERE verification_layer_failed IS NOT NULL;

COMMIT;
