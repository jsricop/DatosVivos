-- 016_seed_valle_publishers.sql
--
-- Quick win — sembrar publishers Valle Datos Abiertos que el seed 014
-- (Cali) no cubrió porque tienen nombres distintos. Top 15 publishers
-- huérfanos del harvested Valle CKAN cubren 40/43 datasets (93%).
--
-- Nota: algunos nombres son muy similares a los de Cali pero no
-- idénticos (ej. "Secretaría de Salud" vs "Secretaría de Salud Pública")
-- — los insertamos como entidades separadas porque el resolver hace
-- word-boundary match exacto.

BEGIN;

INSERT INTO entities (name, abbrev, kind)
SELECT v.name, v.abbrev, 'territorial'
FROM (VALUES
    ('Unidad administrativa Especial de Catastro', NULL),
    ('Secretaría de las Tecnologías de la Información y las Comunicaciones', NULL),
    ('Secretaría de Desarrollo Económico, Competitividad', NULL),
    ('Secretaría General', NULL),
    ('Secretaría de Desarrollo, Inclusión y Participación Social', NULL),
    ('Secretaría de Salud', NULL),
    ('Secretaría Agricultura y Desarrollo Rural', NULL),
    ('Secretaría de Vivienda y Hábitat', NULL),
    ('Departamento Administrativo de Desarrollo Institucional', NULL),
    ('Secretaría de Mujer, Equidad de Género y Diversidad Sexual', NULL),
    ('Departamento Administrativo de Hacienda y Finanzas Pública', NULL),
    ('Departamento Administrativo de Planeación', NULL),
    ('Secretaria de Asuntos Étnicos', NULL),
    ('Secretaría de Paz Territorial y Reconciliación', NULL),
    ('Secretaría de Ambiente y Desarrollo Sostenible', NULL)
) AS v(name, abbrev)
WHERE NOT EXISTS (
    SELECT 1 FROM entities e
    WHERE lower(trim(e.name)) = lower(trim(v.name))
);

COMMIT;
