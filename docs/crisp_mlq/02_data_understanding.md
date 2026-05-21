# 02 — Data Understanding

> CRISP-ML(Q) — Fase 2. Cómo es el catálogo de datos.gov.co y qué descubrimos al inspeccionarlo a fondo.

## Resumen

`datos.gov.co` corre sobre **Socrata** y expone tres APIs públicas: **Discovery** (búsqueda en el catálogo), **Metadata** (esquema de un dataset) y **SODA** (consulta de filas con SoQL). Al momento de la entrega, el portal contiene **8 389 datasets** publicados por **~117 entidades**. La calidad de metadatos es desigual: hay campos clave bien poblados (nombre, descripción, columnas) y otros mal usados (`tags`).

---

## 🏛️ Para el jurado MinTIC

### Qué demuestra esta fase

1. **El equipo entendió el dominio antes de programar.** No asumimos cómo se llaman las entidades o cómo se distribuye el catálogo: descargamos todo el índice y lo analizamos.
2. **Las decisiones técnicas de los capítulos 3–4 (limpieza, expansión de acrónimos, búsqueda multi-tier) están justificadas por hallazgos reales del catálogo**, no por intuición.
3. **Reconocimos defectos del catálogo (no nuestros)** y diseñamos el agente para mitigarlos, en lugar de pretender que el catálogo es perfecto.

### Cifras de cobertura

| Métrica | Valor | Fuente |
|---|---|---|
| Datasets indexados | 8 389 | `scripts/build_index.py` corriendo contra `api.us.socrata.com/api/catalog/v1?domains=www.datos.gov.co` |
| Entidades distintas (`attribution`) | ~117 | `mcp_server/socrata/acronyms.py` — 117 entidades canónicas mapeadas |
| Aliases / acrónimos catalogados | 562 | `acronyms.py` — 4.8 promedio por entidad |
| Topic keywords (Tier 2) | ~3 050 | `topic_keywords_data.py` — keywords semánticos extraídos del corpus |
| APIs Socrata consumidas | 3 | Discovery, Metadata, SODA |

### Cumplimiento normativo verificable

- Todo lo consultado son **datos abiertos publicados** bajo la Ley 1712 de 2014. No tocamos información restringida.
- El identificador del dataset (`id` Socrata, ej. `gdxc-w37w`) y el permalink se preservan en toda respuesta del agente → trazabilidad jurídica.

---

## 🛠️ Para ciudadanos técnicos

### Las tres APIs que consume DatosVivos

| API | Endpoint base | Para qué la usamos | Cliente |
|---|---|---|---|
| **Discovery** | `https://api.us.socrata.com/api/catalog/v1?domains=www.datos.gov.co` | Buscar datasets por keyword, listar catálogo para indexar. | `mcp_server/socrata/discovery_client.py` |
| **Metadata** | `https://www.datos.gov.co/api/views/{dataset_id}.json` | Esquema (columnas, tipos, descripción) de un dataset. | `mcp_server/socrata/metadata_client.py` |
| **SODA** | `https://www.datos.gov.co/resource/{dataset_id}.json` | Ejecutar SoQL para traer filas. | `mcp_server/socrata/soda_client.py` |

> ⚠️ **Gotcha real:** `api.us.socrata.com` indexa *todos los portales Socrata del mundo* (NYC, Chicago, CDC...). El parámetro `domains=` es **obligatorio** para filtrar solo `datos.gov.co`. Caída en este detalle gastaría horas debuggeando ([lessons_learned.md](../lessons_learned.md)).

### Distribución del catálogo

Tras indexar los 8 389 datasets observamos:

- **Concentración alta por entidad.** Pocas entidades dominan el volumen: DANE, SDH, secretarías distritales, MinSalud, MinTransporte. La cola larga incluye gobernaciones, alcaldías, entes territoriales con ≤ 5 datasets.
- **Calidad de descripción variable.** Algunos datasets tienen descripción rica (>200 palabras, contexto, periodicidad); otros vienen con descripción placeholder (`<p></p>` o copy-paste del título).
- **Columnas bien tipadas (mayoría).** Socrata fuerza tipos básicos (texto, número, calendar_date, point); esto es bueno para SoQL automático.

### Bug del campo `tags` que no es bug nuestro

