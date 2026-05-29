-- 011_parse_frequency_dcat.sql
--
-- Hito Q.7.a — el audit reveló ~318 datasets federados con
-- `update_frequency` en formato ISO 8601 DCAT (`R/P1Y`, `R/P1M`, `R/P3M`,
-- `R/P6M`, `R/P1D`, `R/PT1S`, `R/P4Y`, `R/P2M`, `R/P3Y`) que la versión
-- previa de `parse_frequency_days` no reconocía → devolvía NULL → semáforo
-- caía al fallback fijo 30/180 días.
--
-- DCAT v1.1 (https://www.w3.org/TR/vocab-dcat/#Property:dataset_frequency)
-- usa `R/P<n><unit>` donde:
--   - R/  → repetición indefinida
--   - P<n>Y / P<n>M / P<n>W / P<n>D → periodo de n años/meses/semanas/días
--   - PT<n>H / PT<n>M / PT<n>S → periodo sub-diario (lo tratamos como 1 día)
--
-- Preferencia: cuando el N coincide con un nombre español estándar
-- (Trimestral/Semestral/Cuatrimestral), uso el día canónico de migración 007
-- (91/182/122) en vez del cálculo n*30, para que el semáforo sea
-- consistente entre nativos y federados que declaran la misma frecuencia.
--
-- Idempotente: CREATE OR REPLACE. La vista v_dataset_status recalcula al
-- vuelo, no necesita refresh.

BEGIN;

CREATE OR REPLACE FUNCTION parse_frequency_days(freq TEXT)
RETURNS INTEGER
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    f TEXT;
    n INTEGER;
BEGIN
    IF freq IS NULL OR length(trim(freq)) = 0 THEN
        RETURN NULL;
    END IF;
    f := lower(trim(freq));
    -- Inglés (Socrata global)
    IF f IN ('annual', 'annually', 'yearly') THEN RETURN 365; END IF;
    IF f IN ('semi-annual', 'semiannually', 'biannual') THEN RETURN 182; END IF;
    IF f IN ('quarterly') THEN RETURN 91; END IF;
    IF f IN ('monthly') THEN RETURN 30; END IF;
    IF f IN ('biweekly', 'fortnightly') THEN RETURN 14; END IF;
    IF f IN ('weekly') THEN RETURN 7; END IF;
    IF f IN ('daily') THEN RETURN 1; END IF;
    IF f IN ('real-time', 'realtime', 'continuous') THEN RETURN 1; END IF;
    -- DCAT ISO 8601 (federados, Common-Core_Update-Frequency)
    --   subdiario PT* → 1
    --   R/P<n>Y / R/P<n>M / R/P<n>W / R/P<n>D
    IF f ~ '^r/pt' THEN RETURN 1; END IF;
    IF f ~ '^r/p[0-9]+y$' THEN
        n := substring(f from '^r/p([0-9]+)y$')::int;
        RETURN n * 365;
    END IF;
    IF f ~ '^r/p[0-9]+m$' THEN
        n := substring(f from '^r/p([0-9]+)m$')::int;
        IF n = 6 THEN RETURN 182; END IF;
        IF n = 4 THEN RETURN 122; END IF;
        IF n = 3 THEN RETURN 91; END IF;
        RETURN n * 30;
    END IF;
    IF f ~ '^r/p[0-9]+w$' THEN
        n := substring(f from '^r/p([0-9]+)w$')::int;
        RETURN n * 7;
    END IF;
    IF f ~ '^r/p[0-9]+d$' THEN
        n := substring(f from '^r/p([0-9]+)d$')::int;
        RETURN n;
    END IF;
    -- "irregular" → sin schedule conocido → fallback fijo (NULL).
    IF f = 'irregular' THEN RETURN NULL; END IF;
    -- Español (Socrata permite cualquier string). Orden importa: las
    -- subcadenas más específicas van primero (ver migración 007).
    IF f LIKE '%más de tres año%' OR f LIKE '%mas de tres año%' THEN RETURN 1095; END IF;
    IF f LIKE '%trieni%' THEN RETURN 1095; END IF;
    IF f LIKE '%bieni%' THEN RETURN 730; END IF;
    IF f LIKE '%semestr%' THEN RETURN 182; END IF;
    IF f LIKE '%cuatrimestr%' THEN RETURN 122; END IF;
    IF f LIKE '%trimestr%' THEN RETURN 91; END IF;
    IF f LIKE '%quincen%' THEN RETURN 14; END IF;
    IF f LIKE '%anual%' OR f LIKE '%año%' THEN RETURN 365; END IF;
    IF f LIKE '%mensual%' OR f LIKE '%mes%' THEN RETURN 30; END IF;
    IF f LIKE '%semanal%' OR f LIKE '%semana%' THEN RETURN 7; END IF;
    IF f LIKE '%diari%' OR f LIKE '%día%' THEN RETURN 1; END IF;
    IF f LIKE '%tiempo real%' THEN RETURN 1; END IF;
    RETURN NULL;
END;
$$;

COMMIT;
