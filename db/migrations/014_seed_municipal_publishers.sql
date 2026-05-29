-- 014_seed_municipal_publishers.sql
--
-- Bug 3 — sembrar publishers municipales más frecuentes para que los 824
-- datasets harvested de Cali/Valle (y futuros municipios) resuelvan
-- entity_id. Hoy todos tienen entity_id=NULL porque entities solo cubría
-- entidades nacionales y distritales.
--
-- Top 15 publishers Cali sin resolver = 654 datasets (85% de los huérfanos
-- municipales). El sufijo "(Cali)" en `name` es informativo para el
-- display; el matching del resolver usa lower(name) word-boundary contra
-- entity_raw (que NO incluye el sufijo), así que el match real es por
-- el prefijo "Secretaría de Salud Pública" etc.
--
-- IMPORTANTE: el resolver corre _word_match exacto. Si el publisher
-- pone "Secretaría de Salud Pública" pero la entidad se llama
-- "Secretaría de Salud Pública (Cali)", _word_match("secretaría de salud
-- pública (cali)", "secretaría de salud pública") es FALSO porque la
-- versión más larga no es substring de la más corta. Tenemos dos opciones:
--   a) Insertar el name TAL CUAL viene de Common-Core_Publisher (sin
--      sufijo) y aceptar que hay AMBIGÜEDAD con Bogotá si existe el
--      mismo nombre.
--   b) Insertar con sufijo + cambiar el resolver.
-- Vamos con (a) por hoy: el ORDER BY length(name) DESC del resolver
-- prefiere el match más específico cuando hay colisión, y los Cali son
-- publishers únicos (no chocan con bogotanos del mismo nombre).
--
-- Idempotente: NOT EXISTS por lower-trim del name.

BEGIN;

INSERT INTO entities (name, abbrev, kind)
SELECT v.name, v.abbrev, 'territorial'
FROM (VALUES
    -- Cali — top 15 publishers harvested (cubren 654 datasets)
    ('Departamento Administrativo de Planeación Municipal', NULL),
    ('Secretaría de Salud Pública', NULL),
    ('Secretaría de Seguridad y Justicia', NULL),
    ('Unidad Administrativa Especial de Gestión de Bienes y Servicios', NULL),
    ('Departamento Administrativo de Gestión del Medio Ambiente', NULL),
    ('Secretaría de Educación', NULL),
    ('Secretaría de Cultura', NULL),
    ('Secretaría de Desarrollo Territorial y Participación Ciudadana', NULL),
    ('Unidad Administrativa Especial Teatro Municipal', NULL),
    ('Departamento Administrativo de Hacienda Municipal', NULL),
    ('Unidad Administrativa Especial de Servicios Públicos Municipales', NULL),
    ('Secretaría de Turismo', NULL),
    ('Secretaría de Infraestructura', NULL),
    ('Departamento Administrativo de Control Disciplinario Interno', NULL),
    ('Secretaría de Bienestar Social', NULL)
) AS v(name, abbrev)
WHERE NOT EXISTS (
    SELECT 1 FROM entities e
    WHERE lower(trim(e.name)) = lower(trim(v.name))
);

COMMIT;
