# DatosVivos — el panorama de los datos abiertos de Colombia

**Datos del Estado, en tus palabras.**

> **Concurso Datos al Ecosistema 2026: IA para Colombia** (MinTIC)
> **Equipo 93 · Reto de Innovación y Tecnología (Reto 7, id 102) · Nivel Avanzado**
> Equipo GIT TIC — **Agencia Nacional de Infraestructura (ANI)**
>
> 🔴 **En producción:** https://datosvivos.co — cifras en vivo, actualización diaria automática.

DatosVivos integra en un solo catálogo consultable los **25.192 datasets** públicos de
Colombia (corte 2026-07-10; se actualiza a diario) y los presenta en **tres niveles**:
el **panorama nacional** para tomadores de decisiones, el **tablero interactivo** por
sector y entidad, y un **buscador en lenguaje natural** con motor NL2SQL verificado
para la ciudadanía. Incluye modo de accesibilidad (voz y narración, Ley 1618 de 2013).

---

## Problema abordado

Colombia publica más de 25.000 datasets abiertos, pero **nadie tiene el panorama**:
una entidad no sabe cuántos datasets tiene publicados ni cuántos actualizados; un
gerente sectorial con N entidades adscritas no puede hacer control; el propio MinTIC
carece de una vista consolidada (los portales federados viven separados); y el
ciudadano que quiere una cifra necesita saber de APIs y SQL. **Si no conocemos, no
podemos medir — y si no medimos, no podemos mejorar.**
→ Detalle: [docs/planteamiento_problema.md](docs/planteamiento_problema.md)

## Justificación (valor público)

El dato bien gobernado es infraestructura. Al corte del 2026-07-10, **el 71 % del
catálogo está desactualizado frente a la frecuencia que su propia entidad declaró** —
un incumplimiento invisible hasta ahora porque no existía la herramienta que lo
mostrara. DatosVivos convierte ese punto ciego en un indicador gestionable por
entidad, sector y territorio, y elimina la barrera técnica para consultar el dato
público. Se alinea con las Hojas de Ruta de Datos Abiertos Estratégicos y fortalece la
apropiación ciudadana del ecosistema digital (objetivo del Reto 7).

## Cantidad de datasets utilizados

**25.192 datasets** de **1.423 entidades** (corte 2026-07-10 — el catálogo se
re-ingesta automáticamente a diario, las cifras varían). Nivel Avanzado: integración
masiva de fuentes heterogéneas, no un análisis de dataset único.

## Datasets utilizados de datos.gov.co

- **El catálogo completo del portal nacional**: 12.101 datasets vía Socrata Discovery
  API + SODA + Metadata API (8.458 nativos consultables en línea).
- **DIVIPOLA — Codificación de municipios** (`gdxc-w37w`, DANE): referencia canónica
  territorial para la inferencia geográfica y el mapa por departamento.
- Cualquier dataset tabular nativo es consultable en vivo desde el buscador (matrícula,
  contratación, vacunación, etc.) — el motor ejecuta la consulta sobre su API SODA.

## Datasets utilizados externos

Portales integrados por harvesting directo y atribución de origen:
**IGAC / Colombia en Mapas** (6.622) · **Datos Abiertos Bogotá** (4.304, CKAN) ·
**Datos Abiertos Cali** (1.236, CKAN) · **MEDATA Medellín** (823, DCAT) ·
**Datos Abiertos Valle del Cauca** (106, CKAN).
→ Detalle y mecanismos: [docs/fuentes_datos.md](docs/fuentes_datos.md)

## Variables seleccionadas

**29 variables curadas por dataset** en la vista `v_dataset_status_decisor` (fuente
única del tablero y del panorama): identidad y publicador, **semáforo de frescura**
(`status`, calculado contra la frecuencia declarada), uso (descargas/vistas), acceso
(`directo` / `requiere_herramienta` / `solo_metadatos`), procedencia, territorio
(DIVIPOLA) y calidad (`quality_flag`).
→ Diccionario completo: [docs/diccionario_datos.md](docs/diccionario_datos.md)

## Tipo de análisis

