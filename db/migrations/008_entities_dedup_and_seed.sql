-- 008_entities_dedup_and_seed.sql
--
-- Validado contra Socrata Discovery API (campo `attribution`, fuente
-- autoritativa). Dos correcciones:
--
-- 1) Duplicado: entity_id=6 "Departamento Administrativo Nacional de
--    Estadística" (typo, sin "s") tiene 0 datasets locales y 0 en Socrata;
--    el canónico es entity_id=1090 "...Estadísticas" (con "s"), atribución
--    real "Departamento Administrativo Nacional de Estadísticas - DANE,
--    Bogotá D.C." con 2 datasets. Eliminamos el typo.
--
-- 2) Entidades reales del catálogo Socrata que el `entities` seed no
--    cubría → sus datasets terminaban en `entity_id=NULL` (o, antes del
--    fix de _build_entity_resolver, en atribuciones espurias). Counts
--    verificados vía resource.attribution en Discovery API:
--      INVIMA  → 57 datasets
--      INPEC   →  8
--      SNR     →  1 (Superintendencia de Notariado y Registro)
--      EJC     →  1 (Ejército Nacional de Colombia)
--
-- Idempotente: borrado guardado por chequeo de existencia; inserts usan
-- ON CONFLICT DO NOTHING contra (name) lower-trim para evitar duplicados.

BEGIN;

-- (1) Eliminar DANE duplicado (typo "Estadística" sin "s"). Pre-flight:
-- no debe tener datasets atribuidos (la migración aborta si los hay,
-- ahí algo se nos pasó y hay que investigar antes de borrar).
DO $$
DECLARE
    n_refs INTEGER;
BEGIN
    SELECT COUNT(*) INTO n_refs FROM datasets WHERE entity_id = 6;
    IF n_refs > 0 THEN
        RAISE EXCEPTION 'Aborting: entity_id=6 tiene % datasets atribuidos, esperaba 0', n_refs;
    END IF;
    DELETE FROM entities WHERE entity_id = 6;
END $$;

-- (2) Sembrar 4 entidades faltantes (kind/parent quedan defaults; un
-- seeding más rico es trabajo aparte). Salvaguarda: si ya existen por
-- nombre, no duplicar.
INSERT INTO entities (name, abbrev, kind)
SELECT v.name, v.abbrev, 'descentralizada'
FROM (VALUES
    ('Instituto Nacional de Vigilancia de Medicamentos y Alimentos', 'INVIMA'),
    ('Instituto Nacional Penitenciario y Carcelario', 'INPEC'),
    ('Superintendencia de Notariado y Registro', 'SNR'),
    ('Ejército Nacional de Colombia', NULL)
) AS v(name, abbrev)
WHERE NOT EXISTS (
    SELECT 1 FROM entities e
    WHERE lower(trim(e.name)) = lower(trim(v.name))
);

COMMIT;
