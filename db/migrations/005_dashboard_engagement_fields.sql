-- Migration 005 — Campos de engagement + metadata estructurada para el tablero PowerBI.
--
-- Auditoría 2026-05-25: el ETL solo capturaba `view_count`. datos.gov.co
-- (Discovery API) expone muchas más métricas valiosas para un tablero de
-- salud del catálogo: descargas, page views por ventana temporal, fechas
-- distintas (dato vs metadata vs publicación), procedencia, licencia y la
-- metadata estructurada colombiana (`domain_metadata`: cobertura geográfica,
-- frecuencia declarada, sector).
--
-- Además corrige el BUG de `row_count`: el ETL guardaba `viewLastModified`
-- (un timestamp ~1.78e9) como si fuera el número de filas. El conteo real
-- se repuebla vía `count(*)` SODA por dataset (paso aparte del ETL).
--
-- Política de captura (decisión usuario): superset generoso. Mejor tener
-- datos de más que re-correr el ETL sobre 8.396 datasets. Por eso se guarda
-- `domain_metadata` crudo en JSONB además de extraer las claves de alto valor.
--
-- Fuentes complementarias (cada una aporta lo que la otra no tiene):
--   1. Discovery API (bulk)  → engagement, fechas, provenance, license,
--      domain_metadata. AUTORITATIVA para todo lo que expone.
--   2. Metadata API (por id) → SOLO number_of_comments + total_times_rated
--      (Discovery no los tiene). En campos solapados manda Discovery.
--   3. SODA count(*) (por id) → row_count real (ninguna API lo da).
--
-- Aplicar:
--   psql "$DATABASE_URL" -f db/migrations/005_dashboard_engagement_fields.sql
--
-- Idempotente: IF NOT EXISTS en todos los ADD COLUMN.

BEGIN;

ALTER TABLE datasets
    -- Engagement
    ADD COLUMN IF NOT EXISTS download_count          BIGINT,
    ADD COLUMN IF NOT EXISTS page_views_last_week     INTEGER,
    ADD COLUMN IF NOT EXISTS page_views_last_month    INTEGER,
    ADD COLUMN IF NOT EXISTS page_views_total         BIGINT,
    ADD COLUMN IF NOT EXISTS number_of_comments       INTEGER,  -- único de Metadata API
    ADD COLUMN IF NOT EXISTS total_times_rated         INTEGER,  -- único de Metadata API

    -- Fechas (todas distintas; data_updated_at es la del semáforo)
    ADD COLUMN IF NOT EXISTS data_updated_at          TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS metadata_updated_at      TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS publication_date         TIMESTAMPTZ,

    -- Confianza / apertura
    ADD COLUMN IF NOT EXISTS provenance               VARCHAR(20),  -- official | community
    ADD COLUMN IF NOT EXISTS license                  TEXT,

    -- Metadata estructurada colombiana (extraída de domain_metadata)
    ADD COLUMN IF NOT EXISTS cobertura_geografica     TEXT,  -- Municipal | Departamental | Nacional | ...
    ADD COLUMN IF NOT EXISTS frecuencia_declarada     TEXT,  -- Diaria | Mensual | Anual | ... (español, declarada por la entidad)
    ADD COLUMN IF NOT EXISTS sector                   TEXT,

    -- Raw para futuro: cualquier clave de domain_metadata sin re-correr ETL
    ADD COLUMN IF NOT EXISTS domain_metadata          JSONB;

-- Índices para los filtros/segmentaciones típicas del tablero.
CREATE INDEX IF NOT EXISTS idx_datasets_provenance
    ON datasets(provenance) WHERE provenance IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_datasets_download_count
    ON datasets(download_count DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_datasets_cobertura
    ON datasets(cobertura_geografica) WHERE cobertura_geografica IS NOT NULL;

-- NOTA sobre row_count: no se altera el tipo (sigue BIGINT). El ETL corregido
-- dejará de escribir el timestamp y lo repoblará con count(*) real. Los valores
-- basura actuales (~1.78e9) se sobrescriben en el próximo run.

COMMIT;
