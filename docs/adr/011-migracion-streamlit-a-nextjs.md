# ADR-011: Migración de Streamlit a Next.js para Beta-2

**Estado:** Aceptada
**Fecha:** 2026-05-20
**Supersedes:** [ADR-002](./002-streamlit-vs-react.md) (Streamlit en vez de React)

## Decisión

Migrar la interfaz ciudadana de **Streamlit** (`app/`) a **Next.js 15 + React 19 + TypeScript** en una carpeta paralela `web/`. Streamlit se mantiene durante 30 días bajo perfil Docker `legacy` para mitigar riesgo de regresión funcional, luego se retira.

## Razón

ADR-002 eligió Streamlit por velocidad y stack 100% Python. Eso fue correcto para Beta-1. Tres restricciones aparecen ahora que invalidan esa decisión para Beta-2:

- **Rebranding civic editorial** requiere control total sobre header, layout, chat bubbles y tipografía. Streamlit fuerza `st.chat_message` (bubbles izquierda/derecha tipo WhatsApp) que es exactamente la estética que la marca rechaza. CSS injection vía `st.markdown(unsafe_allow_html=True)` no escala a 5 vistas con 3 modos color.
- **Tres modos de color reales** (claro, oscuro, alto contraste con AAA) exigen un sistema de tokens CSS bajo `[data-theme]`. Streamlit `config.toml` solo soporta un tema activo a la vez; cambiar de tema requiere reload y no soporta el modo alto contraste WCAG AAA con acento `#0033A0`.
- **WCAG 2.1 AA estricto** con navegación completa por teclado, focus-visible obligatorio y soporte de lectores de pantalla en los 3 modos — `docs/accessibility.md` ya documenta que Streamlit no cubre lectores como JAWS/NVDA. Beta-2 lo necesita cubierto.

Adicionalmente, el flujo principal cambia de chat conversacional a buscador con chips (`HeroSearch + ChipGroup × 4 ejes`), lo que ya no encaja con el modelo mental de Streamlit.

## Trade-off

- **Costo de skills.** El equipo es backend Python. Next.js implica curva de aprendizaje. Mitigación: el motor IA (`ai_engine/`, `mcp_server/`) no se toca; solo se construye una API HTTP nueva en `api/` (FastAPI, también Python) que Next.js consume. La superficie de TS nueva queda acotada a UI.
- **Build step y deploy más complejo.** Antes era un proceso Python; ahora hay un servicio Node 22 alpine adicional en `docker-compose.yml`. Mitigación: multistage build con artefacto estático; Nginx ya está en el stack.
- **Riesgo de regresión funcional ante sustentación MinTIC.** Mitigación: coexistencia 30 días con perfil `legacy`. Si Next.js falla en demo, se vuelve a `/legacy`. Tests funcionales E2E garantizan que las mismas consultas devuelven las mismas cifras en ambas UIs.
- **`AgentClient` de Streamlit queda como referencia, no como API.** Decisión separada en [ADR-013](./013-fastapi-sse-vs-mcp-http.md).

## Plan de coexistencia

| Periodo | `/` (Nginx) | `/legacy` (Nginx) | `docker-compose` |
|---|---|---|---|
| Sprint A-F (build) | Streamlit | (no existe) | servicio `streamlit` activo |
| Sprint G (cutover) | Next.js | Streamlit | ambos servicios activos |
| Día +30 desde cutover | Next.js | 404 | `streamlit` movido a perfil `legacy` |
| Día +60 | Next.js | — | `app/`, `Dockerfile.streamlit`, `requirements.streamlit.txt` eliminados del repo |

## Referencias

- [`docs/BRAND.md`](../BRAND.md) — sistema visual que motiva la migración
- [ADR-012](./012-civic-editorial-design-system.md) — dirección estética
- [ADR-013](./013-fastapi-sse-vs-mcp-http.md) — contrato API entre Next.js y motor Python
- [`docs/accessibility.md`](../accessibility.md) — limitaciones de Streamlit en lectores de pantalla
- [`app/`](../../app/) — código Streamlit a deprecar
- [`web/`](../../web/) — nuevo frontend (a crear en Sprint B)
