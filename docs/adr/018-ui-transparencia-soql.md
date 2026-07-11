# ADR-018: UI transparencia — SoQL visible para el ciudadano

**Estado:** Aceptada
**Fecha:** 2026-05-29
**Contexto:** Hito 1 / Fase C cerrado. Cada chip de TIPO produce una consulta SoQL/DuckDB determinista que retorna una cifra real. La pregunta de diseño fue: ¿debemos mostrar la query al usuario?

## Decisión

**El frontend expone la consulta SoQL/DuckDB exacta detrás de un toggle "Ver consulta", visible al lado de cada resultado.** Default colapsado (UX limpia para ciudadanos), un clic la despliega para auditores, periodistas, técnicos y gerencia.

Implementación:
- `ChipsResultView.tsx`: `[Ver/Ocultar] consulta SoQL` button + `<pre>` con la query cuando se expande.
- El response del backend (`ChipsExecuteResponse.soql`) viaja siempre; el cliente decide si renderizar.

## Razones

1. **Trust gradient.** ADR-017 separa "IA razona" del "motor verifica". La verificación tiene que ser **auditable** por un humano, no opaca. Si la cifra es trazable hasta SQL → fuente, hay confianza.
2. **Auditoría regulatoria.** Periodistas, entes de control y la academia van a leer el código si dudan de la cifra. Si está escondida, repiten el cálculo manual y nos llaman a explicar.
3. **Educación cívica.** Mostrar la query da contexto: "esto cuenta filas con `WHERE depto='Antioquia'`". El ciudadano avanzado entiende qué leyó.
4. **Costo cero.** El SoQL ya viaja en la respuesta para fines de logging. Mostrarlo solo es UI.

## Alternativas consideradas

- **Mostrar siempre, sin toggle:** rechazado — ruido visual para 90% de los ciudadanos.
- **Mostrar solo en `?debug=1`:** rechazado — la verificabilidad no debe esconderse detrás de flags.
- **Mostrar en JSON request (debug tools):** insuficiente — los auditores no abren DevTools.

## Consecuencias

**Positivas:**
- Audit trail visible.
- Bug reports de stakeholders incluyen la query (mejor diagnóstico).
- Soporte didáctico para usuarios técnicos.

**Negativas:**
- Un usuario malintencionado podría intentar reproducir la query con parámetros distintos en la API pública (`/resource/{id}.json?$query=...`). Mitigación: rate-limit ya existe en SODA; nuestra exposición es marginal.
- El SoQL puede contener nombres de columnas crudos (snake_case) que no son user-friendly. Aceptado — es la query EXACTA.

## Referencias

- ADR-017 (substrato verificable).
- Smoke E2E Fase C confirma que `<details>` con SoQL renderiza correctamente en los 5 TIPOs.
