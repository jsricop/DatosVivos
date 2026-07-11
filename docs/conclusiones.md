# Conclusiones — resultados, interpretación e impacto

> Cifras al corte del **2026-07-10**; el catálogo se actualiza automáticamente a
> diario y los valores varían. Verificable en vivo en
> [datosvivos.co](https://datosvivos.co).

## Resultados clave

1. **Integración única del ecosistema**: 25.192 datasets de **6 portales** (datos.gov.co,
   IGAC/Colombia en Mapas, Bogotá, Cali, MEDATA, Valle del Cauca) consolidados en un
   solo catálogo comparable, con 1.423 entidades publicadoras. Ningún otro servicio
   integra los portales federados territoriales — hoy hay que revisarlos sitio por sitio.
2. **El hallazgo accionable**: el **71 % del catálogo está "en rojo"** — desactualizado
   frente a la frecuencia que su propia entidad declaró (17.948 datasets). Solo el 9 %
   está al día. Esta cifra, invisible hasta ahora, es el punto de partida de cualquier
   política de mejora del dato abierto.
3. **Actualización diaria automática**: el panorama no es una foto — se cura solo.
   ETL nocturno + harvesting semanal + clasificación de calidad re-ejecutada en cada
   corrida. Las cifras del sitio son en vivo; ninguna está quemada en el código.
4. **Motor NL2SQL verificado en producción**: el ciudadano pregunta en lenguaje natural
   y recibe cifras calculadas sobre las filas reales del dataset citado, con
   verificación determinista de 3 capas y política de **cero cifras inventadas** (si no
   se puede verificar, se rehúsa la respuesta).
5. **Calidad de datos con IA, medida**: 17/18 columnas al 100 % de fidelidad contra la
   fuente (auditoría column-by-column), clasificación automática de 2.996 reportes
   administrativos (Ley 1712), inferencia territorial DIVIPOLA con ~89 % de cobertura,
   y guardas contra metadata basura.
6. **Interoperabilidad**: las herramientas del motor expuestas como **MCP server** —
   cualquier agente de IA puede consultar el catálogo colombiano de forma estándar.

## Interpretación

- La brecha del dato abierto en Colombia no es de **cantidad** (25 mil datasets) sino
  de **gobernanza y acceso**: los datos existen pero no se mantienen frescos, y
  consultarlos exige capacidades técnicas que la mayoría no tiene.
- El semáforo demuestra que **medir cambia la conversación**: al comparar cada dataset
  contra la promesa de su propia entidad (su frecuencia declarada), el incumplimiento
  deja de ser una percepción y se vuelve un indicador gestionable por entidad y sector.
- La heterogeneidad de los portales (Socrata/CKAN/DCAT, metadata desigual) es el costo
  oculto de la federación; la consolidación con IA (curación, clasificación,
  inferencia) lo absorbe una sola vez para todos los usuarios.

## Impacto potencial

| Actor | Qué le cambia |
|---|---|
| **Entidad publicadora** | Ve en segundos cuántos datasets tiene, cuántos al día y dónde está su rezago |
| **Cabeza de sector / gerente** | Control consolidado de sus N entidades adscritas (tablero por sector/entidad) |
| **MinTIC / política pública** | Panorama nacional medible para las Hojas de Ruta de Datos Abiertos Estratégicos |
| **Ciudadanía, prensa, academia** | Cifras verificables en lenguaje natural, sin barrera técnica, con fuente citada |

Escalabilidad: la arquitectura es agnóstica del portal (agregar un portal CKAN nuevo es
configuración, no desarrollo); el patrón aplica a cualquier país con catálogos Socrata/
CKAN/DCAT; y el MCP server permite que terceros construyan encima sin tocar el sistema.

## Limitaciones honestas

- El semáforo depende de la **frecuencia declarada** por cada entidad; donde la
  declaración es irreal, el color hereda ese sesgo (la medición sigue siendo útil:
  expone también la calidad de la declaración).
- Los portales federados no reportan métricas de uso (descargas/vistas) — esos campos
  quedan explícitamente como "no reporta", nunca imputados.
- El motor NL2SQL prioriza **no equivocarse** sobre responder siempre: hay preguntas
  que rehúsa cuando la verificación no alcanza el umbral. Es una decisión de diseño.

## Trabajo futuro (el pendiente)

> La migración del LLM a la API de Claude se **ejecutó el 2026-07-11** (backend
> intercambiable `LLM_BACKEND=anthropic`, modelo Haiku): la interpretación de lenguaje
> natural pasó de 31-45 s a **1.5-1.8 s** con mapeos correctos, y la baja del modelo
> local liberó 6.2 GB de disco en la infraestructura para la bodega de datasets.

1. **Cosecha y catalogación previa de datasets** para búsqueda más eficiente: descargar
   y perfilar los datasets tabulares (describe + casos de consulta comunes generados y
   **verificados por el motor** — solo sobreviven los que producen cifra verificada),
   construyendo un set etiquetado para retrieval de mayor precisión.
