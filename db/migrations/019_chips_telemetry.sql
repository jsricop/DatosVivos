-- 019_chips_telemetry.sql
--
-- Telemetría de adopción para los paths de Hito 1 (chips → cifra →
-- narrativa). La tabla `queries` existente cubre el path NL→LLM SSE
-- (POST /api/v1/query). Esta nueva tabla cubre los endpoints chips,
-- que tienen otra forma de evento y otras métricas relevantes.
--
-- No usamos partition aún — empezamos con tabla simple, agregamos
-- partition por fecha si crece >10M filas.

BEGIN;

CREATE TABLE IF NOT EXISTS chips_telemetry (
    id              BIGSERIAL PRIMARY KEY,
    ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    endpoint        VARCHAR(40) NOT NULL,    -- 'execute' | 'explain' | 'from_nl'
    dataset_id      VARCHAR(20),             -- NULL para from_nl
    tipo            VARCHAR(20),             -- ChipTipo o NULL
    source_type     VARCHAR(20),             -- 'socrata' | 'federated' | NULL
    source_portal   VARCHAR(80),             -- portal del dataset
    elapsed_ms      INTEGER,                 -- tiempo del endpoint
    row_count       INTEGER,                 -- filas devueltas
    soql_chars      INTEGER,                 -- longitud de la query (proxy de complejidad)
    error           TEXT,                    -- mensaje de error si hubo; NULL si OK
    hallucinated    INTEGER,                 -- # cifras espurias (Explain); NULL si N/A
    -- Para from_nl
    nl_query_hash   CHAR(40),                -- sha1 del query libre (privacidad)
    chips_picked    INTEGER                  -- # chips que el LLM pudo inferir
);

CREATE INDEX IF NOT EXISTS idx_chips_tel_ts        ON chips_telemetry(ts DESC);
CREATE INDEX IF NOT EXISTS idx_chips_tel_endpoint  ON chips_telemetry(endpoint);
CREATE INDEX IF NOT EXISTS idx_chips_tel_dataset   ON chips_telemetry(dataset_id);
CREATE INDEX IF NOT EXISTS idx_chips_tel_error_ts  ON chips_telemetry(ts DESC) WHERE error IS NOT NULL;

COMMIT;
