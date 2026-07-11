# Guía de validación — cómo replicar y auditar DatosVivos

Esta guía permite al jurado (o a cualquier tercero) **verificar la solución en tres
niveles**: probarla en vivo, auditar sus cifras contra endpoints públicos, y
reproducir el sistema completo desde el código.

## Nivel 1 — Probar la solución en vivo (0 instalación)

| Qué | Dónde |
|---|---|
| Panorama nacional (cifras en vivo, actualización diaria) | https://datosvivos.co |
| Tablero del decisor (Power BI, filtros por sector/entidad/territorio) | https://datosvivos.co/tablero |
| Buscador en lenguaje natural (NL2SQL verificado) | https://datosvivos.co/buscar |
| Accesibilidad (voz, contraste, escala — Ley 1618) | https://datosvivos.co/accesibilidad |

Sugerencias de prueba del buscador: *"¿Cuántos colegios públicos hay en Boyacá?"*,
*"Contratos firmados por la ANI en 2024"*. Cada respuesta cita el dataset fuente con
enlace; el botón "Ver consulta SoQL" muestra la consulta generada (transparencia).

## Nivel 2 — Auditar las cifras (API pública)

```bash
# Panorama completo (mismo JSON que alimenta la home):
curl https://datosvivos.co/api/v1/stats/panorama

# Inventario bruto:
curl https://datosvivos.co/api/v1/stats/catalog

# Exportes completos del catálogo curado (los mismos del tablero Power BI):
curl -O https://datosvivos.co/api/v1/dashboard/datasets_decisor.csv
curl -O https://datosvivos.co/api/v1/dashboard/entities_decisor.csv
```

Toda cifra mostrada en la web sale de estos endpoints — se puede contrastar 1:1.
El significado de cada campo está en el [diccionario de datos](diccionario_datos.md).

## Nivel 3 — Reproducir desde el código

Requisitos: Docker + Docker Compose, Git. (El motor de lenguaje es conectable:
`LLM_BACKEND=anthropic` con una API key de Claude — como corre producción — o
`LLM_BACKEND=ollama` con un modelo local: ~8 GB de
disco para el modelo.)

```bash
git clone https://github.com/jsricop/DatosVivos && cd DatosVivos
cp .env.example .env                     # revisar variables; los ejemplos funcionan local
docker compose up -d postgres api web    # nginx/streamlit son de producción/legacy
```

- Web local: http://localhost:3001 · API: http://localhost:8000/api/v1/stats/catalog
- Poblar el catálogo (ingesta real contra datos.gov.co):
  `docker exec datosvivos-api-1 python -m scripts.etl_refresh_catalog --incremental`
- Harvesting territorial: `python -m scripts.harvest_ckan --portal bogota` (y `cali`,
  `valle`), `python -m scripts.harvest_dcat --portal medellin`.

### Pruebas automatizadas (35 archivos)

```bash
docker exec datosvivos-api-1 python -m pytest tests/ -q
```

Cobertura: verificador SoQL (3 capas), validador anti-alucinación de números,
reparación de consultas, geo/DIVIPOLA, clasificadores, harvesting, servidor MCP
(stdio y SSE), rutas de la API (chips, stats, panorama).

### Evaluación con golden sets

```bash
docker exec datosvivos-api-1 python scripts/run_eval.py \
  --golden eval/golden_queries.yaml --out eval/reports/
```

Casos esperados versionados en [`eval/golden_queries.yaml`](../eval/golden_queries.yaml)
y [`eval/golden_chips.yaml`](../eval/golden_chips.yaml); reportes históricos de
corridas y auditorías de calidad en [`eval/reports/`](../eval/reports/).

### MCP server (interoperabilidad)

Las herramientas del motor (`search_datasets`, `get_metadata`, `query_data`,
`cross_datasets`) se exponen por el estándar MCP — conectables desde cualquier cliente
compatible (Claude Desktop, Cursor, agentes propios). Ver `mcp_server/`.

## Trazabilidad de decisiones

Las decisiones de arquitectura están documentadas como ADRs en [`docs/adr/`](adr/):
motor híbrido IA+determinista (017), transparencia SoQL (018), DuckDB para federados
(019), harvesting CKAN (020), sistema de diseño gov.co (021), **motor NL2SQL
generativo verificado (022)** y home panorama para decisores (023).

> Nota de alcance: el repositorio publica todo lo necesario para replicar y auditar.
> Quedan fuera únicamente credenciales y topología operativa de la infraestructura
> productiva (buena práctica de seguridad; no afectan la reproducibilidad local).
