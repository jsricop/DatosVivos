# Inventario de campos CKAN — Bogotá / Cali / Valle

Fecha: 2026-06-08 · Sample: 5 packages por portal · Endpoint: `/api/3/action/package_search`

## Contexto

El harvester `scripts/harvest_ckan.py` actual extrae solo 7 campos por package: `name`, `organization.title`, `groups[0].title`, `notes`, `license_title`, `last_modified`, `created`, resources URL. **Los 4.625 datasets CKAN (Bogotá 3.801 + Cali 768 + Valle 56) tienen `domain_metadata=NULL` en la DB** porque el harvester nunca pobló nada más. Resultado: cobertura 0% en `cobertura_geografica`, `jurisdiccion_nivel`, `update_frequency`, `sector` para todos los federados CKAN.

Este reporte mapea **TODOS los campos disponibles** en cada portal antes de decidir qué curar y cómo.

## Bogotá (`datosabiertos.bogota.gov.co`) — 42 keys top-level

Campos relevantes (verificados en 5/5 samples):

| Campo top-level | Tipo | Ejemplo | Mapeo posible |
|---|---|---|---|
| `license_id` | string canónico | `CC-BY-4.0` | → `license_id` directo |
| `license_title` | string | `Creative Commons Attribution 4.0` | → `license` (ya extraído) |
| `license_url` | URL | `http://creativecommons.org/licenses/by/4.0/` | → `domain_metadata['license_url']` |
| `spatial` | GeoJSON | `{"type":"Polygon","coordinates":[...]}` (bounding box Bogotá D.C.) | → derivar `cobertura_geografica='Distrital'` |
| `update_frequencies` | array | `[...]` (no presente en samples; existe el campo) | → `update_frequency` si poblado |
| `dis_scope` | string | `Conjunto de datos` | meta, no aporta |
| `idnt_spatial_resolution` | string | (vacío en samples) | → `cobertura_geografica` si poblado |
| `topic_main_categories` | array | — | → `category` complemento |
| `groups` | array de dicts | `[{'name':'salud-proteccion-social'}]` | → `sector` heurístico |
| `tags` | array | `['Salud Bogotá', 'Salud y Protección Social']` | → `dataset_tags` |
| `responsable_types` | string | `Autor` | → `domain_metadata` |
| `presentation_types` | string | `Tabla Digital` | → `domain_metadata` |
| `ideca_languages` | string | `Espanol` | → `domain_metadata['idioma']` |
| `qua_summary` | string libre | `El producto cumple con los datos de calidad...` | → `domain_metadata['calidad_resumen']` |
| `ref_systems` | string | `EPSG 102771 MAGNA-SIRGAS...` | → `domain_metadata['sistema_referencia']` |
| `inf_citation_date`, `date_types` | strings | — | meta |
| `dis_organization` | string | — | secundario |

**Default deducible por portal:**
- `cobertura_geografica = 'Distrital'`
- `jurisdiccion_nivel = 'distrito_capital'`
- `jurisdiccion_geo_codes = ["11001"]`

## Cali (`datos.cali.gov.co`) — 30 keys top-level + **10 keys `extras` estandarizados**

Estructura más simple en top-level, pero todos los packages tienen exactamente las mismas 10 keys en `extras`:

| Extras key | Ejemplo | Mapeo |
|---|---|---|
| `Cobertura Geográfica` | `Municipal/Distrital` | → `cobertura_geografica` |
| `Departamento` | `Valle del Cauca` | → `domain_metadata['departamento']` |
| `Frecuencia de Actualización` | `Anual` / `Mensual` | → `update_frequency` |
| `Idioma` | `Español` | → `domain_metadata['idioma']` |
| `Municipio` | `Cali` | → `domain_metadata['municipio']` |
| `Nombre de la Entidad` | `Alcaldía Municipal de Santiago de Cali` | → mejora `entity_raw` |
| `Orden` | `Territorial` / `Nacional` | → `jurisdiccion_nivel` heurístico |
| `Sector` | `Educación` / `Gestión Pública/Administrativa` | → `sector` |
| `URL Documentación` | (URL o vacío) | → `domain_metadata` |
| `URL Normativa` | (URL o vacío) | → `domain_metadata` |

**Top-level adicional:**
- `license_id`: `cc-by-sa` / `cc-by` (canónico)
- `license_title`: descriptivo (ya extraído)
- `organization.title`: ya extraído
- `tags`: ya disponible

