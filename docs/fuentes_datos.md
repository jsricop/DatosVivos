# Fuentes de datos

> Cifras al corte del **2026-07-10**; el catálogo se actualiza automáticamente a
> diario (ETL nocturno + harvesting semanal), por lo que los valores varían.
> Verificable en vivo: `https://datosvivos.co/api/v1/stats/panorama`.

## Los 6 portales integrados

DatosVivos consolida en un solo catálogo consultable portales que publican cada uno por
su lado y que, de otra forma, habría que revisar sitio por sitio. La atribución es por
**portal de origen** (donde la entidad publica originalmente), no por la ruta de cosecha.

| Portal | Datasets | Mecanismo de ingesta | Frecuencia |
|---|---:|---|---|
| [datos.gov.co](https://www.datos.gov.co) (nacional, MinTIC) | 12.101 | Socrata Discovery API + SODA + Metadata API | Diaria |
| [IGAC — Colombia en Mapas](https://www.colombiaenmapas.igac.gov.co) | 6.622 | Federación vía datos.gov.co (identificación por entidad publicadora) | Diaria |
| [Datos Abiertos Bogotá](https://datosabiertos.bogota.gov.co) | 4.304 | CKAN API (harvest directo) + copias federadas | Semanal |
| [Datos Abiertos Cali](https://datos.cali.gov.co) | 1.236 | CKAN API (harvest directo) + copias federadas | Semanal |
| [MEDATA — Medellín](https://www.medata.gov.co) | 823 | DCAT JSON-LD (harvest directo) + copias federadas | Semanal |
| [Datos Abiertos Valle del Cauca](https://datosabiertos.valledelcauca.gov.co) | 106 | CKAN API (harvest directo) + copias federadas | Semanal |
| **Total** | **25.192** | | |

- **1.423 entidades publicadoras** distintas (nacionales y territoriales).
- Composición: **22.196 datos temáticos** (salud, contratación, educación, movilidad…)
  y **2.996 reportes administrativos** de la Ley de Transparencia (Ley 1712 de 2014).
- Acceso: 8.458 de consulta directa vía API · 6.472 con archivo descargable ·
  10.262 solo metadatos (mapas, geoservicios, documentos).

## Cumplimiento del requisito "mínimo un dataset de datos.gov.co"

El requisito se cumple con holgura: **12.101 datasets provienen directamente de
datos.gov.co** (8.458 nativos Socrata + federados), y además la solución usa datasets
específicos del portal nacional como referencia estructural:

- **DIVIPOLA — Codificación de municipios** (`gdxc-w37w`, DANE en datos.gov.co):
  catálogo canónico de departamentos y municipios usado para la inferencia territorial
  de todo el catálogo y para el mapa coroplético.
- Cualquier dataset tabular nativo es consultable en vivo desde el buscador
  (p. ej. matrícula educativa, contratación SECOP, vacunación) — el motor ejecuta la
  consulta sobre la API SODA del dataset citado.

## Datasets externos (fuera de datos.gov.co)

Los portales territoriales CKAN/DCAT (Bogotá, Cali, MEDATA, Valle) y el geoportal del
IGAC. Sus catálogos se armonizan al mismo esquema (ver
[diccionario de datos](diccionario_datos.md)): título, descripción, entidad, sector,
cobertura geográfica, frecuencia declarada, licencia, URL de datos y fechas.

## Geografía de referencia

- GeoJSON oficial DIVIPOLA (DANE/IGAC, Marco Geoestadístico Nacional): 33 departamentos
  y 1.122 municipios, servidos localmente (sin dependencias de mapas externos).

## Licencias y uso

Todos los datos integrados son **públicos y abiertos**, publicados por las entidades
bajo las licencias declaradas en cada portal (mayoritariamente CC-BY / dominio
público). DatosVivos no accede, procesa ni expone información interna de ninguna
entidad: opera exclusivamente sobre lo ya publicado. La telemetría propia es anónima.
