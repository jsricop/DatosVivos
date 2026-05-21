-- DatosVivos — Schema PostgreSQL 16 productivo
-- ADR-014 (supersede ADR-008): se activa Postgres como BD productiva para
-- alimentar el dashboard PowerBI ejecutivo embebido en /tablero.
--
-- Convenciones:
--   * snake_case en todo
--   * timestamps en UTC con TIMESTAMPTZ
--   * UUID para IDs públicos (queries, etl_runs); SERIAL para internos
--   * VIEWS materializadas refrescadas por cron (ver scripts/etl_refresh_catalog.py)

-- ============================================================
-- 1. DIRECTORIO DE ENTIDADES DEL ESTADO
-- ============================================================

CREATE TABLE entities (
    entity_id       SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,                  -- "Ministerio de Salud y Protección Social"
    abbrev          TEXT,                           -- "MinSalud"
    domain_email    TEXT UNIQUE,                    -- "@minsalud.gov.co" — mapping para magic-link
    kind            VARCHAR(30) DEFAULT 'nacional', -- nacional | territorial | descentralizada
    parent_id       INTEGER REFERENCES entities(entity_id),  -- jerarquía (Mintic, ANI = parent ministerio)
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_entities_domain ON entities(domain_email);
CREATE INDEX idx_entities_abbrev ON entities(abbrev);

-- Seed mínimo de entidades reconocidas (se enriquece después con cargas masivas)
INSERT INTO entities (name, abbrev, domain_email, kind) VALUES
    ('Agencia Nacional de Infraestructura', 'ANI', '@ani.gov.co', 'descentralizada'),
    ('Ministerio de Tecnologías de la Información y las Comunicaciones', 'MinTIC', '@mintic.gov.co', 'nacional'),
    ('Ministerio de Salud y Protección Social', 'MinSalud', '@minsalud.gov.co', 'nacional'),
    ('Ministerio de Educación Nacional', 'MinEducación', '@mineducacion.gov.co', 'nacional'),
    ('Ministerio de Justicia y del Derecho', 'MinJusticia', '@minjusticia.gov.co', 'nacional'),
    ('Departamento Administrativo Nacional de Estadística', 'DANE', '@dane.gov.co', 'descentralizada'),
    ('Departamento Nacional de Planeación', 'DNP', '@dnp.gov.co', 'descentralizada'),
    ('Policía Nacional de Colombia', 'Policía Nacional', '@policia.gov.co', 'nacional'),
    ('Instituto Colombiano Agropecuario', 'ICA', '@ica.gov.co', 'descentralizada'),
    ('Instituto Nacional de Vías', 'INVÍAS', '@invias.gov.co', 'descentralizada'),
    ('Instituto de Hidrología, Meteorología y Estudios Ambientales', 'IDEAM', '@ideam.gov.co', 'descentralizada')
ON CONFLICT (domain_email) DO NOTHING;

-- ============================================================
-- 2. CATÁLOGO DE DATASETS (enriquecido con Socrata Metadata API)
-- ============================================================

CREATE TABLE datasets (
    dataset_id          VARCHAR(20) PRIMARY KEY,            -- 4x4 Socrata (ej. gdxc-w37w)
    name                TEXT NOT NULL,
    entity_id           INTEGER REFERENCES entities(entity_id),
    entity_raw          TEXT,                                -- nombre tal cual viene de Socrata, sin matching
    category            TEXT,
    description         TEXT,
    rows_updated_at     TIMESTAMPTZ,                         -- Socrata rowsUpdatedAt
    update_frequency    TEXT,                                -- "Annual" | "Quarterly" | "Monthly" | "Weekly" | "Daily" | "Real-time" | null
    row_count           BIGINT,
    view_count          BIGINT,
    created_at_socrata  TIMESTAMPTZ,                         -- Socrata createdAt
    socrata_url         TEXT,                                -- página humana datos.gov.co/d/{id}
    api_url             TEXT,                                -- endpoint JSON SODA
    last_refreshed_at   TIMESTAMPTZ DEFAULT NOW()            -- cuándo el ETL trajo este registro
);

CREATE INDEX idx_datasets_entity ON datasets(entity_id);
CREATE INDEX idx_datasets_category ON datasets(category);
CREATE INDEX idx_datasets_rows_updated ON datasets(rows_updated_at);

CREATE TABLE dataset_tags (
    dataset_id      VARCHAR(20) REFERENCES datasets(dataset_id) ON DELETE CASCADE,
    tag             TEXT NOT NULL,
    PRIMARY KEY (dataset_id, tag)
);

CREATE INDEX idx_dataset_tags_tag ON dataset_tags(tag);

-- ============================================================
-- 3. TELEMETRÍA DE CONSULTAS (espejo de data/telemetry/queries.csv)
-- ============================================================

CREATE TABLE queries (
    id                  BIGSERIAL PRIMARY KEY,
    session_id          UUID DEFAULT gen_random_uuid(),
    timestamp_iso       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    question            TEXT NOT NULL,
    intent              VARCHAR(50),                         -- search | descriptive | comparative | temporal | cross_source
    datasets_used       TEXT[],                              -- array de IDs Socrata
    soql_executed       TEXT,
    rows_count          INTEGER,
    censored_count      INTEGER,
    elapsed_s           NUMERIC(10, 2),
    had_statistics      BOOLEAN DEFAULT FALSE,
    CONSTRAINT queries_unique_run UNIQUE (timestamp_iso, question)
);

CREATE INDEX idx_queries_ts ON queries(timestamp_iso DESC);
CREATE INDEX idx_queries_intent ON queries(intent);
CREATE INDEX idx_queries_datasets ON queries USING GIN (datasets_used);

-- Tabla auxiliar 1:N: dataset → query — facilita joins y aggregations PowerBI.
CREATE TABLE dataset_usage (
    id              BIGSERIAL PRIMARY KEY,
    dataset_id      VARCHAR(20) NOT NULL,                    -- no FK: pueden venir datasets no indexados aún
    query_id        BIGINT NOT NULL REFERENCES queries(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_dataset_usage_dataset ON dataset_usage(dataset_id);
CREATE INDEX idx_dataset_usage_query ON dataset_usage(query_id);
CREATE INDEX idx_dataset_usage_created ON dataset_usage(created_at DESC);

-- Cross-source (mantiene compat con schema viejo, no usado todavía por Beta-2)
CREATE TABLE cross_operations (
    id              BIGSERIAL PRIMARY KEY,
    query_id        BIGINT REFERENCES queries(id) ON DELETE CASCADE,
    dataset_a_id    VARCHAR(20) NOT NULL,
    dataset_b_id    VARCHAR(20) NOT NULL,
    join_key        VARCHAR(100),
    rows_result     INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 4. AUTH / AUDITORÍA
-- ============================================================

CREATE TABLE auth_events (
    event_id        BIGSERIAL PRIMARY KEY,
    email           TEXT NOT NULL,
    entity_id       INTEGER REFERENCES entities(entity_id),
    event_type      VARCHAR(40) NOT NULL,                    -- magic_link_requested | magic_link_consumed | login_success | login_rejected | logout
    ip              INET,
    user_agent      TEXT,
    detail          JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_auth_events_email ON auth_events(email);
CREATE INDEX idx_auth_events_entity ON auth_events(entity_id);
CREATE INDEX idx_auth_events_created ON auth_events(created_at DESC);

-- ============================================================
-- 5. ETL RUNS (telemetría del propio cron)
-- ============================================================

CREATE TABLE etl_runs (
    run_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_name         TEXT NOT NULL,                       -- 'etl_refresh_catalog' | 'migrate_telemetry_csv'
    started_at          TIMESTAMPTZ DEFAULT NOW(),
    finished_at         TIMESTAMPTZ,
    datasets_total      INTEGER,
    datasets_succeeded  INTEGER,
    datasets_failed     INTEGER,
    error               TEXT
);

CREATE INDEX idx_etl_runs_script_started ON etl_runs(script_name, started_at DESC);

-- ============================================================
-- 6. FUNCIÓN compute_status
-- ============================================================

-- Mapea Socrata `updateFrequency` (libre, ej. "Annual", "Anual", "Cada año",
-- "every month") a un intervalo en días. Si no se reconoce, retorna NULL para
-- que el caller use el fallback fijo (30/180 d).
CREATE OR REPLACE FUNCTION parse_frequency_days(freq TEXT)
RETURNS INTEGER
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    f TEXT;
BEGIN
    IF freq IS NULL OR length(trim(freq)) = 0 THEN
        RETURN NULL;
    END IF;
    f := lower(trim(freq));
    -- Inglés
    IF f IN ('annual', 'annually', 'yearly') THEN RETURN 365; END IF;
    IF f IN ('semi-annual', 'semiannually', 'biannual') THEN RETURN 182; END IF;
    IF f IN ('quarterly') THEN RETURN 91; END IF;
    IF f IN ('monthly') THEN RETURN 30; END IF;
    IF f IN ('biweekly', 'fortnightly') THEN RETURN 14; END IF;
    IF f IN ('weekly') THEN RETURN 7; END IF;
    IF f IN ('daily') THEN RETURN 1; END IF;
    IF f IN ('real-time', 'realtime', 'continuous') THEN RETURN 1; END IF;
    -- Español (Socrata permite cualquier string)
    IF f LIKE '%anual%' OR f LIKE '%año%' THEN RETURN 365; END IF;
    IF f LIKE '%trimestr%' THEN RETURN 91; END IF;
    IF f LIKE '%mensual%' OR f LIKE '%mes%' THEN RETURN 30; END IF;
    IF f LIKE '%quincen%' THEN RETURN 14; END IF;
    IF f LIKE '%semanal%' OR f LIKE '%semana%' THEN RETURN 7; END IF;
    IF f LIKE '%diari%' OR f LIKE '%día%' THEN RETURN 1; END IF;
    IF f LIKE '%tiempo real%' THEN RETURN 1; END IF;
    RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION compute_status(updated_at TIMESTAMPTZ, frequency TEXT)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    threshold_days INTEGER;
    days_elapsed INTEGER;
BEGIN
    IF updated_at IS NULL THEN
        RETURN 'desconocido';
    END IF;
    days_elapsed := EXTRACT(EPOCH FROM (NOW() - updated_at))::INTEGER / 86400;
    threshold_days := parse_frequency_days(frequency);
    IF threshold_days IS NULL THEN
        -- Fallback fijo
        IF days_elapsed <= 30 THEN RETURN 'verde'; END IF;
        IF days_elapsed <= 180 THEN RETURN 'amarillo'; END IF;
        RETURN 'rojo';
    END IF;
    -- Umbral según frecuencia declarada × 2
    IF days_elapsed <= threshold_days THEN RETURN 'verde'; END IF;
    IF days_elapsed <= threshold_days * 2 THEN RETURN 'amarillo'; END IF;
    RETURN 'rojo';
END;
$$;

-- ============================================================
-- 7. VIEWS PARA POWERBI
-- ============================================================

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
    d.last_refreshed_at
FROM datasets d
LEFT JOIN entities e ON e.entity_id = d.entity_id;

-- Uso agregado por dataset (cruce con telemetría).
CREATE OR REPLACE VIEW v_dataset_usage AS
SELECT
    du.dataset_id,
    COUNT(*) AS n_queries_total,
    COUNT(*) FILTER (WHERE du.created_at >= NOW() - INTERVAL '30 days') AS n_queries_30d,
    COUNT(*) FILTER (WHERE du.created_at >= NOW() - INTERVAL '90 days') AS n_queries_90d,
    MAX(du.created_at) AS last_query_at,
    EXTRACT(EPOCH FROM (NOW() - MAX(du.created_at)))::INTEGER / 86400 AS days_since_last_query,
    MODE() WITHIN GROUP (ORDER BY q.intent) AS top_intent,
    AVG(q.elapsed_s)::NUMERIC(10, 2) AS avg_elapsed_s
FROM dataset_usage du
LEFT JOIN queries q ON q.id = du.query_id
GROUP BY du.dataset_id;

-- Vista maestra por entidad (la que PowerBI página 1 consume directo).
CREATE OR REPLACE VIEW v_entity_summary AS
SELECT
    e.entity_id,
    e.name AS entity_name,
    e.abbrev AS entity_abbrev,
    COUNT(DISTINCT d.dataset_id) AS n_datasets,
    COUNT(DISTINCT du.query_id) FILTER (WHERE du.created_at >= NOW() - INTERVAL '30 days') AS n_queries_30d,
    COUNT(DISTINCT du.query_id) AS n_queries_total,
    COUNT(DISTINCT d.dataset_id) FILTER (WHERE compute_status(d.rows_updated_at, d.update_frequency) = 'verde') AS datasets_verdes,
    COUNT(DISTINCT d.dataset_id) FILTER (WHERE compute_status(d.rows_updated_at, d.update_frequency) = 'amarillo') AS datasets_amarillos,
    COUNT(DISTINCT d.dataset_id) FILTER (WHERE compute_status(d.rows_updated_at, d.update_frequency) = 'rojo') AS datasets_rojos,
    COUNT(DISTINCT d.dataset_id) FILTER (WHERE d.rows_updated_at IS NULL) AS datasets_sin_fecha,
    MAX(du.created_at) AS last_access_at
FROM entities e
LEFT JOIN datasets d ON d.entity_id = e.entity_id
LEFT JOIN dataset_usage du ON du.dataset_id = d.dataset_id
GROUP BY e.entity_id, e.name, e.abbrev;

-- Top 10 datasets más consultados (página benchmark).
CREATE OR REPLACE VIEW v_top_datasets AS
SELECT
    d.dataset_id,
    d.name AS dataset_name,
    e.abbrev AS entity_abbrev,
    d.category,
    COUNT(du.id) AS n_queries,
    MAX(du.created_at) AS last_query_at
FROM datasets d
LEFT JOIN entities e ON e.entity_id = d.entity_id
LEFT JOIN dataset_usage du ON du.dataset_id = d.dataset_id
GROUP BY d.dataset_id, d.name, e.abbrev, d.category
ORDER BY n_queries DESC NULLS LAST
LIMIT 10;

-- Cuenta por día (calendario PowerBI con tendencia).
CREATE OR REPLACE VIEW v_queries_daily AS
SELECT
    DATE_TRUNC('day', timestamp_iso)::DATE AS query_date,
    COUNT(*) AS n_queries,
    COUNT(DISTINCT unnest(datasets_used)) AS n_distinct_datasets,
    AVG(elapsed_s)::NUMERIC(10, 2) AS avg_elapsed_s
FROM queries
GROUP BY DATE_TRUNC('day', timestamp_iso);

-- ============================================================
-- 8. EXTENSIONES
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid()
