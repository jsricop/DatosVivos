# BRAND.md — DatosVivos

> Documento canónico de identidad visual, voz y sistema de diseño de DatosVivos. Toda decisión de marca empieza aquí. Si algo en `/web` contradice este documento, gana el documento; el código se corrige. Si la realidad de uso obliga a cambiar el documento, se cambia primero aquí y luego en el código — nunca al revés.

**Lente:** este documento sirve a tres audiencias, pero la decisión la dirige una sola.

| Lente | Para quién | Qué encuentra |
|---|---|---|
| Para el jurado MinTIC | Evaluadores del concurso | Justificación de cada elección estética, alineación con accesibilidad (Ley 1618, WCAG 2.1 AA), evidencia documental. |
| Para ciudadanos técnicos | Diseñadores, devs frontend, contribuidores | Tokens, componentes, reglas operativas, lista negra. |
| Para ciudadanía general | Cualquier persona | Manifiesto, voz, tono, qué es y qué no es DatosVivos. |

**Audiencia número 1 de la marca:** ciudadanía general colombiana sin contexto técnico. El resto leemos por encima del hombro.

---

## 1. Manifiesto

### 1.1 Qué es DatosVivos

DatosVivos es un **agente civil de datos del Estado colombiano**. El ciudadano pregunta en su idioma — el del barrio, el del trabajo, el del periódico — y el agente responde ejecutando consultas reales sobre `datos.gov.co`. Cada cifra que aparece está calculada con `pandas` a partir de filas verdaderas; cada respuesta cita el dataset que la sustenta con un enlace clicable. El motor LLM corre localmente en una máquina del Estado.

### 1.2 Qué NO es DatosVivos

- **No es un chatbot.** No tiene personalidad inventada, no se llama por un nombre humano, no usa emojis para parecer "amigable". Es una herramienta de búsqueda con narrativa.
- **No es un asistente "inteligente".** Si no encuentra datasets relevantes, lo dice. No improvisa, no inventa entidades, no estima cifras que no existen.
- **No es un panel ejecutivo.** No vende dashboards. Devuelve respuestas y permite al ciudadano verificar la fuente.
- **No es un sitio promocional del Estado.** Es infraestructura cívica neutral; no celebra ni critica políticas — solo entrega los datos públicos.

### 1.3 Voz y tono

- **Segunda persona singular informal** (`tú` / `tu pregunta`), por defecto. Excepción: si la consulta es claramente formal o territorial, el sistema mantiene `usted` cuando el LLM lo sugiere para el contexto. Nunca mezclar en una misma respuesta.
- **Español neutro colombiano.** Sin localismos opacos ("chévere", "berraco"), sin neutro ibérico ("vale", "vosotros"). Léxico que un periodista de El Tiempo o La Silla Vacía firmaría.
- **Frases cortas.** Una idea por oración. Si una oración necesita una coma compleja, mejor dos oraciones.
- **Sin anglicismos evitables.** `dataset` se mantiene (es nombre técnico del dominio Socrata). Prohibidos: *insight*, *workflow*, *feature*, *parsear*, *trackear*, *deploy*, *fixear*. Sus equivalentes en español: hallazgo, flujo, funcionalidad, analizar, registrar, desplegar, corregir.
- **Honestidad sobre el alcance.** Si los datos del catálogo no responden la pregunta, se dice. Se sugiere qué dataset podría servir, no se inventa una cifra.
- **Sin marketing.** No hay "el mejor", "el más avanzado", "potenciado por IA". Lo único que se proclama son los hechos verificables.

Tres anclas léxicas que el sistema usa con consistencia:

- **"Datos verificados"** — siempre que se introduce el bloque de cifras calculadas con pandas.
- **"Fuentes consultadas"** — siempre que se introducen las citas con enlace al dataset.
- **"No encontré datasets relevantes"** — mensaje fijo cuando el resultado es vacío. Nunca variar.

### 1.4 Tres pilares declarados

Ligan a las promesas Beta-1 (`README.md` §"Garantías para el ciudadano"):

1. **Soberanía** — el modelo corre en una máquina del Estado. Las preguntas no salen del servidor.
2. **Verificabilidad** — cada cifra es reproducible. Cada dataset citado es clicable.
3. **Interoperabilidad** — el motor también se expone como MCP server estándar (cualquier cliente compatible puede consumirlo).

La interfaz visual debe reforzar estos tres pilares, no decorarlos.

---

## 2. Flujo de uso

### 2.1 Flujo principal

```
   ┌──────────┐    ┌────────────┐    ┌─────────────┐    ┌──────────────┐
   │  HOME    │ ─▶ │  BUSCAR    │ ─▶ │  RESULTADO  │ ─▶ │  VERIFICAR   │
   │  /       │    │  /buscar   │    │  /buscar?…  │    │  /dataset/…  │
   └──────────┘    └────────────┘    └─────────────┘    └──────────────┘
        │                                  │                    │
        │                                  ▼                    ▼
        │                          ┌──────────────┐    ┌──────────────┐
        │                          │  COMPARTIR   │    │  JSON SODA   │
        │                          │  (URL)       │    │  (externo)   │
        │                          └──────────────┘    └──────────────┘
        │
        └───────── bucle lateral permanente ─────────┐
                                                     ▼
                                          ┌────────────────────┐
                                          │  /accesibilidad    │
                                          │  modo · voz · tipo │
                                          └────────────────────┘
```

