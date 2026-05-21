# ADR-003: Power BI para analítica, no para interfaz principal

**Estado:** Superada por [ADR-008](./008-scope-sin-powerbi.md)
**Fecha:** Sprint 1 (planificación)

## Decisión original

Usar **Power BI** únicamente como dashboard de métricas de uso del agente (queries por día, datasets más consultados, latencia), conectado a las tablas PostgreSQL del schema `db/init.sql`. **No** como interfaz ciudadana.

## Razón

- Power BI **no puede enviar consultas dinámicas a un MCP Server**: su modelo es de pull periódico desde una fuente de datos. Inviable como UI conversacional.
- Sí puede visualizar tablas relacionales — apto para analítica de uso interna del equipo operador.

## Trade-off original

- Dos interfaces conviven (Streamlit ciudadana + Power BI interna). Justificado porque cumplen funciones distintas.

## Por qué fue superada

Durante Sprint 4 (2026-05-16) decidimos quitar Power BI del scope del entregable: ver [ADR-008](./008-scope-sin-powerbi.md). El schema PostgreSQL queda en el repo como referencia para activarlo en un sprint futuro si se requiere logging persistente; Power BI (o Metabase, Superset, etc.) puede conectarse a él como integración externa opcional.

## Referencias

- [ADR-008: Sprint 4 sin Power BI](./008-scope-sin-powerbi.md)
- `db/init.sql` (schema referencia)
