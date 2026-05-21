# 03 — Data Preparation

> CRISP-ML(Q) — Fase 3. Cómo preparamos los metadatos del catálogo para que el agente los pueda usar bien.

## Resumen

DatosVivos **no toca los datos en sí** (siempre los lee en vivo desde Socrata). Lo que sí preparamos son los **metadatos del catálogo**: descripciones, nombres de entidades, columnas. La preparación produce tres artefactos: el **índice vectorial** (ChromaDB) y dos diccionarios — **acrónimos** (Tier 1) y **topic keywords** (Tier 2) — que se usan en la búsqueda multi-tier.

---

## 🏛️ Para el jurado MinTIC

### Qué demuestra esta fase

- El pipeline de preparación es **reproducible desde cero**: cualquier auditor con acceso a internet puede correr `python -m scripts.build_index` y `python -m scripts.extract_topic_keywords` y obtener los mismos artefactos.
- La preparación está **probada**: `tests/test_scripts_reproducibility.py` corre ambos scripts contra un tmp_path limpio y verifica que generan estructuras válidas.
- **No metimos datos sintéticos.** Los acrónimos y keywords salen del propio catálogo (campo `attribution` real) + revisión humana.

### Datos generados

| Artefacto | Tamaño | Cobertura | Generador |
|---|---|---|---|
| Índice vectorial (`data/vector_index/`) | ~30 MB | 8 389 datasets | `scripts/build_index.py` |
| Diccionario de acrónimos | 117 entidades · 562 aliases | Sector público colombiano | `mcp_server/socrata/acronyms.py` (curado a mano + extracción) |
| Diccionario de topic keywords | ~3 050 keywords | Las mismas 117 entidades | `scripts/extract_topic_keywords.py` + `topic_keywords_data.py` |

### Trazabilidad

Cada artefacto se regenera con un comando documentado, sin pasos manuales ocultos. Los archivos generados están versionados (acrónimos, topic keywords) o gitignorados pero reconstruibles (índice vectorial, demasiado grande para git).

---

## 🛠️ Para ciudadanos técnicos

### Pipeline 1: índice vectorial del catálogo

**Objetivo:** dada una pregunta en español, encontrar los `k` datasets más relevantes sin depender exclusivamente del *keyword matching* literal de Socrata.

**Cómo:**

```
[Discovery API] → JSON con name+description+columns
       │
       ▼
[Concatenación a texto plano por dataset]
       │
       ▼
[sentence-transformers/multilingual-e5-large]
       │ (embeddings 1024-dim)
       ▼
[ChromaDB cosine] → data/vector_index/
```

Implementación: `scripts/build_index.py` + `ai_engine/vector_index.py`.

**Decisiones de diseño concretas:**

- **Modelo:** `multilingual-e5-large` (sentence-transformers). Soporta español nativamente, suficientemente grande para captar matices, no tan pesado como modelos 7B+. ADR-002.
- **Almacenamiento:** ChromaDB local en disco. Sin servicios extra; cargable con un constructor. Alternativa considerada (FAISS) descartada por ergonomía de Python.
- **Threshold de similitud:** `min_score = 0.83`. Empírico: por debajo se filtran demasiados falsos positivos. Configurable en `VectorIndex.search`.
- **Idempotencia:** el script reconstruye el índice completo cada corrida; no hay deltas para evitar deriva en orden de inserción.

**Paginación cuidadosa:** la Discovery API devuelve en páginas de 100. Pagina hasta agotar (o hasta `--limit` en dev). El script imprime el total recibido para que sea visible.

### Pipeline 2: acrónimos del sector público (Tier 1)

**Problema:** un ciudadano pregunta *"datos del DANE"*; Socrata Discovery `q=DANE` retorna pocos resultados porque el catálogo guarda *"Departamento Administrativo Nacional de Estadística"* completo, no la sigla.

**Solución:**

`mcp_server/socrata/acronyms.py` mapea **117 entidades** del sector público colombiano, cada una con su nombre canónico y todos sus alias conocidos. Ejemplos:

```python
ENTITIES = {
  "DANE": Entity(
      canonical="Departamento Administrativo Nacional de Estadística",
      aliases={"DANE", "Departamento Nacional de Estadística", ...},
      category="estadística",
  ),
  "INVÍAS": Entity(
      canonical="Instituto Nacional de Vías",
      aliases={"INVIAS", "INVÍAS", "Instituto Nacional de Vías", ...},
      category="transporte e infraestructura",
  ),
  ...
}
```

Cuando llega una query a `DiscoveryClient.search`, antes de enviarla a Socrata, **expandimos los acrónimos** al nombre canónico. ADR-006.

**Cómo se generaron los 562 aliases:**

