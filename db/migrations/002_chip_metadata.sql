-- Migration 002 — Chip metadata: jurisdicción geográfica por dataset.
--
-- Necesario para Fase 1 del audit top-down: la UI con chips estructurados
-- (TEMA, TIPO, TERRITORIO, ENTIDAD) debe poder filtrar el catálogo de 8.396
-- datasets por jurisdicción real. Hoy `datasets.category` ya cubre TEMA, y
-- `entities` cubre ENTIDAD; falta el campo TERRITORIO.
--
-- Aplicar:
--   psql "$DATABASE_URL" -f db/migrations/002_chip_metadata.sql
--
-- Idempotente: usa IF NOT EXISTS.

BEGIN;

ALTER TABLE datasets
    -- nacional | departamental | municipal | distrito_capital | multi | desconocido
    ADD COLUMN IF NOT EXISTS jurisdiccion_nivel        VARCHAR(30),
    -- Lista de códigos DIVIPOLA (str). null si nivel=nacional o desconocido.
    -- Ejemplos: ["11"] = Bogotá, ["15"] = Boyacá, ["05001"] = Medellín.
    ADD COLUMN IF NOT EXISTS jurisdiccion_geo_codes    JSONB,
    -- high | medium | low. null = no inferido. Permite distinguir lo que
    -- vino por regla unívoca (high) de lo que vino por keyword en descripción
    -- (medium) o de un LLM fallback (low).
    ADD COLUMN IF NOT EXISTS jurisdiccion_confidence   VARCHAR(10),
    ADD COLUMN IF NOT EXISTS jurisdiccion_inferred_at  TIMESTAMPTZ,
    -- Texto libre con el por qué de la asignación, para auditar a posteriori.
    -- Ejemplos: "entity_match: Secretaría de Educación de Bogotá",
    --           "national_keyword: Ministerio de", "fallback_llm".
    ADD COLUMN IF NOT EXISTS jurisdiccion_reason       TEXT;

CREATE INDEX IF NOT EXISTS idx_datasets_jurisdiccion_nivel
    ON datasets(jurisdiccion_nivel) WHERE jurisdiccion_nivel IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_datasets_jurisdiccion_codes
    ON datasets USING GIN (jurisdiccion_geo_codes);

COMMIT;