### 2.2 Reglas del flujo

- **El estado de la búsqueda vive en la URL.** `/buscar?q=cuantos+colegios+en+boyaca&tema=educacion&territorio=boyaca` es compartible y bookmarkable. No hay estado oculto en `sessionStorage` para la consulta.
- **No hay modal de "espera, estamos pensando".** La latencia (30-90s) se muestra como progreso explícito con eventos SSE: `Clasificando intención → Buscando datasets → Ejecutando consulta → Calculando cifras → Redactando narrativa`. Cada etapa visible.
- **Verificar es un click, no un menú.** Cada cita de dataset es un enlace que abre `/dataset/{id}` en la misma pestaña; el enlace al JSON SODA externo se abre en pestaña nueva.
- **Accesibilidad es global, no una página aparte para "quienes la necesitan".** El toggle de modo de color y el control de voz están siempre disponibles desde el header. La página `/accesibilidad` documenta y centraliza, no es la única puerta.

---

## 3. Sistema de color

Tres modos. Mismos nombres de token. Distinta tabla de valores. El usuario escoge; el default es **claro/papel**.

### 3.1 Tokens semánticos

| Token | Función |
|---|---|
| `--bg` | Fondo de página |
| `--bg-elev` | Fondo de tarjetas, paneles, drawer |
| `--ink` | Texto principal |
| `--ink-2` | Texto secundario, metadata |
| `--ink-muted` | Texto deshabilitado, placeholders |
| `--hairline` | Bordes, separadores, regletas |
| `--accent` | Acento primario (CTA, links, énfasis editorial) |
| `--accent-2` | Acento secundario (chips activos, badges de tipo de pregunta) |
| `--focus-ring` | Anillo de foco accesible (siempre visible, nunca outline:none) |
| `--danger` | Alertas, errores (rara vez usado; siempre con icono y texto) |

### 3.2 Modo claro / papel (default)

| Token | Hex | Comentario |
|---|---|---|
| `--bg` | `#F3EFE3` | Papel crema. No blanco puro: blanco puro es pantalla, no documento. |
| `--bg-elev` | `#E8E1CE` | Papel envejecido. Contraste suficiente con `--bg` para distinguir paneles sin línea. |
| `--ink` | `#16130E` | Tinta negra cálida. Contraste con `--bg`: 14.3:1 (AAA). |
| `--ink-2` | `#3B342A` | Tinta secundaria. Contraste con `--bg`: 9.1:1 (AAA). |
| `--ink-muted` | `#776A55` | Tinta apagada. Contraste con `--bg`: 4.6:1 (AA). Reservado para placeholders y metadata fina. |
| `--hairline` | `#B7A98B` | Borde sepia. Solo 1.5:1 contraste — su rol es separar, no transmitir información. |
| `--accent` | `#A52A2A` | Granate editorial. Usado en CTA, citas inline `[1]`, énfasis. Contraste con `--bg`: 7.4:1 (AAA). |
| `--accent-2` | `#B8860B` | Ámbar oscuro. Chips activos, badges de tipo de pregunta. Contraste con `--bg`: 4.7:1 (AA normal). |
| `--focus-ring` | `#A52A2A` | Mismo granate, ancho 2px con offset 2px. Siempre visible en `:focus-visible`. |
| `--danger` | `#7A1212` | Granate más oscuro. Contraste con `--bg`: 11.2:1 (AAA). |

### 3.3 Modo oscuro / tinta

| Token | Hex | Comentario |
|---|---|---|
| `--bg` | `#0E0C08` | Tinta profunda cálida. No `#000` puro: el papel "negro" del periódico también es cálido. |
| `--bg-elev` | `#1A1612` | Capa de tarjeta sobre tinta. |
| `--ink` | `#E8E1CE` | Papel sobre tinta. Contraste con `--bg`: 13.8:1 (AAA). |
| `--ink-2` | `#B0A88F` | Papel apagado. Contraste con `--bg`: 8.4:1 (AAA). |
| `--ink-muted` | `#7A7158` | Contraste con `--bg`: 4.6:1 (AA). |
| `--hairline` | `#3B342A` | Borde marrón oscuro. |
| `--accent` | `#C24A4A` | Granate más luminoso (la luz se invierte). Contraste con `--bg`: 5.6:1 (AA). |
| `--accent-2` | `#D4A24A` | Ámbar luminoso. Contraste con `--bg`: 7.9:1 (AAA). |
| `--focus-ring` | `#D4A24A` | Más luminoso que el accent para ser visible sobre fondos oscuros. |
| `--danger` | `#E07070` | Contraste con `--bg`: 6.1:1 (AA). |