- **Descriptivo del ecosistema**: panorama nacional en vivo (composición, frescura,
  acceso, sectores, territorio, portales) + tablero exploratorio Power BI.
- **IA generativa aplicada (agente de servicios públicos)**: consultas ciudadanas en
  lenguaje natural resueltas con **NL2SQL / Text-to-SQL verificado** sobre los datos
  reales; clasificación automática de calidad; inferencia territorial.

## Modelo utilizado

Organizado por nivel del producto (nivel avanzado del TDR):

- **En los tableros** — IA para la **depuración, consolidación y definición de casos de
  calidad de datos**: clasificación de reportes administrativos (Ley 1712), curación de
  columnas con LLM + heurísticas, inferencia territorial DIVIPOLA, guardas anti-basura,
  consolidación de 6 portales con 3 protocolos.
- **En el buscador** — **motor NL2SQL generativo con verificación determinista de 3
  capas** (genera con LLM viendo solo columnas curadas reales; verifica con código
  antes de ejecutar; repara o rehúsa): embeddings `multilingual-e5` + ChromaDB para
  retrieval semántico, clasificador de intención, narrativa anti-alucinación (cero
  cifras inventadas) y **MCP server** que expone las herramientas a cualquier agente de IA.
- Backend LLM conectable: **producción con la API de Claude (Haiku)** desde 2026-07-11 — interpretación NL en ~1.5 s (antes 31-45 s con modelo local); `LLM_BACKEND=ollama` queda para réplicas sin API key.
→ Metodología CRISP-ML adaptada: [docs/marco_metodologico.md](docs/marco_metodologico.md)

## Por qué Nivel Avanzado (con la letra del TDR)

| El TDR (Nivel Avanzado) exige | DatosVivos lo cumple con |
|---|---|
| **Agentes de IA para servicios públicos** que consulten y procesen datos abiertos automáticamente | El agente consulta, cruza y procesa el catálogo para responder solicitudes ciudadanas |
| **IA generativa** para asistentes y **sistemas conversacionales basados en datos abiertos** | Buscador en lenguaje natural con motor **NL2SQL / Text-to-SQL** generativo verificado |
| **Modelos de lenguaje** y **arquitecturas híbridas** | LLM + verificación determinista de 3 capas ("la IA razona, el motor verifica") + embeddings neuronales de retrieval |
| **Integración de grandes volúmenes de datos**, múltiples fuentes | **25.192 datasets** de 6 portales y 3 protocolos (Socrata, CKAN, DCAT) — muy por encima de los 3-10 conjuntos del nivel intermedio |
| **Datos estructurados y no estructurados** | Metadata estructurada + texto libre (títulos, descripciones) procesado con embeddings y clasificadores |
| Más variables que el nivel intermedio (10-20) | **29 variables curadas por dataset** en la vista analítica (sobre 42 columnas fuente) |
| **Automatización, escalabilidad y despliegue funcional** | Actualización diaria automática, arquitectura agnóstica del portal, **en producción** en datosvivos.co |
| IA **pertinente, aplicable, interpretable y con aporte real** (no superficial) | Cada componente de IA resuelve un problema concreto y es auditable: la verificación es código, la clasificación es reproducible, cada cifra cita su fuente |

## Resultados clave

1. **Integración única**: nadie más consolida los portales federados territoriales de
   Colombia en un catálogo comparable.
2. **El hallazgo**: 71 % del catálogo "en rojo" (desactualizado frente a su propia
   promesa de frecuencia). Solo 9 % al día.
3. **Actualización diaria automática**: el panorama se cura solo (ETL nocturno +
   harvesting semanal + clasificación continua). Ninguna cifra del sitio está quemada.
4. **Cero cifras inventadas**: verificación determinista + citación de fuente en cada
   respuesta del buscador.
5. **Calidad medida**: 17/18 columnas al 100 % de fidelidad contra la fuente; ~89 % de
   cobertura territorial inferida; **100 % de cobertura de categoría temática** (2.504
   huecos cerrados con clasificación semántica + curación revisada; vocabulario
   consolidado de 60+ etiquetas redundantes a 25 canónicas).
