# ADR-002: Streamlit en vez de React

**Estado:** Aceptada
**Fecha:** Sprint 1 (planificación), implementada Sprint 4

## Decisión

Construir la interfaz ciudadana en **Streamlit**, no en React/Next.js u otro framework JS.

## Razón

- **100% Python.** El equipo es backend Python; no tenemos skill operativo de frontend JS.
- **Chat nativo.** `st.chat_message` + `st.chat_input` cubren el caso principal sin librerías custom.
- **Multipage nativo.** `st.navigation` con tres páginas (chat / explorer / about) sin router externo.
- **Despliegue simple.** Un único proceso, sin build step, sin bundling.

## Trade-off

- **Customización visual limitada.** Streamlit fuerza un estilo; con tema dark accesible es suficiente para el MVP del concurso.
- **Re-runs por interacción.** El modelo de re-ejecución de Streamlit puede sorprender; mitigado con `st.cache_resource` para el `AgentClient`.
- **Migración futura.** Si se requiere UX más sofisticada, el `AgentClient` queda como interfaz estable que un frontend React podría consumir sin tocar el motor.

## Referencias

- `app/main.py`, `app/pages/`
- [`docs/crisp_mlq/06_deployment.md`](../crisp_mlq/06_deployment.md)
