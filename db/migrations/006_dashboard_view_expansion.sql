-- Migration 006 — Expandir v_dataset_status con engagement + metadata para el tablero.
--
-- La migración 005 agregó columnas a `datasets` (download_count, page_views_*,
-- provenance, license, cobertura_geografica, etc.). Esta migración las expone
-- en la view que consume Power BI, además de `quality_flag` (para el toggle
-- útil/admin_only que el tablero ofrecerá) y `jurisdiccion_nivel`.
--
-- Postgres exige que CREATE OR REPLACE VIEW conserve las columnas previas en el
-- mismo orden; las nuevas van al final. No se rompe ningún binding existente.
--
-- Aplicar:
--   psql "$DATABASE_URL" -f db/migrations/006_dashboard_view_expansion.sql

BEGIN;

CREATE OR REPLACE VIEW v_dataset_status AS
SELECT
    -- === columnas originales (orden preservado) ===
    d.dataset_id,
    d.name AS dataset_name,
    d.entity_id,
    e.name AS entity_name,
    e.abbrev AS entity_abbrev,
    d.category,
    d.rows_updated_at,
    d.update_frequency,
    parse_frequency_days(d.update_frequency) AS frequency_days,
    CASE
        WHEN d.rows_updated_at IS NULL THEN NULL
        ELSE EXTRACT(EPOCH FROM (NOW() - d.rows_updated_at))::INTEGER / 86400
    END AS days_since_update,
    compute_status(d.rows_updated_at, d.update_frequency) AS status,
    d.row_count,
    d.view_count,
    d.socrata_url,
    d.api_url,
    d.last_refreshed_at,
    -- === columnas nuevas (apéndice) ===
    d.quality_flag,                 -- NULL/ok = útil; admin_only = obligación Ley 1712 (toggle)
    d.download_count,
    d.page_views_total,
    d.page_views_last_week,
    d.page_views_last_month,
    d.data_updated_at,
    d.metadata_updated_at,
    d.publication_date,
    d.provenance,                   -- official | community
    d.license,
    d.cobertura_geografica,         -- declarada por la entidad (Municipal/Departamental/Nacional)
    d.frecuencia_declarada,         -- declarada en español (Diaria/Mensual/Anual)
    d.sector,
    d.number_of_comments,
    d.total_times_rated,
    d.jurisdiccion_nivel            -- inferida por nosotros (curate_chip_metadata)
FROM datasets d
LEFT JOIN entities e ON e.entity_id = d.entity_id;

COMMIT;
