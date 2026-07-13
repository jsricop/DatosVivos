# ADR-023: Home "Panorama primero" — arquitectura de información para tomadores de decisiones

**Estado:** Aceptada
**Fecha:** 2026-07-10
**Relacionada:** [ADR-021](./021-sistema-diseno-gov-co.md) (sistema visual gov.co — sigue
vigente íntegro), [ADR-017](./017-arquitectura-hibrida-ia-determinista.md) (chips como entrada
estructurada del buscador — sigue vigente, se reubica a `/buscar`), enmienda ADR-014
(tablero Power BI público sin login).
**Modifica:** `BRAND.md` §1.2, §9.1 y §11.6 (este ADR es la justificación documentada).

## Contexto

DatosVivos nació "buscador primero": la home era una caja de lenguaje natural + chips, y la
analítica del catálogo vivía escondida (primero tras login, luego en `/tablero` como página
secundaria). Dos hechos cambiaron el peso relativo de las piezas:

1. **El tablero Power BI maduró** (spec: `docs/powerbi/GUIA_PowerBI_DatosVivos.pdf`): 4 páginas — salud
   del catálogo, engagement, por entidad, cobertura territorial — con slicers por
   `acceso_datos`, `entity_name`, `category`, `sector`, `quality_flag`. Está diseñado
   explícitamente **para un tomador de decisiones por sector o entidad**, y desde 2026-07-10
   es público (publish-to-web, sin login).
2. **El catálogo curado es el activo más valioso del proyecto**: ~25k datasets con semáforo
   de frescura, acceso, sector y jurisdicción DIVIPOLA — información de panorama que ningún
   otro sitio ofrece agregada, y que la home actual no mostraba (solo 4 KPIs sueltos).

Decisión del dueño (2026-07-10): invertir el concepto. Quien llega a `datosvivos.co` debe ver
**el panorama de los datos abiertos a nivel nacional** — cuántos datasets hay, cuántas
entidades publican, en qué sectores, en qué departamentos, qué tan frescos están y cómo se
accede a ellos — antes que una caja de búsqueda.

## Decisión

**Arquitectura de información de 3 niveles**, de lo general a lo puntual:

| Nivel | Ruta | Pregunta que responde | Audiencia primaria |
|---|---|---|---|
| 1. Panorama | `/` | ¿Cómo está el ecosistema de datos abiertos de Colombia? | Tomador de decisiones, prensa, ciudadanía |
| 2. Detalle | `/tablero` | ¿Cómo está MI sector / MI entidad / MI territorio? | Tomador de decisiones por sector/entidad |
| 3. Dato puntual | `/buscar` | ¿Cuál es la cifra exacta que necesito? | Ciudadano, periodista, analista |

Reglas que se derivan:

1. **La home es 100% panorama.** KPIs y gráficas en vivo (endpoint
   `GET /api/v1/stats/panorama` sobre `v_dataset_status_decisor` + `datasets`). La búsqueda
   se reduce a un CTA hacia `/buscar`; el detalle segmentado, a un CTA hacia `/tablero`.
2. **No-duplicación con Power BI.** La web muestra **agregados nacionales** (una cifra por
   dimensión: sector, departamento, semáforo, acceso). El corte interactivo por
   entidad/slicers vive SOLO en `/tablero`. Si una gráfica de la home necesita un filtro,
   está en el nivel equivocado.
3. **El buscador no pierde nada:** los chips de sector, "Lo más consultado" y el constructor
   avanzado se reubican al estado vacío de `/buscar`. ADR-017 (chips deterministas) sigue
   siendo la arquitectura del buscador; solo cambia su posición en la jerarquía.
4. **Titular de la home:** deja de ser el tagline. Pasa a un titular de panorama
   ("El panorama de los datos abiertos de Colombia"); el tagline "Datos del Estado, en tus
   palabras." se conserva como línea de marca (kicker) — sigue siendo el tagline oficial del
   producto (BRAND §7.3 no cambia).

### Animación de revelado de datos (excepción acotada a BRAND §11.6)

La blacklist prohibía toda "animación de aparición". Se mantiene la prohibición en el flujo
de búsqueda/resultados (la respuesta a una consulta no se "presenta", se entrega). Se abre
una **excepción única para la home panorama**: animación de *revelado de datos* — count-up
de KPIs, crecimiento de barras (`scaleX`), fade del mapa — bajo estas condiciones:

- Ocurre **una sola vez**, al entrar el elemento al viewport (IntersectionObserver).
- Duración ≤ 800ms, easing estándar del sistema.
- `prefers-reduced-motion` la **anula por completo** (tokens ya colapsan `--duration-*` a 0).
- El valor final está siempre en el HTML server-rendered: la animación revela, nunca es
  requisito para ver el dato (sin JS se ve la cifra completa).
- Nada de spring/bounce/parallax/stagger decorativo. El movimiento comunica magnitud, no adorna.

### Universo de conteo del panorama

**Enmienda 2026-07-10 (decisión del dueño, mismo día):** la línea editorial va sobre el
**catálogo COMPLETO** — el `total` del panorama coincide con `GET /stats/catalog`. La
división entre **datos temáticos** y **reportes administrativos** (Ley 1712: registros de
activos, esquemas de publicación, índices) no es un filtro previo sino **una gráfica más**
del panorama (`composicion`), visible y explicada en lenguaje llano. Razones: (a) el
tamaño real del catálogo integrado es parte del mensaje; (b) ocultar ~3k datasets tras un
filtro invisible generaba cifras "que no cuadran" con otras fuentes (pasó con el conteo de
entidades: 1.011 útiles vs 1.423 totales).

Además el panorama muestra **por_portal** (datos.gov.co + Bogotá + Cali + Medellín/MEDATA +
Valle del Cauca): la integración de portales federados territoriales es trabajo
diferenciador del proyecto y debe ser visible, no un detalle de infraestructura.

## Consecuencias

- (+) El activo más valioso (catálogo curado con semáforo/geo/sector) es lo primero que se ve.
- (+) El tablero Power BI deja de ser un anexo: es el nivel 2 explícito de la navegación.
- (+) La home carga de un solo fetch cacheado (TTL 5 min server-side); sin JS muestra cifras.
- (−) La home depende de la API para sus cifras → degradación obligatoria (sin crash, texto
  "cifras no disponibles") cuando la API no responde.
- (−) BRAND.md §1.2 ("No es un panel ejecutivo") quedó obsoleto en su literalidad y se
  reescribe: la home ES un panorama ejecutivo nacional; lo que sigue sin ser DatosVivos es
  un dashboard *promocional* (cifras sin fuente ni semántica auditable).
- Restricción respetada: **cero cambios** a esquema, ETL o vistas. El endpoint nuevo es
  lectura pura.
