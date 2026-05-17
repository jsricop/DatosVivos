# 04 — Modeling

> CRISP-ML(Q) — Fase 4. Qué modelos de IA usamos, cómo se orquestan, y por qué local-first.

## Resumen

DatosVivos usa **tres modelos** especializados, no uno monolítico:

1. **Embeddings multilingüe** (`multilingual-e5-large`) para recuperar datasets relevantes del catálogo.
2. **Clasificador de intención** basado en prototipos de embeddings (no LLM) para decidir qué tipo de pregunta es.
3. **LLM local** (Qwen 2.5 Coder vía Ollama) para tres tareas: generar SoQL, reformular preguntas (Tier 3 fallback) y narrar resultados en español.

Todo orquestado por `ai_engine/analyzer.py`. **Local-first**: ningún componente requiere proveedores cloud para funcionar.

---

## 🏛️ Para el jurado MinTIC

### Qué demuestra esta fase

- **Soberanía técnica real:** el LLM corre en infraestructura propia (Ollama). El proyecto está diseñado para que se despliegue en una VM del Estado y nada salga a proveedores externos.
- **Modelos especializados, no un martillo único:** cada problema se resuelve con la herramienta más adecuada. No usamos LLM cuando un clasificador deterministico era suficiente; no usamos clasificador cuando un LLM era inevitable.
- **Backend intercambiable:** la capa `LLMBackend` (ADR-001) permite cambiar de Ollama a Anthropic (Claude) a OpenAI a un proveedor local sin tocar el resto del código. Política, no técnica.

### Modelos en producción

| Componente | Modelo | Tamaño | Dónde corre | Selección configurable por |
|---|---|---|---|---|
| Embeddings | `intfloat/multilingual-e5-large` | ~2.2 GB | Local (CPU o GPU) | `ai_engine/vector_index.py` |
| Intent classifier | Centroides sobre embeddings + cosine | < 1 KB de datos | Local CPU | `ai_engine/intent_classifier.py` |
| LLM (default) | `qwen2.5-coder:3b` Q4_K_M | ~2 GB | Ollama local | `LLM_BACKEND=ollama` |
| LLM (alternativo cloud) | Claude / Gemini / OpenAI | — | API externa | `LLM_BACKEND=anthropic` (stub) |
| LLM (testing) | MockBackend | — | In-process | `LLM_BACKEND=mock` |

### Argumento técnico para "local-first"

Para un agente de gobierno, **no es opcional**: las consultas ciudadanas no pueden filtrarse a un proveedor extranjero por defecto. Si una entidad quiere usar Claude o Gemini para narrativas más fluidas, puede activarlo conscientemente con `LLM_BACKEND=anthropic|google`. Pero el camino por defecto preserva la soberanía.

---

## 🛠️ Para ciudadanos técnicos

### Modelo 1: embeddings con `multilingual-e5-large`

**Por qué este modelo:**

- Modelo de la familia **e5** entrenado por Microsoft, optimizado para retrieval semántico multilingüe.
- Soporta **español** sin tener que entrenar nada propio.
- Salida de **1024 dimensiones**, balance razonable entre expresividad y memoria.
- **Open weights**, sin restricciones de uso.

**Cómo se usa:**

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("intfloat/multilingual-e5-large")
emb = model.encode("¿cuántos hospitales hay en Cundinamarca?", normalize_embeddings=True)
# luego: ChromaDB cosine similarity contra los 8 389 datasets indexados
```

**Decisión clave:** la búsqueda vectorial **no reemplaza** la búsqueda de Socrata; las dos coexisten y se cruzan. El vector index es el "primer lugar donde miramos"; Socrata Discovery es el "confirmador en el catálogo oficial".

### Modelo 2: clasificador de intención sin LLM

**Por qué no usar LLM aquí:**

Clasificar `"¿cuántos hospitales hay?"` como *count* vs `"muéstrame los hospitales"` como *list* es un problema **estrecho y repetitivo**. Usar un LLM 7B costaría 200-500 ms por consulta para una decisión que se puede hacer en < 5 ms con embeddings.

**Cómo funciona:**

1. Definimos **prototipos** (5–10 frases canónicas) por intent: `search`, `count`, `compare`, `aggregate`, `lookup`, `cross`, `descriptive`.
2. Pre-computamos el centroide de embeddings de cada intent.
3. En runtime: embedding de la pregunta → cosine vs cada centroide → intent ganador.
4. Confianza = max similarity. Si está por debajo de un umbral, default a `search`.

Implementación: `ai_engine/intent_classifier.py`. Probado en `tests/test_intent_classifier.py`.

**Honestidad:** este clasificador NO es perfecto. Hay zonas grises (*"compara X con Y"* puede ser comparative o cross). Cuando se equivoca, el siguiente componente (analyzer) suele compensar porque la búsqueda vectorial recupera el dataset correcto igual. Documentado en lessons_learned: "el classifier falla a veces pero el pipeline aguanta".

### Modelo 3: LLM local con Qwen 2.5 Coder

**Por qué Qwen 2.5 Coder y no Llama 3 / Mistral / etc.:**

- **Coder** está fine-tuned para generación de código y consultas estructuradas — exactamente lo que necesitamos para SoQL.
- Tamaño 3B Q4_K_M = **~2 GB de RAM**, corre en hardware modesto del Estado (no requiere GPU dedicada).
- Versión 7B disponible si el hardware lo permite (ADR-001 contempla swap por env var).
- Licencia permisiva.

**Tres tareas que le delegamos:**

1. **NL → SoQL** (`ai_engine/query_generator.py`)  
   Prompt incluye: pregunta + esquema real del dataset + **muestra de 3-5 filas** (`sample_rows`). Sin la muestra, Qwen 3B confundía `cod_dpto` con `dpto`. Con ella, mucho mejor. Reintenta hasta 2 veces si la SoQL usa columnas inválidas.

2. **Reformulación Tier 3** (`ai_engine/analyzer.py — _llm_reformulate`)  
   Cuando los 3 tiers de búsqueda fallan, le pedimos al LLM 3-5 keywords alternativas para reintentar. Si tampoco encuentra, devolvemos respuesta honesta de "no datasets".

3. **Narrativa en español** (`ai_engine/analyzer.py — _narrate_*`)  
   Toma los resultados de la consulta + datasets usados, genera 1-3 párrafos en español citando fuentes.

**Limitaciones conocidas del 3B (honestidad):**

- Bajo carga concurrente, timeouts de 60s eran insuficientes. Subimos a **120s** (`OllamaBackend`).
- Flakiness ocasional: a veces inventa una columna agregada (`cantidad_municipios`) en lugar de usar `count(*) AS n`. Reintentamos, pero a veces termina con `SELECT * LIMIT 1` que no cumple el objetivo. Es un test verificado fallando ocasionalmente — lo dejamos visible en `test_sprint3_acceptance.py` en lugar de esconderlo. Mitigable subiendo a 7B en hardware con más memoria.

### Orquestación: `Analyzer.analyze()`

```
Pregunta NL
    │
    ▼
