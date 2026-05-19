# ADR-010: GeoResolver con DIVIPOLA + plantillas SoQL deterministas para comparativa

**Estado:** Aceptada
**Fecha:** 2026-05-19 (Sprint 6 — Beta-1)

## Decisión

`ai_engine/geo_resolver.py` detecta menciones a **territorios colombianos** en la pregunta del ciudadano y produce un `GeoContext` canónico con códigos DIVIPOLA, listado de targets, y modo de comparación. El `Analyzer` propaga ese contexto al pipeline para:

1. **Boost de retrieval**: hits que mencionan el territorio en `name + description` reciben `GEO_BOOST=0.08` adicional sobre el score del vector index.
2. **Hint al `QueryGenerator` LLM**: agrega "PISTA (DIVIPOLA): usa cod_dpto='05'" al prompt.
3. **Plantillas SoQL deterministas** (`build_comparison_soql`): para `comparison_mode in {"vs", "ranking", "vs_national"}`, construye el SoQL sin pasar por LLM. Reconoce tanto columnas-código (`cod_dpto`) como columnas-nombre (`departamento_del_hecho_dane`, `municipio`) con `lower(col) IN ('medellín','medellin','cali')`.

**Estructura de `GeoContext`**:

```python
@dataclass(frozen=True)
class GeoTarget:
    name: str
    code: str | None    # None solo para level="national"
    level: str          # "national" | "dpto" | "mpio"

@dataclass(frozen=True)
class GeoContext:
    targets: list[GeoTarget]
    comparison_mode: str | None  # "vs" | "ranking" | "vs_national" | None
    groupby: str | None
    scope: str
    confidence: float
    notes: list[str]
    top_n: int
```

Accessors retrocompatibles `dpto_code` / `dpto_name` / `mpio_code` / `mpio_name` que infieren del primer target del tipo correspondiente.

## Cobertura inicial

- 32 departamentos + Bogotá D.C. con sinónimos comunes (`Bogotá DC`, `Distrito Capital`, `Bogota`, etc.).
- 32 capitales departamentales (Medellín, Cali, Barranquilla, Quibdó, …).
- 7 municipios grandes no-capital (Soledad, Bello, Soacha, Itagüí, Envigado, Cartago, Buenaventura).

**Total: 39 municipios resolvibles**. Cobertura completa de ~1100 mpios DIVIPOLA queda como mejora futura ([`PROD_IMPROV.md#3`](../PROD_IMPROV.md#3-cobertura-completa-de-municipios-divipola)).

## Reglas de resolución

| Pregunta | Detección | GeoContext.targets | comparison_mode | SoQL generada |
|---|---|---|---|---|
| "Datos sobre educación" | sin geo | — | None | flujo normal sin filtro |
| "Inflación en Colombia" | scope=national | — | None | sin filtro (datos agregados) |
| "Homicidios en Bogotá" | dpto=11 | 1 dpto | None | `WHERE cod_dpto='11'` |
| "Cuántos municipios tiene Antioquia" | dpto=05 + plural genérico | 1 dpto (sin mpio capital) | None | `WHERE cod_dpto='05'` |
| "Compara Antioquia y Valle del Cauca" | 2 dptos | 2 dptos | vs | `WHERE cod_dpto IN ('05','76') GROUP BY cod_dpto` |
| "Bogotá vs Medellín" | 2 mpios | 2 mpios | vs | `WHERE lower(municipio) IN ('bogotá','bogota','medellín','medellin')` |
| "Top 10 ciudades con más homicidios" | ranking, "ciudades"=mpio | 0 targets | ranking | `GROUP BY cod_mpio ORDER BY count(*) DESC LIMIT 10` |
| "Casos por departamento" | groupby=cod_dpto | 0 targets | None | `GROUP BY cod_dpto` |
| "Tasa de homicidios en Antioquia respecto al nacional" | vs_national + dpto=05 | 1 dpto + 1 national | vs_national | `GROUP BY cod_dpto LIMIT 50` |

## Razón

Tres problemas reales medidos en journeys previos:

1. **"¿Cuántos municipios tiene Antioquia?"** (P1) retornaba datasets de pensiones o víctimas porque el vector index hace matching semántico superficial y "Antioquia" matchea muchos datasets que mencionan el dpto sin ser DIVIPOLA. El GeoResolver detecta el plural genérico ("municipios"), evita inferir el mpio capital (Medellín), y boostea datasets canónicos.
2. **Comparativas multi-target** ("compara A y B", "top N") no se soportaban — el LLM 3B intentaba generar SoQL con `IN(...)` y fallaba el 70% de las veces inventando columnas. La plantilla determinista es 100% confiable.
3. **Atribuciones incorrectas** del LLM: con código DIVIPOLA explícito en el prompt, el `QueryGenerator` tiene menos margen para errar.

## Regla anti-capital (fix P1)

Si la pregunta usa **plural genérico** (`"municipios"`, `"departamentos"`, `"territorios"`, `"regiones"`) y nombra un dpto pero **no** menciona explícitamente un mpio, descartamos los matches de mpios que sean capitales del dpto mencionado. Esto evita que "municipios de Antioquia" colapse a "Medellín capital".

## Protección anti falsos positivos

- Lista negra de países extranjeros (`Ecuador`, `Perú`, `Venezuela`, `Brasil`, `Panamá`, `México`, `Chile`, `Argentina`): si la pregunta los menciona y NO incluye "Colombia", retorna `None`.
- Dedup por overlap de matches: "Valle del Cauca" no se solapa con "Cauca".
- Fuzzy match `difflib.get_close_matches(cutoff=0.78)` tolera typos simples ("Medeyín" → Medellín) pero rechaza tokens demasiado distintos.

## Trade-offs

- **Cobertura municipal limitada (39 mpios)**: para preguntas sobre mpios pequeños el resolver retorna solo el dpto padre. No es regresión — el flujo cae al comportamiento sin geo (vector search) que funciona. Mejora futura cargar los ~1100 mpios desde DIVIPOLA.
- **No detecta comparativas implícitas**: "qué dpto tiene más X" no activa `comparison_mode='ranking'`. Mejora registrada en [`PROD_IMPROV.md#4`](../PROD_IMPROV.md#4-detección-de-comparativa-implícita).
- **Atribución incorrecta sobrevive con plantilla**: si el dataset elegido no es DIVIPOLA, la plantilla puede contar cosas distintas a las que el ciudadano pregunta. El bloque "📊 Datos verificados" debajo de la narrativa permite contrastar. Mitigación posterior en [`PROD_IMPROV.md#5`](../PROD_IMPROV.md#5-validación-geográfica-de-rows-anti-atribución-incorrecta).

## Referencias

- `ai_engine/geo_resolver.py` — implementación.
- `ai_engine/analyzer.py::_retrieve`, `_execute_soql`, `_geo_match_tokens`.
- `tests/test_geo_resolver.py` (13 frozen) + `tests/test_geo_comparison.py` (16 frozen).
- [`docs/glossary.md#divipola`](../glossary.md) — códigos DIVIPOLA.
- Commits `2fb19cd`, `46c13ee`.
