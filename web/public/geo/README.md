# GeoJSON DIVIPOLA — Colombia

Carpeta destino de los archivos GeoJSON oficiales para mapas coropléticos (PLAN_DASHBOARD §6).

| Archivo | Nivel | Origen sugerido | Tamaño |
|---|---|---|---|
| `co_dptos.geojson` | 33 departamentos | DANE / IGAC `Marco geoestadístico nacional` | ~50 KB minificado |
| `co_mpios.geojson` | 1122 municipios | DANE / IGAC `Marco geoestadístico nacional` | ~2 MB (simplificado al 10 %) |

## Descarga sugerida

Una opción libre y verificable es el repositorio público de [john-guerra/colombia.geo.json](https://github.com/john-guerra/colombia.geo.json) (Creative Commons), o el shapefile oficial DANE convertido a GeoJSON con `mapshaper`:

```bash
# Departamentos (uso oficial DANE):
ogr2ogr -f GeoJSON co_dptos.geojson MGN_DPTO_POLITICO.shp -t_srs EPSG:4326 \
        -simplify 0.001 -lco RFC7946=YES

# Municipios (simplificado 10 %):
mapshaper MGN_MPIO_POLITICO.shp -simplify 10% keep-shapes \
          -o co_mpios.geojson format=geojson
```

Reglas:
- Conservar propiedad `cod_dpto` o `cod_mpio` (5 dígitos) en cada feature — es la llave que el spec usa para hacer match.
- Servir con `Cache-Control: max-age=31536000, immutable` en Nginx (ver `nginx/default.conf`).
- El de mpios se carga **lazy** desde el frontend solo cuando un Dashboard spec lo requiere.

## Estado actual

`ChoroplethMapBlock.tsx` ya soporta el render coroplético via MapLibre. Mientras los archivos no estén presentes, el componente cae a un mapa de marcadores en las capitales de los códigos DIVIPOLA referenciados (versión degradada honesta — no inventa polígonos).
