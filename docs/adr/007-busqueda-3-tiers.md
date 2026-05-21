# ADR-007: Búsqueda con fallback en 3 tiers

**Estado:** Aceptada
**Fecha:** Sprint 3 + extensiones (acrónimos, topic keywords)

## Decisión

`DiscoveryClient.search()` + `Analyzer.analyze()` aplican **tres niveles de expansión en cascada** cuando la query directa a Socrata no encuentra resultados:

1. **Tier 1 — Acrónimos** (`mcp_server/socrata/acronyms.py`)
   Match exacto de sigla/nombre/alias → expansión al nombre canónico de la entidad antes de pegarle a Socrata. Sin LLM. Cero latencia agregada. 117 entidades, 562 aliases.

2. **Tier 2 — Topic keywords iterativo** (`mcp_server/socrata/topic_keywords.py`)
   Si Tier 1 no aportó y Socrata devuelve `[]`, calcula ranking de entidades por overlap de keywords temáticos. Agrupa de 2 en 2 por relevancia. Intenta búsqueda con grupo 1; si vacío, grupo 2; etc. hasta agotar o encontrar.

3. **Tier 3 — Reformulación por LLM** (`Analyzer._llm_reformulate`)
   Si los dos tiers anteriores agotan opciones sin resultados, el analyzer invoca al LLM para reformular la pregunta con keywords alternativos. Marca en `AnalysisResult.narrative` que se reformuló (transparencia con el usuario).

## Razón

Los ciudadanos rara vez mencionan a las entidades por nombre. Dicen *"datos sobre tierras"*, no *"datos de la ANT"*. Tres tiers cubren tres perfiles de usuario:

- **Tier 1:** el que conoce siglas.
- **Tier 2:** el que solo conoce el tema.
- **Tier 3:** el que escribe vago, ambiguo o con errores.

## Trade-offs

- **Cap de 2 entidades por grupo en Tier 2:** evita inundar la query a Socrata con 5+ nombres canónicos (cada uno de 6-8 palabras), lo que mete ruido en el matching. A cambio, hasta N llamadas HTTP secuenciales en el peor caso. En la práctica las queries con tema claro encuentran en 1-2 iteraciones.
- **Tier 3 es caro (~2 s latencia LLM):** solo se ejecuta cuando tiers 1 y 2 fallan. Si Ollama no está disponible (CI o dev sin daemon), Tier 3 se salta silenciosamente y el caller recibe `[]`.
- **Datos de keywords data-driven:** se extraen del campo `description` + `name` + columnas de los datasets de cada entidad. Filtros de stopwords y términos ultra-genéricos (*"datos"*, *"información"*, *"colombia"*).

## Referencias

- `mcp_server/socrata/acronyms.py` — Tier 1
- `mcp_server/socrata/topic_keywords.py` + `topic_keywords_data.py` — Tier 2
- `ai_engine/analyzer.py::_llm_reformulate` — Tier 3
- `scripts/extract_topic_keywords.py` — generador de keywords data-driven
- `tests/test_acronyms_acceptance.py`, `test_topic_keywords_acceptance.py`
- [`docs/crisp_mlq/03_data_preparation.md`](../crisp_mlq/03_data_preparation.md)
