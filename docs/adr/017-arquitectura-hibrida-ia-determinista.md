# ADR-017: Arquitectura híbrida — IA razona, motor determinista ejecuta y verifica

**Estado:** Aceptada
**Fecha:** 2026-05-25

## Decisión

DatosVivos adopta una arquitectura en **dos planos con responsabilidades estrictamente separadas**:

### Plano determinista (la fuente de verdad)

- **Selección de dataset:** chips estructurados (TEMA/TIPO/TERRITORIO/ENTIDAD) → filtro SQL contra el catálogo curado en Postgres. Sin retrieval ML. (`api/routes/chips.py`)
- **Ejecución de consulta:** SoQL contra Socrata vía SODA. Las **cifras provienen SIEMPRE de filas reales**, nunca del LLM. Reafirma el ADR-009 (ADR temprano no conservado).
- **Medida por defecto:** `COUNT(*)`; la suma de un valor (`SUM(métrica)`) se ofrece solo cuando existe una columna métrica usable. Ver `project_soql_count_default` (memoria) y la auditoría de cobertura 2026-05-25.

### Plano de razonamiento (la IA)

La IA opera **solo en las partes ambiguas y de lenguaje**, siempre contra un substrato verificable:

1. **NL → estructura:** mapear una pregunta en lenguaje libre a chips `{tema, tipo, territorio, entidad, refinador}`. Clasificación a vocabulario finito.
2. **Selección de columnas:** inferir qué métrica/dimensión/fecha/geo usar dentro del dataset ya elegido, contra `dataset_columns_curated`.
3. **SoQL asistido por IA con validación:** para preguntas fuera de las plantillas TIPO, la IA genera SoQL viendo **solo columnas curadas reales**; un validador verifica (las columnas existen, hay filtro geo cuando aplica, es read-only) **antes** de ejecutar.
4. **Narrativa:** explicar resultados ya verificados.

### Principio rector

> **La IA razona; el motor determinista ejecuta y verifica.**

Una cifra alucinada es el peor modo de fallo de una herramienta de datos públicos del Estado. Preferimos que el sistema diga *"no puedo responder eso con certeza"* a que responda con fluidez pero a veces invente. La fluidez sin verificación es un pasivo, no un activo.

## Razón

- El retrieval open-text contra ~8.000 datasets (ADR-007, no conservado) era poco confiable — elegía UPTC como top-1 para preguntas de Bogotá. Los chips deterministas eliminan ese fallo **por diseño** (filtro sobre `jurisdiccion_geo_codes`).
- Pero el determinismo puro **capa la expresividad** en 5 TIPO fijos. La IA recupera el long-tail de preguntas **sin reintroducir alucinación**, porque opera contra un contrato tipado (columnas curadas) y todo output se valida antes de ejecutar.
- Construir el plano determinista **primero** es metodológicamente necesario: sin substrato verificable no hay ground truth contra el cual iterar la capa LLM (cada cambio sería a ciegas).

## Trade-offs

- **La capa NL→chips puede inferir mal.** Mitigación: pre-marca los chips inferidos y deja al usuario corregir antes de buscar. Telemetría `auto_chip_accepted` vs `auto_chip_corrected`.
- **El SoQL asistido por IA exige un validador robusto.** Si el validador no puede garantizar el SoQL generado, se cae a la plantilla TIPO determinista o se informa la incapacidad. **Nunca se ejecuta SoQL no validado.**
- **Dos planos agregan complejidad** vs un solo LLM end-to-end. Se acepta a cambio de cero alucinación de cifras.
- **Cobertura real (auditoría 2026-05-25):** con `COUNT(*)` por defecto los TIPO cubren 57-70% de los datasets útiles (Mapa 57%, Tendencia 64%, Ranking 70%); exigir métrica los bajaría a 28-30%. El techo de métricas sumables (43%) es real y no se gana iterando el clasificador.

## Referencias

- `api/routes/chips.py` — plano determinista (filtro chips → SQL)
- `ai_engine/column_classifier.py` + tabla `dataset_columns_curated` — contrato tipado de columnas
- `ai_engine/analyzer.py` — camino legacy de texto libre (ahora "Modo libre")
- ADR-007 — búsqueda 3-tiers (degradada a Modo libre por este ADR; ADR temprano no conservado)
- ADR-009 — cifras solo desde datos reales (reforzada; ADR temprano no conservado)
- [ADR-010](./010-geo-resolver.md) — DIVIPOLA + plantillas SoQL deterministas
- Plan `~/.claude/plans/merry-puzzling-pie.md` — roadmap A→D + Fase 2 (mapper NL→chips)