1. Extracción del campo `attribution` de los 8 389 datasets indexados → lista de entidades reales.
2. Para cada entidad, generación automática de variantes (con/sin tildes, con/sin "del", abreviaturas comunes).
3. **Revisión humana** para añadir alias coloquiales (*"min trabajo"*, *"hacienda"*, *"DPS"*) y categorizar.

### Pipeline 3: topic keywords iterativos (Tier 2)

**Problema:** el ciudadano dice *"información sobre vacunación"* sin mencionar MinSalud ni INS. Tier 1 (acrónimos) no expande nada; Socrata `q=vacunación` puede devolver resultados débiles o cero.

**Solución (ADR-007):**

Asociar a cada entidad un conjunto de **keywords temáticos** que la representan. Cuando Tier 1 + Socrata directa fallan, iteramos grupos de **2 entidades por iteración** ordenadas por overlap de keywords con la query, hasta encontrar resultados o agotar.

```python
# Pseudocódigo en mcp_server/socrata/topic_keywords.py
def expand_with_topics_iterative(client, query, limit, max_groups=None):
    base_results = await client.search(query)
    if base_results:
        return base_results
    groups = topic_match_ranked(query)  # grupos de 2, ordenados por overlap
    for group in groups[:max_groups]:
        merged_query = f"{query} {' OR '.join(group)}"
        results = await client.search(merged_query)
        if results:
            return results
    return []
```

**Generación del diccionario:** `scripts/extract_topic_keywords.py` analiza el corpus indexado (nombre + descripción + columnas) por entidad, identifica los términos más distintivos (TF-IDF con filtros), y los persiste en `topic_keywords_data.py`. Suplementos manuales para casos críticos (*IDEAM ↔ "clima"*, *AND ↔ "tierras restitución"*).

**Filtros aplicados durante extracción:**

- `min_len=4` para evitar partículas.
- `min_freq=2` para evitar términos únicos a un solo dataset.
- Filtro global contra `all_aliases_lower` para no re-incluir acrónimos (esos son Tier 1).
- Filtro contra stopwords español + términos genéricos (*"información"*, *"datos"*, *"colombia"*).

### Normalización DIVIPOLA

Para que `cross_datasets` funcione, los códigos territoriales deben ser comparables:

- **Padding a 2 chars** para `cod_dpto` (`"5"` → `"05"`).
- **Padding a 5 chars** para `cod_mpio` (`"5001"` → `"05001"`).
- Coerción a string (algunos datasets guardan como int, otros como str).

Aplicado lazy en `cross_datasets` antes del `pandas.merge`, no en el pipeline de indexación (no queremos modificar el catálogo en sí).

---

## 👥 Para ciudadanía general

### ¿Por qué hay que "preparar" los datos?

Imagínalo así: la información en `datos.gov.co` está ahí, pero está en miles de archivos separados, cada uno con nombres técnicos y descripciones a veces incompletas. Si le diéramos al agente solo un buscador básico, sería como pedirle a alguien que encuentre un libro en una biblioteca sin catálogo: tendría que abrir uno por uno.

Lo que hicimos fue **construirle al agente un catálogo inteligente**:

- Una **memoria semántica** (índice vectorial) que entiende que "vivienda" y "casa" son cosas parecidas, aunque las palabras sean diferentes.
- Un **diccionario de siglas**: si tú dices "DANE" o "Ministerio de Trabajo", el agente sabe a qué entidad real corresponden.
- Un **mapa temático**: si tú no mencionas la entidad pero sí el tema (*"vacunación"*, *"vías terciarias"*, *"impuestos"*), el agente puede inferir cuáles entidades probablemente publican algo sobre eso.

### ¿Esto significa que el agente puede equivocarse en la búsqueda?

Sí, y lo asumimos honestamente. Hay tres niveles de búsqueda que se intentan en cascada:

1. Primero: buscar por palabras exactas + siglas conocidas.
2. Si no hay resultados: buscar por temas relacionados con entidades.
3. Si tampoco: pedir a la IA que reformule la pregunta y reintentar.

Cuando los tres niveles fallan, el agente te dice *"no encontré datasets que respondan a tu pregunta"* en vez de inventar. Esa honestidad es deliberada.

### Lo que hay versionado y lo que se regenera

- **Versionado en el repositorio** (lo puedes ver en GitHub): los diccionarios de siglas y topic keywords, los scripts que los generan, todos los tests.
- **Regenerable bajo demanda** (no cabe en git): el índice vectorial completo. Cualquier persona puede reconstruirlo con un comando.

---

## Siguiente capítulo

[04 — Modeling](./04_modeling.md): qué modelos de IA usamos para entender preguntas, clasificarlas y generar consultas SoQL.