**Default deducible por portal:**
- `cobertura_geografica` desde extras directo (Municipal/Distrital)
- `jurisdiccion_nivel = 'municipal'` (Orden='Territorial' + Municipio='Cali')
- `jurisdiccion_geo_codes = ["76001"]`
- `sector` desde extras
- `update_frequency` desde extras

## Valle (`datosabiertos.valledelcauca.gov.co`) — 35 keys top-level

Esquema custom — campos directos en top-level (no en extras):

| Campo top-level | Ejemplo | Mapeo |
|---|---|---|
| `license_id` | `cc-by-sa` | → `license_id` |
| `frecuencia_actualizacion` | (no presente en samples; existe el campo) | → `update_frequency` si poblado |
| `category` | (no presente en samples; existe el campo) | → `category` |
| `ciudad` | (no presente en samples; existe) | → `domain_metadata['municipio']` |
| `departamento` | (no presente en samples; existe) | → `jurisdiccion_geo_codes` |
| `consolidado` | (no presente; existe) | — |
| `groups` | `['paz-territorial-y-reconciliacion']` | → `sector` heurístico |
| `tags` | `['gobernacion', 'valle del cauca']` | → `dataset_tags` |

**Default deducible por portal:**
- `cobertura_geografica = 'Departamental'`
- `jurisdiccion_nivel = 'departamental'`
- `jurisdiccion_geo_codes = ["76"]`

## Plan de curación recomendado

### Fase 1 — Default mínimo por source_portal (SQL UPDATE, 5 min)

Garantiza cobertura ≥99% en `cobertura_geografica`/`jurisdiccion_nivel`/`jurisdiccion_geo_codes` para los 4.625 datasets CKAN ya ingestados. No requiere re-cosechar.

| source_portal | cobertura_geografica | jurisdiccion_nivel | jurisdiccion_geo_codes |
|---|---|---|---|
| `datosabiertos.bogota.gov.co` | `Distrital` | `distrito_capital` | `["11001"]` |
| `datos.cali.gov.co` | `Municipal` | `municipal` | `["76001"]` |
| `datosabiertos.valledelcauca.gov.co` | `Departamental` | `departamental` | `["76"]` |

### Fase 2 — Harvester por-portal con extractor especializado (~30-45 min implementación)

Refactor `harvest_ckan.py` con función `_build_row_<portal>()` por portal que extrae:
- **Bogotá:** `license_id`, `spatial`, `tags`, `qua_summary`, `ideca_languages`, `groups[0]` como `sector`.
- **Cali:** `license_id`, **TODOS los extras** (10 keys consistentes → mapeo directo a `cobertura_geografica`, `update_frequency`, `sector`, `entity_raw` mejorado).
- **Valle:** `license_id`, `frecuencia_actualizacion`, `category`, `groups[0]` como `sector`.

Dump completo de extras/custom fields a `domain_metadata` JSONB para preservar todo lo demás.

### Fase 3 — Re-correr harvest_ckan.py + re-medir cobertura

```
make harvest-bogota harvest-cali harvest-valle
psql -c "SELECT source_portal, COUNT(*),
  ROUND(100.0*COUNT(cobertura_geografica)/COUNT(*),1) AS pct_cob,
  ROUND(100.0*COUNT(update_frequency)/COUNT(*),1) AS pct_freq,
  ROUND(100.0*COUNT(sector)/COUNT(*),1) AS pct_sect,
  ROUND(100.0*COUNT(license_id)/COUNT(*),1) AS pct_lic
FROM datasets WHERE source_type='federated' GROUP BY 1"
```

Esperado post-curación: cobertura/jurisdicción ≥99% en CKAN; update_frequency 80-100% en Cali (extras siempre), variable en Bogotá/Valle.

## Lecciones para el plan principal (Hito R)

1. **El audit Q.7 firmó nativos contra Socrata** pero el CKAN harvest se ejecutó después y nunca fue auditado — gap de proceso.
2. **NULL en columnas curables ≠ NULL legítimo.** `cobertura_geografica=NULL` en CKAN es bug del ETL, no característica de la fuente. Distinguir esto es central para la filosofía de honestidad.
3. **La matriz keep/drop debe esperar a la curación.** Algunas columnas pueden ir de "0% federados → drop" a "100% federados → keep sin marca" con 1 hora de trabajo.
