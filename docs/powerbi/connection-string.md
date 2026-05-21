# Conexión Power BI Desktop → PostgreSQL DatosVivos

Documentación para ANI sobre cómo conectar Power BI Desktop al PostgreSQL productivo de DatosVivos.

## Pre-requisitos

- Power BI Desktop instalado (Windows o macOS via Parallels).
- Acceso a la VM productiva o IP pública de Postgres con whitelist del IP del analista.
- Credenciales `dv` / password (las maneja DevOps de ANI, no se publican).
- Driver PostgreSQL para Power BI: viene incluido en Power BI Desktop ≥ 2.96.

## Cadena de conexión

**Servidor:** `<IP_VM_PROD>:5432` (o `db.datosvivos.co:5432` cuando exista DNS).
**Base de datos:** `datosvivos`
**Modo:** DirectQuery (recomendado) o Import (refresh manual).
**Autenticación:** Database (usuario+password). NO usar Windows authentication.

## Paso a paso

1. Power BI Desktop → `Inicio → Obtener datos → Más…`
2. Buscar `PostgreSQL database` → Conectar.
3. Servidor: `<IP_VM_PROD>:5432`, Base de datos: `datosvivos`.
4. Modo de conectividad: **DirectQuery**.
5. Usuario: `dv`. Password: pedir a DevOps de ANI.
6. En el navegador, seleccionar SOLO las **views** (no las tablas raw):
   - `v_dataset_status` — renombrar el alias a `Datasets` (Power BI lo usa como tabla principal del filtro de URL).
   - `v_dataset_usage` — renombrar a `Usage`.
   - `v_entity_summary` — renombrar a `EntitySummary`.
   - `v_top_datasets` — renombrar a `TopDatasets`.
   - `v_queries_daily` — renombrar a `QueriesDaily`.
   - `queries` — opcional, para drill-down a consultas individuales en Página 2.
7. Cargar.

## Relaciones del modelo

Power BI suele auto-detectar las relaciones por nombre de columna. Verificar:

- `Datasets[dataset_id]` ↔ `Usage[dataset_id]` (1:1)
- `Datasets[entity_abbrev]` ↔ `EntitySummary[entity_abbrev]` (1:1)
- `Datasets[entity_abbrev]` ↔ `TopDatasets[entity_abbrev]` (1:N permitida pero filtra)
- `queries[id]` ↔ (sin relación directa, sólo via subqueries DAX)

Para drill-through Página 1 → Página 2 sobre `dataset_id`, añadir:
- `Datasets[dataset_id]` ↔ `Usage[dataset_id]` con dirección **Both** (filtro cruzado en ambas direcciones).

## Tabla calculada `dim_date`

Ver `dashboard-spec.md → Calendario`. Crear con DAX `CALENDAR(DATE(2024,1,1), TODAY())`. Relacionar con `queries[timestamp_iso]` casteada a fecha.

## Seguridad de la cadena

- El password NO debe quedar en el archivo `.pbix`. Usar **OAuth2** o **Personal Gateway** cuando se publique a Power BI Service.
- Para publish-to-web, Power BI Service necesita credenciales almacenadas server-side (Power BI las cifra). No exponen el password al cliente final.

## Verificación

```sql
-- Desde psql, validar que las views devuelvan filas:
SELECT entity_name, n_datasets, n_queries_30d FROM v_entity_summary LIMIT 5;
SELECT status, COUNT(*) FROM v_dataset_status GROUP BY status;
SELECT * FROM v_top_datasets;
```

Si las queries devuelven datos, Power BI los podrá leer.

## Troubleshooting

- **"SSL connection required"**: añadir `?sslmode=require` en la cadena o configurar SSL del lado servidor.
- **"timezone unknown"**: Power BI Desktop puede no respetar el timezone del server. Asegurarse de que `TIMEZONE=UTC` en `postgresql.conf` y de que las medidas DAX usen `TODAY()` (local) coherentemente.
- **"too many rows"**: en DirectQuery, `queries` puede exceder el límite. Usar `v_queries_daily` agregado en lugar de `queries` raw para visuales temporales.