### 3.4 Modo alto contraste

Dos variantes que el usuario elige según preferencia. Ambas WCAG 2.1 AAA.

**Variante A — sobre blanco:**

| Token | Hex |
|---|---|
| `--bg` | `#FFFFFF` |
| `--bg-elev` | `#FFFFFF` |
| `--ink` | `#000000` (21:1) |
| `--ink-2` | `#000000` |
| `--ink-muted` | `#333333` (12.6:1) |
| `--hairline` | `#000000` (a 2px en lugar de 1px) |
| `--accent` | `#0033A0` (azul ultramar, 9.3:1) |
| `--accent-2` | `#0033A0` |
| `--focus-ring` | `#0033A0` |
| `--danger` | `#9B0000` (8.8:1) |

**Variante B — sobre negro:**

| Token | Hex |
|---|---|
| `--bg` | `#000000` |
| `--bg-elev` | `#000000` |
| `--ink` | `#FFFFFF` (21:1) |
| `--ink-2` | `#FFFFFF` |
| `--ink-muted` | `#CCCCCC` (15.9:1) |
| `--hairline` | `#FFFFFF` (a 2px) |
| `--accent` | `#FFD400` (amarillo escolar, 16.1:1) |
| `--accent-2` | `#FFD400` |
| `--focus-ring` | `#FFD400` |
| `--danger` | `#FF6B6B` (5.9:1, AA) |

### 3.5 Reglas operativas

- Todos los tokens se exponen como variables CSS bajo `:root[data-theme="light|dark|contrast-light|contrast-dark"]`.
- **Prohibido** usar cualquier color de la paleta default de Tailwind. Las clases Tailwind se basan exclusivamente en estos tokens (`bg-paper`, `text-ink`, etc., mapeados vía `@theme`).
- **Prohibido** usar gradientes (lineales o radiales) en cualquier componente productivo. La única excepción autorizada es una hairline degradada `linear-gradient(to right, var(--hairline), transparent)` para separadores asimétricos editoriales.
- **Prohibido** usar opacidad para "deshabilitar". Usar `--ink-muted` y aria-disabled.
- **Verificación obligatoria:** todo token de texto sobre todo token de fondo debe pasar 4.5:1 (normal) o 3:1 (large) en su modo correspondiente. Script CI valida.

---

## 4. Tipografía

### 4.1 Familias

Tres familias, una sola familia tipográfica de origen — **IBM Plex**. Libre, latín extendido completo, mantenida activamente, sin asociación con AI tooling.

| Familia | Uso | Pesos |
|---|---|---|
| **IBM Plex Serif** | Display, h1, h2, citas largas, query echo en `/buscar` | 400 (regular), 600 (semibold) |
| **IBM Plex Sans** | Body, h3-h6, UI controls, narrativa pandas | 400, 500, 600 |
| **IBM Plex Mono** | Data, IDs de dataset, SoQL citado, kickers de chip (`TEMA`, `TIPO`), números en tablas | 400, 500 |

Las tres se sirven **self-hosted** desde `web/public/fonts/` en formato `woff2` con `next/font/local`. Subset latin-ext. Prohibido cargar fuentes desde Google Fonts CDN u otros CDN externos (requisito de privacidad ciudadana).

### 4.2 Escala tipográfica

Tamaños fluidos con `clamp()` para que escalen con el viewport sin breakpoints duros.

| Nivel | Familia | Tamaño | Line-height | Peso |
|---|---|---|---|---|
| Display XL | Serif | `clamp(2.75rem, 5.5vw, 4.5rem)` | 1.05 | 600 |
| h1 | Serif | `clamp(2.25rem, 4vw, 3.25rem)` | 1.1 | 600 |
| h2 | Serif | `clamp(1.75rem, 3vw, 2.5rem)` | 1.15 | 600 |
| h3 | Sans | `clamp(1.375rem, 2vw, 1.625rem)` | 1.25 | 600 |
| h4 | Sans | `1.125rem` | 1.3 | 600 |
| body-lg | Sans | `1.125rem` | 1.6 | 400 |
| body | Sans | `1rem` (17px) | 1.6 | 400 |
| body-sm | Sans | `0.9375rem` | 1.5 | 400 |
| caption | Sans | `0.875rem` | 1.45 | 500 |
| kicker | Mono | `0.75rem` | 1 | 500 (uppercase, letter-spacing 0.08em) |
| mono | Mono | `0.9375rem` | 1.5 | 400 |
| data | Mono | `1rem` | 1.4 | 400 (tabular-nums obligatorio en tablas) |

### 4.3 Reglas operativas