┌───────────────────────────────────┐
│ IntentClassifier.classify()       │ ← embeddings, sin LLM
└─────────────┬─────────────────────┘
              │
              ▼
┌───────────────────────────────────┐
│ VectorIndex.search(k=5)           │ ← retrieval semántico
└─────────────┬─────────────────────┘
              │
        ¿hits == 0?
              │
        sí ────▼─── no
              │       │
   LLM        │       │
   reformula ─┘       │
   (Tier 3)           │
                      ▼
              ┌──────────────────┐
              │ intent == search?│
              └────┬─────────────┘
                   │
            sí ────▼─── no
                   │       │
        narrativa  │       ▼ (futuro: query_generator
        de búsqueda│         + SodaClient para
                   │         consultas no-search)
                   ▼
              AnalysisResult
```

`AnalysisResult` (`ai_engine/analyzer.py`) es la **interfaz estable** entre el motor de IA y la UI Streamlit. Tiene `question`, `intent`, `datasets_used`, `soql_executed`, `rows`, `narrative`. Dict-like para compatibilidad.

### Backend intercambiable (ADR-001)

```python
# ai_engine/llm_backend.py
class LLMBackend(Protocol):
    async def generate(self, prompt: str, **kw) -> str: ...

class OllamaBackend(LLMBackend): ...
class AnthropicBackend(LLMBackend): ...  # stub, completable
class MockBackend(LLMBackend): ...        # determinista, para tests

def get_backend() -> LLMBackend:
    name = os.getenv("LLM_BACKEND", "ollama")
    ...
```

Esto permite que **el mismo agente** corra:

- En una VM del estado, con Ollama local (default).
- En desarrollo, con MockBackend (sin esperar a Ollama).
- En una alcaldía con presupuesto cloud, con Claude o Gemini.

Sin cambiar el código del `Analyzer` ni de las páginas Streamlit.

---

## 👥 Para ciudadanía general

### ¿La IA "piensa"?

No en el sentido humano. Lo que hace el agente es:

1. **Comparar tu pregunta** con miles de descripciones de datasets para ver cuáles se parecen más al tema. (Esto lo hace un modelo de comparación semántica, sin "entender" como un humano.)
2. **Clasificar el tipo de pregunta**: ¿estás contando algo, comparando, listando, buscando?
3. **Traducir tu pregunta** al idioma técnico que usa `datos.gov.co` (un lenguaje llamado SoQL).
4. **Narrar el resultado** en español, citando de dónde vino la información.

### ¿La IA puede inventar respuestas?

**Diseñamos el sistema para que no pueda.** El LLM nunca pone números él mismo: solo formula preguntas técnicas; las respuestas con cifras vienen siempre de las APIs reales de `datos.gov.co`. Si la búsqueda no encuentra datasets, el agente te dice *"no encontré información"*, no inventa.

Esto es importante: muchos asistentes de IA pueden "alucinar" datos. DatosVivos está construido para que cualquier número que veas venga de un dataset oficial trazable.

### ¿Y si quiero usar un LLM más potente?

Por defecto usamos un modelo que corre en una computadora del proyecto, sin pagar nube. Pero si una entidad o usuario avanzado quisiera conectarlo a Claude (Anthropic), Gemini (Google) u otro, **el sistema lo permite cambiando una sola variable de configuración**. No hay que reescribir el agente.

### ¿Por qué eso es importante?

Porque cada institución puede decidir según su presupuesto, su política de privacidad y su nivel de confianza:

- *"Quiero que nada de lo que pregunten los ciudadanos salga a servidores extranjeros"* → modelo local.
- *"Quiero respuestas más fluidas, pago una API"* → cloud LLM.

Ambos caminos están abiertos, y el código que los soporta es el mismo.

---

## Siguiente capítulo

[05 — Evaluation](./05_evaluation.md): cómo verificamos que esto funciona y qué limitaciones documentamos honestamente.
