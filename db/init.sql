-- DatosVivos — Schema inicial PostgreSQL 16
-- Tablas para logs de consultas, métricas de uso y operaciones de cruce.
-- Power BI se conecta a estas tablas para el dashboard de analítica.

CREATE TABLE queries (
    id              SERIAL PRIMARY KEY,
    session_id      UUID NOT NULL,
    user_query      TEXT NOT NULL,
    intent_type     VARCHAR(50),        -- search, descriptive, comparative, temporal, cross_source
    datasets_used   TEXT[],             -- array de dataset_ids consultados
    response_text   TEXT,
    execution_ms    INTEGER,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE dataset_usage (
    id              SERIAL PRIMARY KEY,
    dataset_id      VARCHAR(20) NOT NULL,
    dataset_name    TEXT,
    entity          TEXT,               -- entidad publicadora
    query_id        INTEGER REFERENCES queries(id),
    action          VARCHAR(20),        -- search, metadata, query, cross
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE cross_operations (
    id              SERIAL PRIMARY KEY,
    query_id        INTEGER REFERENCES queries(id),
    dataset_a_id    VARCHAR(20) NOT NULL,
    dataset_b_id    VARCHAR(20) NOT NULL,
    join_key        VARCHAR(100),       -- DIVIPOLA, codigo_dane, nit, etc.
    rows_result     INTEGER,
    created_at      TIMESTAMP DEFAULT NOW()
);