- **Ancho de lectura máximo: 72ch** para body en `<article>` y narrativa pandas. Ancho de manifiesto/about: 60ch.
- **Prohibido**: Inter, Roboto, Space Grotesk, SF Pro, Geist, Helvetica, Arial, system-ui, sans-serif sin fallback explícito a Plex.
- **Prohibidos los font-stretch variables y los wave-text effects.**
- Italics en serif para énfasis literario o citas. En sans, peso 500 para énfasis funcional. **Sin underline para énfasis** — underline está reservado a enlaces.
- `font-feature-settings: "ss01", "cv11"` para Plex Sans (variantes circular `g` y `l` straight); `tnum` para Mono y para data tabular.
- Escala de usuario (`A11yPanel`): 90% / 100% (default) / 115% / 130%. Aplicada con `font-size` en `:root` para que `rem` y `clamp` escalen consistentemente.

---

## 5. Tokens de forma y espacio

### 5.1 Border-radius

- `--radius-0`: `0` — botones primarios, cards, tarjetas de dataset, drawer, modales.
- `--radius-1`: `2px` — chips, inputs, badges, controles de tipo de pregunta.
- **Nunca** `--radius-2` (>2px). Prohibido. No hay "pill", no hay "rounded-full".

### 5.2 Borde

- `1px solid var(--hairline)` — separador estándar (regleta).
- `1.5px solid currentColor` — solo iconos SVG.
- `2px solid var(--accent)` — énfasis selectivo: card activa, chip seleccionado, focus-ring.
- `2px solid var(--hairline)` — solo en modo alto contraste (donde el hairline absorbe 2px para ser perceptible).

### 5.3 Grilla y espacio

- Base **4px**. Tokens: `--space-1` 4px, `--space-2` 8px, `--space-3` 12px, `--space-4` 16px, `--space-5` 24px, `--space-6` 32px, `--space-7` 48px, `--space-8` 64px, `--space-9` 96px.
- Contenedor: `max-inline-size: 1200px`; centrado; padding lateral `clamp(16px, 4vw, 48px)`.
- Cuneta de lectura: `max-inline-size: 72ch` para narrativa; `60ch` para about/manifesto.

### 5.4 Sombras

- **Prohibidas** las box-shadow con blur. Sin elevation Material. Sin "soft shadows" Apple.
- Permitida: `box-shadow: 0 1px 0 var(--hairline)` — regleta inferior tipo periódico. Esta es la única sombra que existe.
- Para indicar foco: solo `outline` con `--focus-ring`, ancho 2px, offset 2px. No box-shadow ring.

### 5.5 Transiciones

- Duración estándar: `120ms` (interacciones pequeñas: hover, focus, chip toggle).
- Duración expansión/colapso: `200ms`.
- Easing: `cubic-bezier(0.4, 0, 0.2, 1)` (Material standard easing — el único elemento Material que sobrevive).
- **Prohibido**: animaciones de aparición (fade-up, slide-in), spring, lottie, parallax, smooth-scroll forzado.
- Si `prefers-reduced-motion: reduce`, todas las transiciones colapsan a `0ms` excepto las que comunican estado (un fade de 80ms en cambio de tema, por ejemplo).

---

## 6. Iconografía

### 6.1 Política

- **Cero emojis.** En ninguna parte de la UI productiva. Ni en placeholders, ni en mensajes de estado, ni en alt-text, ni en commits que produzcan UI visible.
- Iconos propios en `web/public/icons/`, SVG con `stroke="currentColor"`, `viewBox="0 0 24 24"`, `stroke-width="1.5"`, `stroke-linecap="square"`, `stroke-linejoin="miter"`, sin `fill` (siempre outline).
- **Prohibidos**: íconos rellenos, íconos con gradientes, íconos con sombras, sets pre-hechos (Material Icons, Feather, Lucide) sin re-trazar al stroke 1.5px square.

### 6.2 Set MVP (16 iconos obligatorios)

| Nombre | Uso |
|---|---|
| `search` | Botón principal de HeroSearch |
| `filter` | Trigger del FilterPanel |
| `mic` | STT inactivo |
| `mic-off` | STT deshabilitado / no soportado |
| `speaker` | TTS activo |
| `speaker-off` | TTS apagado |
| `map` | Botón "ver en mapa" |
| `table` | Botón "ver tabla cruda" |
| `chart-bars` | Indicador de visualización barras |
| `chart-line` | Indicador de visualización línea |
| `external-link` | Enlaces a `datos.gov.co` y JSON SODA |
| `expand` | Abrir tabla / sección colapsable |
| `collapse` | Cerrar |
| `close` | Cerrar drawer/modal |
| `contrast` | Toggle de modo color |
| `type-size` | Control de tamaño tipográfico |

### 6.3 Glifos tipográficos como decoración

Sustituyen a la iconografía cuando el contexto es textual:

`·` (separador inline) · `—` (em dash, regleta horizontal) · `→` (resultado, navegación) · `↵` (submit, enter) · `▾` (dropdown) · `▸` (acordeón cerrado) · `▾` (acordeón abierto) · `¶` (referencia editorial) · `§` (sección) · `|` (pleca del wordmark)

---

## 7. Wordmark, tagline y firma

### 7.1 Wordmark

`Datos|Vivos`

