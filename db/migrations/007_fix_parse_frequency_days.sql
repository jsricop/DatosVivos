-- 007_fix_parse_frequency_days.sql
--
-- Fix de orden en parse_frequency_days(): 'Semestral' caía en %mes% → 30,
-- 'Cuatrimestral' caía en %trimestr% → 91, 'Trienio'/'Más de tres años'
-- quedaban sin resolver o caían en %año% → 365. Las subcadenas más
-- específicas deben evaluarse antes que las genéricas.
--
-- v_dataset_status calcula frequency_days vía esta función en cada SELECT,
-- así que basta con CREATE OR REPLACE: el semáforo refleja el fix en la
-- siguiente lectura. Idempotente y reversible (re-corriendo init.sql
-- antiguo se vuelve atrás).

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
    -- Español (Socrata permite cualquier string). Orden importa: las
    -- subcadenas más específicas van primero para que 'semestral' no
    -- caiga en %mes%, 'cuatrimestral' no caiga en %trimestr%, etc.
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