6. **Bodega local en Parquet**: los datasets más valiosos del catálogo (prioridad
   determinista "valor por GB": uso real + engagement + frescura ÷ tamaño) se descargan
   a disco de la infraestructura y **el buscador responde desde la copia local en
   milisegundos** cuando el snapshot está fresco; si la fuente cambió, cae al dato vivo.
   Una regla diaria de cola (entra-uno-sale-uno) la mantiene actualizada sola.

## Interpretación

La brecha del dato abierto colombiano no es de cantidad sino de **gobernanza y
acceso**: los datos existen, pero no se mantienen frescos y consultarlos exige
capacidades técnicas. Medir contra la promesa de cada entidad convierte la percepción
en indicador gestionable. → [docs/conclusiones.md](docs/conclusiones.md)

## Impacto potencial

| Actor | Qué le cambia |
|---|---|
| Entidad publicadora | Ve en segundos cuántos datasets tiene y cuántos al día |
| Gerente / cabeza de sector | Control consolidado de sus entidades adscritas |
| MinTIC / política pública | Panorama nacional medible para las Hojas de Ruta |
| Ciudadanía | Cifras verificables en lenguaje natural, sin barrera técnica |

Escalable: agregar un portal CKAN es configuración; el patrón aplica a cualquier país
con catálogos Socrata/CKAN/DCAT; el MCP server permite construir encima.

## Solución en Producción (Demo en Vivo)

Para ver y probar la solución funcionando en tiempo real:

**Aplicación Web / Producción:** [https://datosvivos.co](https://datosvivos.co)
· [Tablero del decisor](https://datosvivos.co/tablero)
· [Buscador en lenguaje natural](https://datosvivos.co/buscar)

**API pública de estadísticas (verificación en vivo):**
[`/api/v1/stats/panorama`](https://datosvivos.co/api/v1/stats/panorama) ·
[`/api/v1/dashboard/datasets_decisor.csv`](https://datosvivos.co/api/v1/dashboard/datasets_decisor.csv)

## Enlaces de acceso

Presentación del proyecto:

*   [Descargar archivo original (.PPTX)](recursos/presentacion.pptx) — *Para abrir y editar en PowerPoint.*
*   [Ver presentación en línea (.PDF)](recursos/presentacion.pdf) — *Abre el visor interactivo de GitHub o GitLab.*
*   [Descarga directa (.PDF)](recursos/presentacion.pdf?raw=true&inline=false) — *Fuerza la descarga en ambas plataformas.*

## Documentación

| Documento | Contenido |
|---|---|
| [Planteamiento del problema](docs/planteamiento_problema.md) | El dolor del decisor y la pregunta problema |
| [Marco metodológico](docs/marco_metodologico.md) | CRISP-ML(Q) adaptado, fase a fase |
| [Fuentes de datos](docs/fuentes_datos.md) | Los 6 portales integrados, mecanismos y licencias |
| [Diccionario de datos](docs/diccionario_datos.md) | Las 29 variables + contratos de la API |
| [Arquitectura](docs/architecture.md) | El sistema completo (3 capas) |
| [Conclusiones](docs/conclusiones.md) | Resultados, interpretación, impacto, límites |
| [Guía de validación](docs/validation_guide.md) | Cómo replicar y auditar (jurado) |
| [Decisiones de arquitectura (ADRs)](docs/adr/) | Trazabilidad de cada decisión técnica |

## Roadmap (trabajo futuro)

1. **Casos de consulta verificados sobre la bodega** — la cosecha (bodega Parquet
   con regla diaria) y la catalogación (100 % de categorías) ya están en producción;
   falta el perfilado con casos de consulta generados y verificados por el motor para
   un retrieval aún más preciso.

## Equipo

**GIT TIC — Agencia Nacional de Infraestructura (ANI)**: Hernán Darío Gutiérrez Casas
(líder estratégico) · Ileana Andrea Navarro Castrillón (líder de equipo y
comunicaciones) · Jhonatan Sneider Rico Pinto (líder técnico y de datos).

## Licencia

Código abierto para validación y reutilización en el marco del concurso. Los datos
consultados son públicos, publicados por sus entidades bajo las licencias declaradas
en cada portal.
