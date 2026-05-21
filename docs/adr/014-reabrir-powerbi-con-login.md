# ADR-014: Reabrir Power BI con login institucional embebido

**Estado:** Aceptada
**Fecha:** 2026-05-21
**Supersedes:** [ADR-008](./008-scope-sin-powerbi.md) (Sprint 4 sin Power BI)

## Decisión

Reintroducir Power BI al alcance productivo de DatosVivos como **módulo BI ejecutivo embebido bajo login** dentro de `datosvivos.co/tablero`. El dashboard se publica desde Power BI Service con la cuenta gratuita (publish-to-web) y se incrusta vía iframe filtrado por entidad.

- **BD productiva:** PostgreSQL se activa y queda como fuente de datos del tablero (telemetría + catálogo enriquecido desde Socrata Metadata API).
- **Auth:** magic-link por email institucional (NextAuth v5 + nodemailer), dominio limitado a `.gov.co` (configurable).
- **Scoping por entidad:** filtro vía URL del iframe (`?filter=Datasets/entity_abbrev eq '…'`). No es Row-Level Security real — limitación documentada.
- **Estado de datasets:** función SQL `compute_status` aplica umbrales según `updateFrequency` de Socrata cuando exista, con fallback fijo 30/180 días.

## Razón

ADR-008 (2026-05-16) sacó Power BI del Sprint 4 priorizando Streamlit + accesibilidad para llegar al MVP del concurso. Sigue vigente la lógica de aquella decisión para Beta-1: Power BI no debía bloquear la entrega ciudadana.

La situación cambia ahora:

- **Demanda explícita de la dirección del proyecto:** se quiere mostrar a cada entidad publicadora un tablero ejecutivo con sus datasets, consultas, último acceso y estado de actualización. Es un entregable institucional que complementa al agente ciudadano.
- **Beta-2 con Civic Editorial estable:** el frontend Next.js (`web/`) ya cuenta con tokens, layout, auth-ready boilerplate, etc. Agregar `/login` + `/tablero` ya no compite con el cierre del MVP.
- **PostgreSQL preparado en código pero apagado:** `db/init.sql` define el schema desde Sprint 1; `docker-compose.yml` lo tiene comentado. Activarlo es un cambio quirúrgico.
- **Costo total de oportunidad bajo:** publish-to-web es gratuito; nodemailer + NextAuth funcionan con SMTP institucional sin costo de licencia.

## Trade-off

- **Sin RLS real:** publish-to-web no soporta Row-Level Security. El filtro por entidad vía URL es manipulable por un usuario técnico. Aceptable porque los datos son agregados públicos del catálogo `datos.gov.co` (no PII). Si MinTIC o ANI lo exigen, escalar a Power BI Embedded (~735 USD/mes A1).
- **`.pbit` se entrega como especificación, no como binario:** no puedo generar un `.pbix`/`.pbit` desde el entorno Linux/Docker. ANI lo arma en Power BI Desktop siguiendo `docs/powerbi/dashboard-spec.md`. Es 30-60 min de trabajo para alguien con experiencia.
- **Dual-write CSV + Postgres durante 30 días:** la telemetría sigue persistiendo en CSV como fuente de verdad de respaldo. Si Postgres cae, el agente sigue funcionando. Después de 30 días estables se puede ponderar el CSV como fallback solo.
- **5 000 llamadas a Metadata API en cada bulk-refresh:** el ETL diario respeta rate-limit con `asyncio.Semaphore(5)` + 200 ms entre lotes. ~17 min nocturnos. Aceptable.
- **`auth_events` puede crecer ilimitadamente:** documentar política de retención (90 días sugerido) cuando alcance ~100k filas. Sin acción hasta entonces.

## Referencias

- [ADR-008](./008-scope-sin-powerbi.md) — decisión superada
- [ADR-013](./013-fastapi-sse-vs-mcp-http.md) — API HTTP de la SPA
- [`db/init.sql`](../../db/init.sql) — schema productivo extendido
- [`scripts/etl_refresh_catalog.py`](../../scripts/etl_refresh_catalog.py) — bulk-refresh diario
- [`scripts/migrate_telemetry_csv_to_postgres.py`](../../scripts/migrate_telemetry_csv_to_postgres.py) — one-shot
- [`ai_engine/telemetry.py`](../../ai_engine/telemetry.py) — dual-write CSV + Postgres
- [`web/src/lib/auth.ts`](../../web/src/lib/auth.ts) — NextAuth v5 magic-link
- [`web/src/app/tablero/page.tsx`](../../web/src/app/tablero/page.tsx) — embed con filtro por entidad
- [`docs/powerbi/dashboard-spec.md`](../powerbi/dashboard-spec.md) — especificación visual
- [`docs/powerbi/publish-runbook.md`](../powerbi/publish-runbook.md) — paso a paso para ANI
