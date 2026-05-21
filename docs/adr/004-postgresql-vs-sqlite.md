# ADR-004: PostgreSQL en vez de SQLite

**Estado:** Aceptada (schema definido, no activado en MVP)
**Fecha:** Sprint 1 (planificación)

## Decisión

Si llegamos a persistir logs y métricas, hacerlo en **PostgreSQL 16**, no en SQLite.

## Razón

- **Conectores BI nativos.** PostgreSQL es ciudadano de primera clase para Metabase, Superset, Power BI, etc.
- **Concurrencia real.** Múltiples procesos (`mcp-server` + `streamlit` + scripts) escribiendo simultáneamente.
- **Operación estándar.** Cualquier DBA del Estado sabe operar PostgreSQL.

## Trade-off

- **Setup más complejo.** Mitigado con Docker (`docker-compose.yml` deja el servicio comentado, listo para activar).
- **No activado en MVP.** Sprint 4 cerró sin instrumentar logging persistente — fuera de scope. El schema vive en `db/init.sql` como referencia.

## Referencias

- `db/init.sql`
- `docker-compose.yml` (servicio `postgres` comentado)
