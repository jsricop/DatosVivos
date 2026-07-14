# GeoJSON DIVIPOLA — Colombia

GeoJSON oficiales para los mapas coropléticos del sitio. Render: **SVG puro con
`d3-geo`** (geoMercator + geoPath), sin tiles ni servicios externos — cumple la
promesa "Sin trackers" del footer.

| Archivo | Nivel | Origen | Tamaño |
|---|---|---|---|
| `co_dptos.geojson` | 33 departamentos | DANE / IGAC `Marco geoestadístico nacional` | ~1.5 MB |
| `co_mpios.geojson` | 1122 municipios | DANE / IGAC (simplificado al 10 % con mapshaper) | ~790 KB |

## Consumidores

- `web/src/components/panorama/PanoramaMap.tsx` — coropleta de departamentos
  en la home panorama (ADR-023). Carga `co_dptos.geojson` lazy client-side.
- `web/src/components/charts/ChoroplethMapBlock.tsx` — mapas en dashboards
  generados por el flujo de búsqueda. Soporta `dpto` y `mpio`.

Ambos hacen match por las propiedades `DPTO` (2 dígitos) / `MPIO` (5 dígitos)
y usan buckets por cuantiles con opacidad creciente sobre `--accent`.

## Regeneración (si cambia la fuente DANE)

```bash
# Departamentos:
ogr2ogr -f GeoJSON co_dptos.geojson MGN_DPTO_POLITICO.shp -t_srs EPSG:4326 \
        -simplify 0.001 -lco RFC7946=YES

# Municipios (simplificado 10 %):
mapshaper MGN_MPIO_POLITICO.shp -simplify 10% keep-shapes \
          -o co_mpios.geojson format=geojson
```

Reglas:
- Conservar `DPTO`/`MPIO`/`NOMBRE_DPT`/`NOMBRE_MPI` en cada feature — llaves
  del match y de los tooltips.
- El geojson se carga **lazy** desde el frontend solo cuando hay un mapa en
  pantalla.
