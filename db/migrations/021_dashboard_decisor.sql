-- 021_dashboard_decisor.sql
--
-- Hito R — vistas paralelas curadas para el tablero PowerBI del Director.
--
-- Filosofía (acordada con el usuario el 2026-06-08):
--   1. No dar falsa sensación de seguridad ocultando columnas con NULL alto.
--      NULL puede ser señal real ("nadie comentó", "fuente no declara").
--   2. Asegurar que los datos correspondan a lo real, no ocultar problemas.
--   3. Drop solo de duplicados literales y técnicos sin valor para el decisor.
--
-- ¿Por qué vistas paralelas (_decisor) en vez de reemplazar?
--   - PowerBI tiene queries M pegadas a nombres de columna. Vista paralela
--     permite migrar el .pbix sin romper el modelo existente.
--   - 2-4 semanas de coexistencia, luego drop de las viejas si todo OK.
--
-- DROP (5 columnas):
--   - view_count                 → alias literal de page_views_total
--   - data_updated_at            → alias literal de rows_updated_at
--   - frecuencia_declarada       → alias literal de update_frequency
--   - api_url                    → técnico (devs), NULL en federados
--   - last_refreshed_at          → telemetría ETL → header HTTP Last-Modified
--
-- KEEP (29 columnas) — con metadata de cobertura conocida documentada.
--
-- Idempotente: CREATE OR REPLACE.

BEGIN;

-- =============================================================================
-- v_dataset_status_decisor — 29 columnas curadas
-- =============================================================================
CREATE OR REPLACE VIEW v_dataset_status_decisor AS
SELECT
    -- ── Identidad ──
    d.dataset_id,
    d.name AS dataset_name,
    d.entity_id,
    e.name AS entity_name,
    e.abbrev AS entity_abbrev,

    -- ── Catalogación (cobertura parcial: 88.9% global, 96.5% nativos) ──
    d.category,

    -- ── Frescura (semáforo completo) ──
    d.rows_updated_at,
    d.update_frequency,
    parse_frequency_days(d.update_frequency) AS frequency_days,
    CASE
        WHEN d.rows_updated_at IS NULL THEN NULL
        ELSE EXTRACT(EPOCH FROM (NOW() - d.rows_updated_at))::INTEGER / 86400
    END AS days_since_update,
    compute_status(d.rows_updated_at, d.update_frequency) AS status,

    -- ── Engagement (NULL en federados = no aplica vía API Socrata) ──
    d.row_count,
    d.page_views_total,
    d.page_views_last_week,
    d.page_views_last_month,
    d.download_count,

    -- ── Fechas de catálogo (100% global) ──
    d.metadata_updated_at,
    d.publication_date,

    -- ── Atributos editoriales ──
    d.provenance,
    d.license_id,
    d.cobertura_geografica,
    d.jurisdiccion_nivel,
    d.sector,

    -- ── Señales sociales (NULL = sin interacción, lectura honesta) ──
    d.number_of_comments,
    d.total_times_rated,

    -- ── Link público ──
    d.socrata_url,

    -- ── Marcadores de calidad y segmentación ──
    d.quality_flag,
    CASE WHEN d.source_type = 'federated' THEN 'sí' ELSE 'no' END AS es_federado,
    CASE
        WHEN d.source_type = 'socrata' THEN 'directo'
        WHEN d.source_type = 'federated' AND d.federated_status = 'ok' THEN 'requiere_herramienta'
        ELSE 'solo_metadatos'
    END AS acceso_datos

FROM datasets d
LEFT JOIN entities e ON e.entity_id = d.entity_id;

COMMENT ON VIEW v_dataset_status_decisor IS
'Tabla maestra del tablero del Director (Hito R 2026-06-08). 29 cols vs 34 de v_dataset_status. Drop: 3 alias literales + api_url + last_refreshed_at. KEEP: comments/rated (NULL=sin interacción, señal real). Cobertura cobertura_geografica/jurisdiccion/sector/license_id es 100% nativos + 100% CKAN + 0% datos.gov.co federados (la fuente no declara).';


-- =============================================================================
-- v_entity_summary_decisor — 11 originales + 3 derivadas (= 14 columnas)
-- =============================================================================
CREATE OR REPLACE VIEW v_entity_summary_decisor AS
SELECT
    e.entity_id,
    e.name AS entity_name,
    e.abbrev AS entity_abbrev,

    -- ── Volumen ──
    COUNT(DISTINCT d.dataset_id) AS n_datasets,
    COUNT(DISTINCT d.dataset_id) FILTER (WHERE d.source_type = 'socrata') AS n_datasets_directos,
    COUNT(DISTINCT d.dataset_id) FILTER (WHERE d.source_type = 'federated') AS n_datasets_federados,

    -- ── Telemetría ciudadano (NULL/cero = sin uso, lectura honesta) ──
    COUNT(DISTINCT du.query_id) FILTER (WHERE du.created_at >= NOW() - INTERVAL '30 days') AS n_queries_30d,
    COUNT(DISTINCT du.query_id) AS n_queries_total,
    MAX(du.created_at) AS last_access_at,

    -- ── Semáforo (KPI principal) ──
    COUNT(DISTINCT d.dataset_id) FILTER (WHERE compute_status(d.rows_updated_at, d.update_frequency) = 'verde') AS datasets_verdes,
    COUNT(DISTINCT d.dataset_id) FILTER (WHERE compute_status(d.rows_updated_at, d.update_frequency) = 'amarillo') AS datasets_amarillos,
    COUNT(DISTINCT d.dataset_id) FILTER (WHERE compute_status(d.rows_updated_at, d.update_frequency) = 'rojo') AS datasets_rojos,
    COUNT(DISTINCT d.dataset_id) FILTER (WHERE d.rows_updated_at IS NULL) AS datasets_sin_fecha,

    -- ── Cumplimiento derivado ──
    ROUND(
      100.0 * COUNT(DISTINCT d.dataset_id) FILTER (
        WHERE compute_status(d.rows_updated_at, d.update_frequency) = 'verde'
      ) / NULLIF(COUNT(DISTINCT d.dataset_id), 0),
      1
    ) AS pct_verdes

FROM entities e
LEFT JOIN datasets d ON d.entity_id = e.entity_id
LEFT JOIN dataset_usage du ON du.dataset_id = d.dataset_id
GROUP BY e.entity_id, e.name, e.abbrev
ORDER BY n_datasets DESC NULLS LAST;

COMMENT ON VIEW v_entity_summary_decisor IS
'Resumen por entidad para el tablero del Director (Hito R 2026-06-08). 14 cols (11 originales + 3 derivadas: pct_verdes, n_datasets_directos, n_datasets_federados). Telemetría dataset_usage permanece como columna (cero = no consultado, señal honesta de adopción).';

COMMIT;

-- =============================================================================
-- Verificación inmediata
-- =============================================================================
SELECT 'v_dataset_status_decisor' AS view, COUNT(*) AS rows FROM v_dataset_status_decisor
UNION ALL
SELECT 'v_entity_summary_decisor', COUNT(*) FROM v_entity_summary_decisor;
