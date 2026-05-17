# ADR-008: Sprint 4 sin Power BI — scope solo Streamlit + accesibilidad

**Estado:** Aceptada
**Fecha:** 2026-05-16

## Decisión

El Sprint 4 entrega únicamente la **interfaz Streamlit** ciudadana + el **modo accesible** (Web Speech API). Power BI **sale del scope del entregable** y queda como integración externa opcional que cualquier entidad podría conectar a su propia base si activa logging persistente.

## Razón

- **Foco en el criterio ciudadano.** El reto MinTIC pide un asistente virtual de acceso ciudadano; Power BI es dashboard interno del equipo operador, no toca al ciudadano.
- **Sprint 4 ya tenía 7 fases técnicas** (tests, setup, páginas, componentes, accesibilidad, Docker, PR). Agregar Power BI hubiera presionado el cronograma sin agregar valor al criterio principal.
- **PostgreSQL no se instrumentó como logging activo en el MVP.** Sin tabla con datos, un dashboard Power BI estaría vacío. Mejor diferir hasta tener telemetría real.
- **Integraciones externas no son la propuesta core.** Si una entidad quiere Power BI / Metabase / Superset, puede conectar al schema `db/init.sql` cuando esté activado; no tiene que estar en el repo del agente.

## Trade-off

- **Supera [ADR-003](./003-powerbi-analitica.md)**, que sí ponía Power BI en el alcance. ADR-003 se marca como "Superada" pero se conserva por trazabilidad.
- **No hay dashboard de uso interno listo para el operador.** Asumido: el operador puede armarlo después con cualquier herramienta cuando se active el logging.

## Consecuencias en docs

- `README.md` y `docs/architecture.md` §3 reescritos como "Capa 3: Streamlit" (singular).
- `docs/crisp_mlq/06_deployment.md` declara Power BI como **fuera de scope** explícitamente.
- `docker-compose.yml` deja `postgres` y `nginx` comentados (referencia para activación futura).

## Referencias

- [ADR-003](./003-powerbi-analitica.md) (superada)
- `MAIN.md §10.5` (estado Sprint 4)
- PR #11 (merge a develop tras corrección de base por fast-forward)