- La pleca `|` es un carácter ASCII real, no decoración. Es estructura.
- Composición: IBM Plex Serif 600, kerning compacto (`letter-spacing: -0.01em`), color `var(--ink)`.
- La pleca se renderiza en `var(--accent)` (granate) para que actúe como acento editorial.
- No hay logo gráfico separado. El wordmark **es** el logo.

### 7.2 Subtítulo (siempre acompaña al wordmark)

`── datos.gov.co`

- Em-dashes ASCII (`──`) en lugar de un icono. Plex Mono 500, `var(--ink-2)`.
- Función: declara el origen de los datos, sin necesidad de explicación.

### 7.3 Tagline

`Datos del Estado, en tus palabras.`

- Plex Serif 400 italic, tamaño `display-xl` en home, `h2` en `/acerca`, escondido en otras vistas.
- **Inmutable.** Esta es la única promesa que la marca proclama. No se varía estacionalmente.

### 7.4 Firma técnica al pie

Footer minimal en cada vista, Plex Mono `caption`:

```
Agencia Nacional de Infraestructura — Reto #07 MinTIC 2026
Beta. Sin trackers. El modelo corre en una máquina del Estado.
```

---

## 8. Componentes nucleares

Cada componente vive en `web/src/components/`. Documentación contractual: nombre · props mínimas · estados · reglas duras.

### 8.1 `HeroSearch`

- **Props:** `q?: string`, `placeholder: string`, `onSubmit(q): void`, `voiceEnabled: boolean`.
- **Estados:** `idle` · `typing` · `listening` (STT activo) · `loading` (SSE en curso).
- **Reglas:** ancho full-width hasta `--container-max`. Altura `--space-9` (96px). Borde inferior `1px solid var(--hairline)` cuando idle, `2px solid var(--accent)` cuando focused. Botón submit dentro del campo, a la derecha, glifo `↵` + label "Buscar" (no solo icono). Placeholder rota cada 6s entre 5 preguntas reales ejemplares (cargadas desde `/api/v1/popular`).

### 8.2 `Chip`

- **Props:** `label: string`, `kicker?: string`, `count?: number`, `active: boolean`, `disabled?: boolean`, `onClick(): void`.
- **Estados:** default · hover · focus-visible · active · disabled.
- **Reglas:** padding `8px 14px`, radius `--radius-1` (2px). Borde `1px solid var(--hairline)` default, `2px solid var(--accent)` active (el borde se vuelve más grueso, no cambia el color — invariante de tamaño consistente). Texto Plex Sans 500. Si `kicker` presente, aparece arriba en Plex Mono uppercase tracking. Si `count`, aparece a la derecha en `var(--ink-muted)`.

### 8.3 `ChipGroup`

- **Props:** `axis: "tema" | "tipo" | "territorio" | "entidad"`, `options: ChipOption[]`, `multi: boolean`, `selected: string[]`, `onChange(values): void`.
- **Reglas:** Etiqueta del grupo arriba con kicker mono (`TEMA`, `TIPO DE PREGUNTA`, `TERRITORIO`, `ENTIDAD`). Wrap a líneas múltiples con gap `--space-2`. Para `tipo` (Cuántos/Comparar/Ranking/Tendencia/Mapa), `multi: false`. Para los otros tres, `multi: true`.

### 8.4 `FilterPanel`

- **Props:** `axes: Axis[]`, `selected: Record<Axis, string[]>`, `onChange(...)`, `onClear(): void`.
- **Reglas:** En desktop, sticky a la izquierda del contenido. En mobile, drawer derecho que se abre con botón `filter`. Cada eje colapsable (acordeón). Footer del panel: botones "Limpiar todo" (texto, no botón coloreado) y "Aplicar" (botón `--accent`).

### 8.5 `ResultCard`

- **Props:** `intent: Intent`, `narrative: string`, `citations: Citation[]`, `chart?: ChartData`, `map?: MapData`, `rawRows?: Row[]`, `relatedQuestions: string[]`.
- **Reglas:** No tiene borde lateral; solo regletas superior e inferior `1px solid var(--hairline)`. La narrativa se renderiza dentro de `<article>` con max 72ch. Las citas inline `[1][2]` son `<sup><a>` que enlazan a la tarjeta `DatasetCitation` correspondiente al pie. `rawRows` siempre colapsado por defecto con `<details><summary>Ver tabla cruda</summary>`.

### 8.6 `DatasetCitation`

- **Props:** `index: number`, `entity: string`, `name: string`, `id: string`, `url: string`, `apiUrl: string`, `lastUpdated?: string`.
- **Reglas:** Numeración manual con `[N]` en Plex Mono al inicio (no list-style nativo). Entidad en kicker mono. Nombre del dataset en Plex Serif. ID en Plex Mono color `var(--ink-2)`. Dos enlaces con `external-link`: "ver dataset" → `url`, "JSON SODA" → `apiUrl`.

### 8.7 `DataTable`

