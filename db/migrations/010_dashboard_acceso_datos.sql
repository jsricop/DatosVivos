-- 010_dashboard_acceso_datos.sql
--
-- Agrega 2 columnas editoriales al CSV público del tablero:
--   - es_federado:    sí | no   (lectura directa de source_type)
--   - acceso_datos:   directo | requiere_herramienta | solo_metadatos
--
-- Motivación: post Hito Q (migración 009) el catálogo pasó de 8.404 nativos a
-- 18.402 datasets totales (incluye 9.995 federados). Sin marcar, el usuario del
-- tablero asume que toda fila es consultable de la misma manera y se choca al
-- intentar cruzar datos federados (≈48% del catálogo no es tabular vía SODA).
--
-- Lógica:
--   directo               → nativos en SODA (source_type='socrata'). API queryable.
--   requiere_herramienta  → federados con CSV accesible (source_type='federated'
--                           AND federated_status='ok'). Cubre tanto MEDATA (CSV
--                           directo) como Cali/Bogotá/Valle (URL CKAN que hay
--                           que resolver). PowerBI no los consume directo.
--   solo_metadatos        → federados sin CSV en metadata.access_points (mayoría
--                           IGAC y similares; geoservicios WMS/WFS no tabulares).
--
-- Idempotente: CREATE OR REPLACE conserva columnas previas en su orden.

BEGIN;

CREATE OR REPLACE VIEW v_dataset_status AS
SELECT
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
    d.quality_flag,
    d.download_count,
    d.page_views_total,
    d.page_views_last_week,
    d.page_views_last_month,
    d.data_updated_at,
    d.metadata_updated_at,
    d.publication_date,
    d.provenance,
    d.license,
    d.cobertura_geografica,
    d.frecuencia_declarada,
    d.sector,
    d.number_of_comments,
    d.total_times_rated,
    d.jurisdiccion_nivel,
    -- === migración 010 — apéndice ===
    CASE WHEN d.source_type = 'federated' THEN 'sí' ELSE 'no' END AS es_federado,
    CASE
        WHEN d.source_type = 'socrata' THEN 'directo'
        WHEN d.source_type = 'federated' AND d.federated_status = 'ok' THEN 'requiere_herramienta'
        ELSE 'solo_metadatos'
    END AS acceso_datos
FROM datasets d
LEFT JOIN entities e ON e.entity_id = d.entity_id;

COMMIT;
