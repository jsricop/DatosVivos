-- 012_seed_federated_publishers.sql
--
-- Hito Q.7.d follow-up — siembra de los 10 publishers federados con más
-- datasets huérfanos (entity_id=NULL) detectados en el audit. Cubre
-- ~2.150 de los 2.626 federados sin resolver (82%). Eleva la resolución
-- de federados de 73.7% a ≥ 90%.
--
-- Los nombres están copiados EXACTOS de `Common-Core_Publisher` de los
-- payloads Discovery — incluyendo variantes sin tilde donde el publicador
-- los registra así (ej. "Gobernacion Valle del Cauca"). El resolver
-- `_build_entity_resolver` usa `_word_match` lower-cased y necesita
-- coincidencia textual, así que respetamos la forma original.
--
-- Insert idempotente con NOT EXISTS por nombre normalizado lower-trim.

BEGIN;

INSERT INTO entities (name, abbrev, kind)
SELECT v.name, v.abbrev, v.kind
FROM (VALUES
    ('Corporación Autónoma Regional de Cundinamarca', 'CAR', 'descentralizada'),
    ('Alcaldía Distrital de Santiago de Cali', NULL, 'territorial'),
    ('Secretaría Distrital de Planeación', NULL, 'territorial'),
    ('Instituto Amazónico de Investigaciones Científicas', 'SINCHI', 'descentralizada'),
    ('Empresa de Acueducto y Alcantarillado de Bogotá', 'EAAB', 'territorial'),
    ('Gobernacion Valle del Cauca', NULL, 'territorial'),
    ('Secretaría Distrital del Hábitat', NULL, 'territorial'),
    ('Secretaría Distrital de Hacienda', NULL, 'territorial'),
    ('Laboratorio SIG y SR - Instituto SINCHI', NULL, 'descentralizada'),
    ('Secretaría Distrital de Integración Social', NULL, 'territorial')
) AS v(name, abbrev, kind)
WHERE NOT EXISTS (
    SELECT 1 FROM entities e
    WHERE lower(trim(e.name)) = lower(trim(v.name))
);

COMMIT;