- **Props:** `columns: Column[]`, `rows: Row[]`, `pagination?: PaginationOptions`, `downloadCsv?: () => void`.
- **Reglas:** TanStack Table headless. Tipografía Plex Mono para celdas numéricas (con `tnum`), Plex Sans para celdas texto. Zebra striping prohibido — usar regletas `1px solid var(--hairline)` entre filas. Header sticky cuando scroll vertical. Botón "Descargar CSV" en la esquina superior derecha si `downloadCsv` está presente.

### 8.8 `MapBlock`

- **Props:** `geojson: FeatureCollection`, `valueByCode: Record<string, number>`, `colorScale: "sequential" | "diverging"`, `divipolaLevel: "dpto" | "mpio"`, `caption: string`.
- **Reglas:** MapLibre GL JS. Tile base monocromática (custom style basado en Natural Earth, no MapTiler default si requiere ofuscamiento de marca). Choropleth en escala del acento granate (`#A52A2A` con `chroma.js scale`) en modo claro, ámbar en oscuro, ultramar en alto contraste. Leyenda obligatoria abajo. Caption con fuente y fecha bajo el mapa. Alt-text auto-generado por el motor IA — guardado en la prop `altText`.

### 8.9 `ChartBlock`

- **Props:** `type: "bar" | "line" | "scatter"`, `data: ChartData`, `xAxis: AxisSpec`, `yAxis: AxisSpec`, `caption: string`, `altText: string`.
- **Reglas:** Visx headless. Axes con tipografía Plex Mono tnum. Grilla horizontal solo, color `var(--hairline)` opacidad 1 (no semi-transparente). Barras y líneas usan `var(--accent)`. Si hay múltiples series, segunda usa `var(--accent-2)`, tercera y posteriores usan `var(--ink-2)` con dashed (`stroke-dasharray: 4 2`). **Nunca** colores arcoiris / categóricos pastel. Título en Plex Serif arriba; fuente y nota metodológica en Plex Mono caption abajo.

### 8.10 `DisclaimerBeta`

- **Props:** `variant: "inline" | "footer"`.
- **Reglas:** Texto fijo, no editable por dev: *"DatosVivos está en versión Beta-1. Cada cifra que aparece arriba está calculada con `pandas` sobre los datos reales del dataset citado. Si una afirmación parece imprecisa, abre el dataset original y verifícalo."* Estilo: `var(--ink-2)` Plex Sans `body-sm`, separado por regleta superior `1px solid var(--hairline)`.

### 8.11 `ColorModeToggle`

- **Props:** `current: "light" | "dark" | "contrast"`, `onChange(mode): void`.
- **Reglas:** ToggleGroup de Radix con 3 botones, glifos icono + label visible ("Claro", "Oscuro", "Alto contraste"). Persistido en `localStorage` bajo clave `datosvivos:theme`. Aplica `data-theme` en `<html>`. Variante alto contraste tiene sub-selector A/B (sobre blanco / sobre negro) que aparece solo cuando alto contraste está activo.

### 8.12 `A11yPanel`

- **Props:** `state`, `onChange`.
- **Reglas:** Sección lateral o página completa con controles agrupados: ColorModeToggle, escala tipográfica (90/100/115/130%), TTS on/off + selección de voz `es-CO` + velocidad, STT on/off, lista de atajos de teclado (key=Tab navegación, /=focus search, ?=ayuda, M=mute TTS, T=toggle theme).

### 8.13 `Citation` inline

- Etiqueta `<sup><a href="#cita-N">[N]</a></sup>`, color `var(--accent)`, sin subrayado, hover subrayado.

---

## 9. Pantallas — ASCII de referencia

### 9.1 Home `/`