Al indexar el catálogo descubrimos que el campo `tags` de Discovery (que esperaríamos contuviera tags semánticos como *"salud"*, *"educación"*) **viene poblado con los nombres normalizados de las columnas** del dataset (`cod_dpto`, `latitud`, etc.). No son tags semánticos; son metadatos de esquema mal etiquetados como tags.

- **Implicación:** no podemos confiar en `tags` para clasificación temática.
- **Mitigación:** construimos nuestros propios `topic_keywords` extrayendo señal del nombre + descripción + columnas. Ver [03_data_preparation.md](./03_data_preparation.md).
- **Origen del bug:** está en la fuente (`datos.gov.co`) o en una versión del conector Socrata, no en nuestro pipeline. Lo documentamos como deuda técnica externa.

### Joins reales: el caso DIVIPOLA

Para validar que `cross_datasets` funciona, identificamos un dataset *canónico* que sirve como puente entre entidades: **DIVIPOLA** (`gdxc-w37w`, *"Departamento, Municipio y Centro Poblado"*, DANE), con las columnas `cod_dpto`, `cod_mpio`, `dpto`, `nom_mpio`, `latitud`, `longitud`.

- **Cifras del dataset DIVIPOLA:** 1 122 municipios, 33 departamentos. **Antioquia (cód. 05) tiene 125 municipios** — usamos este número como *golden assertion* en tests porque es verificable contra fuente oficial.
- **Joins probados:** DIVIPOLA × dataset territorial por `cod_dpto` o `cod_mpio`. Cualquier dataset que respete esa convención puede cruzarse.

> ⚠️ **Gotcha real:** la primera versión usó el dataset `vcjz-niiq` como contraparte; no compartía `cod_dpto` con DIVIPOLA. Migramos al par `t7kp-7a7c` que sí. Lección: **antes de usar un par para cruce, verificar que comparten la clave**.

### Lo que el LLM necesita saber sobre los datos

Para que el `query_generator` no invente columnas, le pasamos en el prompt:

1. **Esquema real** del dataset (`get_metadata`): nombres exactos de columnas + tipos.
2. **Muestra de filas** (`sample_rows`, 3-5 filas via `SELECT * LIMIT 5`): le permite distinguir `cod_dpto` (`"05"`) de `dpto` (`"ANTIOQUIA"`).

Esta segunda pieza fue una **lección aprendida**: Qwen 3B confundía sistemáticamente `cod_dpto` con `dpto` sin ver una muestra. Con la muestra incorporada, la confusión cayó dramáticamente (no a 0, pero a manejable).

---

## 👥 Para ciudadanía general

### ¿Qué hay en datos.gov.co?

Datos.gov.co es el portal oficial donde las entidades del Estado colombiano publican información pública en formatos que pueden ser leídos por máquinas. Hay datos de:

- **Salud** (afiliados a EPS, infraestructura hospitalaria, calidad de servicios).
- **Educación** (matrículas, instituciones, resultados Saber).
- **Transporte** (vías, accidentes, congestión, transporte público).
- **Hacienda y finanzas** (presupuesto, ejecución, contratos).
- **Demografía** (censo, división política, estadísticas vitales).
- **Ambiente** (calidad del aire, agua, áreas protegidas).
- Y muchos más, publicados por ministerios, secretarías, alcaldías, gobernaciones y entidades adscritas.

Al momento de hacer este proyecto contamos **8 389 datasets** públicos.

### ¿Es información oficial?

Sí. Cada dataset pertenece a una entidad publicadora (lo verás como *"entidad"* o *"attribution"* en la app). El agente siempre te dice **quién publicó el dato** y te enlaza al dataset original en `datos.gov.co`, para que puedas verificar la fuente.

### ¿Los datos están siempre actualizados?

**Depende de cada entidad.** Algunas actualizan diariamente (transporte, salud), otras mensualmente, otras anualmente. El agente te muestra la fecha de la última actualización (`updated_at`) para que sepas qué tan reciente es lo que estás viendo.

### ¿Qué pasa si el dato que busco no existe?

El agente te dice honestamente que no encontró un dataset que responda tu pregunta. **No se lo inventa.** En esos casos puedes:

1. Reformular la pregunta con palabras diferentes.
2. Usar el modo "Explorador" para navegar manualmente.
3. Consultar directamente la entidad responsable del tema.

---

## Siguiente capítulo

[03 — Data Preparation](./03_data_preparation.md): qué transformaciones aplicamos a estos datos para que la IA los pueda usar.
