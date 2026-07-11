# ADR-021: Sistema de diseño alineado con gov.co (entidad pública moderna)

**Estado:** Aceptada
**Fecha:** 2026-06-24
**Supersede:** [ADR-012](./012-civic-editorial-design-system.md) (Civic Editorial)

## Contexto

DatosVivos corría bajo *Civic Editorial* (ADR-012): IBM Plex Serif/Sans/Mono,
fondo papel-crema `#F3EFE3`, acentos granate/ámbar, formas hairline. Bello, pero
en la práctica leía como **periodismo de datos / think-tank**, no como un servicio
oficial del Estado — y esa estética editorial-minimal se confundía con el look
genérico "hecho por IA" que el proyecto quería evitar desde el principio.

DatosVivos **es** una propiedad del Estado colombiano (datos.gov.co, ANI, concurso Datos al
Ecosistema 2026 de MinTIC). Para el ciudadano, *parecerse a gov.co* es señal directa de legitimidad y
confianza. Colombia tiene un **Sistema de Diseño gov.co** oficial (Kit UI v9.2,
MinTIC) con paleta y tipografía definidas.

## Decisión

Adoptar una identidad visual de **entidad pública moderna alineada con gov.co**.
Elementos:

- **Tipografía:** **Nunito Sans** (oficial gov.co) para títulos y cuerpo,
  self-hosted woff2 (sin Google Fonts CDN). Se conserva **IBM Plex Mono** para datos
  tabulares, IDs y SoQL. Se **elimina IBM Plex Serif** (firma editorial).
- **Color:** superficie blanca + **azul institucional gov.co** `#004884` (texto/
  enlaces/header) y **azul interactivo** `#3366CC` (rellenos). Semánticos gov.co
  para el semáforo de frescura del catálogo: verde `#068460`, dorado `#FFAB00`,
  rojo `#F42F63` (texto-seguro `#C32D4B`).
- **Estructura institucional:** barra superior tipo **GovHead** con atribución
  **textual** del Estado ("República de Colombia · Datos abiertos del Estado");
  header sólido azul; footer institucional con borde superior de acento.
- **Formas:** se introduce escala de radius (`4/8/12px`) — tarjetas y botones con
  esquina suave, CTA primario **sólido** (la acción principal manda, patrón Kit UI).
- **Wordmark:** `Datos|Vivos` se conserva (es identidad de producto, no de gov.co),
  ahora en Nunito Sans ExtraBold con pleca en azul institucional, + `── datos.gov.co`.
- **Restricción dura — sin marcas protegidas:** se usa el *registro visual* del
  Estado (color, tipografía, estructura, atribución textual) pero **NO** el logo
  gov.co, el escudo nacional ni el lockup oficial. No estamos habilitados para
  exhibirlos. "República de Colombia" es texto, no marca.
- **Accesibilidad intacta:** se conservan los **5 modos** (claro/oscuro/alto contraste
  ×2/auto), la escala tipográfica del A11yPanel, los patrones SVG para daltonismo y
  el anti-FOUC. La paleta gov.co se re-deriva en cada modo con contraste validado.

Definición operativa completa en [`docs/BRAND.md`](../BRAND.md) (reescrito).

## Razón

- **Legitimidad sobre diferenciación.** ADR-012 descartó esta dirección ("Civic
  Modern") por *"poco diferenciada, cercana a gob.uk"*. Reevaluado con el dueño del
  producto (2026-06-24): para un servicio del Estado, parecerse al estándar gov.co
  **es** el objetivo, no un defecto. La diferenciación la da el producto (agente
  conversacional sobre datos), no la piel.
- **Despegarse de la estética IA.** Alinearse con la imagen real del Estado es lo
  que más aleja el producto del look genérico "hecho por v0/Bolt".
- **Aprovechar el Hito R.** Los semánticos gov.co (verde/dorado/rojo) calzan exacto
  con el semáforo de frescura que hoy solo vivía en PowerBI; ahora es señal ciudadana.

## Trade-off

- **Se pierde calidez/distinción editorial.** Riesgo de verse como cualquier portal
  gov. Asumido conscientemente a cambio de legitimidad.
- **Migración de marca.** Reescribir `BRAND.md`, re-derivar tokens en 5 modos,
  restilar 34 componentes + 7 rutas. Mitigado: los **nombres de tokens se conservan**
  (cambian valores), así que la mayoría de componentes heredan vía CSS vars.
- **Contraste del azul interactivo.** `#3366CC` sobre blanco ≈5.4:1 (pasa AA); aún así
  el texto-enlace primario usa `#004884` (~9.3:1) por margen. Validado por modo.

## Referencias

- [`docs/BRAND.md`](../BRAND.md) — documento operativo reescrito, fuente de verdad.
- [ADR-012](./012-civic-editorial-design-system.md) — sistema superado.
- Sistema de Diseño gov.co / Kit UI v9.2 (MinTIC) — paleta y tipografía oficiales.
- `web/src/styles/tokens.css`, `web/src/styles/globals.css` — implementación.