```
┌─────────────────────────────────────────────────────────────────┐
│  Datos|Vivos                              Claro · Oscuro · Alto │
│  ── datos.gov.co                                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│            Datos del Estado, en tus palabras.                   │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  ¿Cuántos colegios públicos hay en Boyacá?         ↵    │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   TEMA                                                          │
│   [ Salud ] [ Educación ] [ Seguridad ] [ Movilidad ]          │
│   [ Justicia ] [ Economía ] [ Medio Ambiente ] [ Vivienda ]    │
│   [ Trabajo ]                                                   │
│                                                                 │
│   TIPO DE PREGUNTA                                              │
│   [ Cuántos ] [ Comparar ] [ Ranking ] [ Tendencia ] [ Mapa ]  │
│                                                                 │
│   TERRITORIO                                                    │
│   [ Nacional ] [ Departamento ▾ ] [ Municipio ▾ ]              │
│                                                                 │
│   ENTIDAD                                                       │
│   [ MinSalud ] [ MinEducación ] [ Policía ] [ DANE ] [ + ]     │
│                                                                 │
│   ─────────────────────────────────────────────────────────    │
│                                                                 │
│   LO MÁS CONSULTADO ESTA SEMANA                                 │
│   1. ¿Tendencia de homicidios en Cali 2018-2024?               │
│   2. ¿Cobertura de vacunación contra fiebre amarilla?          │
│   3. ¿Top 10 municipios con más estudiantes matriculados?      │
│   ...                                                           │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│   ANI — Reto #07 MinTIC 2026 · Beta · Sin trackers              │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 Resultados `/buscar?q=…`

```
┌─────────────────────────────────────────────────────────────────┐
│  Datos|Vivos                              Claro · Oscuro · Alto │
│  ── datos.gov.co                                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TENDENCIA · BOYACÁ · EDUCACIÓN                                 │
│                                                                 │
│  ¿Cuántos colegios públicos hay en Boyacá?         [ Editar ]  │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  En Boyacá hay 2.341 instituciones educativas oficiales         │
│  registradas en el SIMAT (corte abril 2025) [1], distribuidas   │
│  en 123 municipios. El municipio con más instituciones es       │
│  Tunja con 187, seguido de Sogamoso con 142 [2].                │
│                                                                 │
│  ┌─── Gráfico de barras — instituciones por municipio ───────┐  │
│  │  ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒  Tunja            187                  │  │
│  │  ▒▒▒▒▒▒▒▒▒▒▒▒▒     Sogamoso           142                 │  │
│  │  ▒▒▒▒▒▒▒▒▒▒▒       Duitama            98                  │  │
│  │  ... 120 municipios más                                   │  │
│  │  Fuente: SIMAT 2025 [1] · DIVIPOLA [2]                    │  │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ▸ Ver tabla cruda (50 filas)                                   │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  FUENTES CONSULTADAS                                            │
│                                                                 │
│  [1] MIN. DE EDUCACIÓN NACIONAL                                 │
│      Establecimientos educativos por municipio — SIMAT          │
│      ID: abc1-2def · ver dataset → · JSON SODA →                │
│                                                                 │
│  [2] DANE                                                       │
│      DIVIPOLA — Códigos municipios                              │
│      ID: gdxc-w37w · ver dataset → · JSON SODA →                │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  PREGUNTAS RELACIONADAS                                         │
│  → ¿Cobertura educativa en Boyacá?                              │
│  → ¿Cuántos colegios privados hay en Boyacá?                    │
│  → ¿Tendencia de matrícula en Boyacá 2018-2024?                 │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  DatosVivos está en versión Beta-1. Cada cifra se calcula con   │
│  pandas sobre los datos reales del dataset citado. Si una       │
│  afirmación parece imprecisa, abre el dataset original y        │
│  verifícalo.                                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.3 Dataset detail `/dataset/{id}`

```
┌─────────────────────────────────────────────────────────────────┐
│  ← volver                                                       │
│                                                                 │
│  Establecimientos educativos por municipio — SIMAT              │
│  MINISTERIO DE EDUCACIÓN NACIONAL                               │
│                                                                 │
│  ┌── METADATA ────────────────┐  ┌── PREVIEW ─────────────────┐ │
│  │ ID         abc1-2def       │  │ cod_mpio │ nombre │  est  │ │
│  │ Publicado  2018-03-15      │  │ ─────────┼────────┼─────  │ │
│  │ Actualizado 2025-04-01     │  │ 15001    │ Tunja  │  187  │ │
│  │ Frecuencia mensual         │  │ 15759    │ Sogam… │  142  │ │
│  │ Licencia   Open Data CO    │  │ ...                       │ │
│  │ Filas      ~85 000         │  │                           │ │
│  │ Columnas   12              │  │ Mostrando 100 de 85 000   │ │
│  │ ver en datos.gov.co →      │  │ Descargar CSV →           │ │
│  │ JSON SODA →                │  │                           │ │
│  └────────────────────────────┘  └────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.4 Acerca `/acerca`

Una columna 60ch. Manifiesto en Plex Serif body-lg, tres pilares como `<section>` numerados con kicker mono. Foto en blanco y negro del equipo ANI (opcional; mejor sin foto). Enlaces a docs CRISP-ML(Q), ADRs y este BRAND.md.

### 9.5 Accesibilidad `/accesibilidad`

Una columna 60ch con `A11yPanel` arriba y documentación textual abajo: qué cumple (Ley 1618, WCAG 2.1 AA), qué no cubre, atajos de teclado, contacto para reportar problemas de accesibilidad.

---

## 10. Inspiraciones (referencias reales)

Antes de inventar, mirar a estas referencias. Ninguna se copia; todas se respetan.

| Referencia | URL | Qué tomamos |
|---|---|---|
| GOV.UK Design System | <https://design-system.service.gov.uk/> | Sobriedad, jerarquía clara, accesibilidad como estándar mínimo, scripting anti-FOUC para temas. |
| Datawrapper | <https://www.datawrapper.de/> | Fuente + nota metodológica obligatorias bajo cada gráfico. Tipografía data Plex Mono. |
| Observable | <https://observablehq.com/> | Citas inline `[N]` con enlace a fuente. |
| NYT The Upshot | <https://www.nytimes.com/section/upshot> | Narrativa pandas con cifras dentro del párrafo. Tipografía editorial serif. |
| Pampa Type | <https://www.pampatype.com/> | Referente latam de tipografía; alternativa documentada si IBM Plex se descarta (Trasandina). |
| Stripe Press | <https://press.stripe.com/> | Editorial, papel, generosidad espacial, tipografía con autoridad. |
| Werner's Nomenclature of Colours | <https://www.c82.net/werner/> | Paleta nominada, no decorativa. Cada color tiene un origen y un uso. |
| data.gov.uk | <https://www.data.gov.uk/> | Referente público de catálogo abierto, tipografía pública. |
| Lazarillo Colombia | <https://lazarillo.app/> | Accesibilidad como diferencial, no como afterthought. |
| El Tiempo (cabezotes históricos) | — | Referencia colombiana de jerarquía periodística. |
| Gaceta Oficial de Colombia | — | Composición a dos columnas con metadata izquierda, contenido derecha. |

**Anti-inspiraciones (lo que NO somos):**

- Vercel, Linear, Stripe Dashboard (sin sus letras editoriales) — fondo negro + acento neón + sombras radiales.
- Sitios "powered by AI" tipo v0, Bolt, Lovable — gradientes púrpura, neumorphism, generic Inter.
- Páginas de gobierno Latam que imitan Apple — sin identidad propia.

---

## 11. Lista negra (qué nunca hacer)

Si una propuesta viola alguna de estas reglas, se rechaza sin discusión. No requiere justificación nueva — la justificación está aquí.

1. Sin **emojis** en ninguna UI productiva.
2. Sin **morados, violetas, fucsia, cyan** como acentos.
3. Sin **gradientes** lineales o radiales en componentes productivos (excepto la única excepción documentada en §3.5).
4. Sin **glassmorphism, neumorphism, backdrop-blur** sobre fondos.
5. Sin **shadows con blur** mayor que `0`. Ninguna excepción.
6. Sin **animaciones de aparición** (fade-up, slide-in, spring). Las transiciones existen solo para estados, no para "presentación".
7. Sin **fuentes en lista negra**: Inter, Roboto, Space Grotesk, SF Pro, Geist, Lato, Open Sans, Montserrat, sans-serif default.
8. Sin **lottie de "IA pensando"**, sin sparkle `✨`, sin avatares de robot, sin "powered by AI".
9. Sin **shimmer skeletons coloridos** — skeleton solo en hairline gris-papel.
10. Sin **iconos rellenos**, sin pre-sets (Material/Feather/Lucide) sin re-trazar al stroke 1.5px square.
11. Sin **badges pill** (radius > 2px). Sin chips circulares.
12. Sin **Tailwind blue/purple/indigo/pink/teal defaults**. Solo tokens propios.
13. Sin **"Powered by AI"**, "Made with [emoji]", "Built with [stack]" en pie.
14. Sin **chat bubbles**. Aunque el motor responde como agente, la UI no mimica WhatsApp.
15. Sin **avatares de "asistente"**. No hay persona detrás de la respuesta — hay un dataset y un cálculo.
16. Sin **emoji-as-icon** ni en mensajes del sistema ni en empty states.
17. Sin **autocompletado intrusivo** en HeroSearch — las sugerencias aparecen como chips abajo, no como dropdown que tapa la respuesta.
18. Sin **modales** que bloqueen flujo — solo drawer lateral derecho para filtros y accesibilidad.
19. Sin **opacidad como mecanismo de deshabilitar**. Usar `--ink-muted` + `aria-disabled`.
20. Sin **outline: none** en focus. Siempre `--focus-ring` 2px offset 2px visible.

---

## 12. Mantenimiento del documento

- Este documento se cambia primero, el código después. No al revés.
- Cualquier cambio requiere PR con razón documentada en `CHANGELOG.md` bajo "Brand".
- Decisiones estructurales (cambio de paleta, cambio de tipografía, cambio de wordmark) requieren ADR nuevo.
- Decisiones tácticas (añadir un token, ajustar contraste de un acento, sumar un icono al MVP) no requieren ADR — pero deben quedar en `CHANGELOG.md`.
- Cada PR de `/web` que afecte estilos confirma en su descripción: *"Cumple BRAND.md §N"* citando las secciones tocadas.

### Referencias bidireccionales

- [`README.md`](../README.md) — enlace en la tabla "Para el jurado MinTIC".
- [`docs/architecture.md`](./architecture.md) — Capa 3 (Interfaz) cita este documento.
- [`docs/accessibility.md`](./accessibility.md) — cruzar §3.4 (alto contraste) y §4.2 (escala tipográfica).
- [`docs/adr/012-civic-editorial-design-system.md`](./adr/012-civic-editorial-design-system.md) — ADR que decide el sistema cuya implementación documenta este archivo.
- [`docs/adr/011-migracion-streamlit-a-nextjs.md`](./adr/011-migracion-streamlit-a-nextjs.md) — ADR que habilita el rebranding al cambiar de stack.
- [`docs/crisp_mlq/00_index.md`](./crisp_mlq/00_index.md) — entrada del catálogo documental.
- [`docs/glossary.md`](./glossary.md) — términos del sistema visual (token, hairline, Civic Editorial, IBM Plex, anti-FOUC, modo).
