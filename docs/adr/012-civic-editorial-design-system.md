# ADR-012: Sistema de diseño Civic Editorial

**Estado:** ~~Aceptada~~ **Superada por [ADR-021](./021-sistema-diseno-gov-co.md)** (2026-06-24)
**Fecha:** 2026-05-20

> **Nota (2026-06-24):** este sistema fue reemplazado por el de ADR-021 (entidad
> pública moderna alineada con gov.co). La alternativa *"Civic Modern"* que aquí
> se descartó (línea 30) terminó siendo la dirección elegida: la legitimidad de
> verse como un servicio del Estado pesó más que la diferenciación editorial. El
> contenido siguiente se conserva como registro histórico.

## Decisión

Adoptar el sistema de diseño **Civic Editorial** (papel & tinta) como identidad visual canónica de DatosVivos. Sus elementos no negociables:

- **Wordmark:** `Datos|Vivos` con pleca ASCII real `|` en color `var(--accent)` (granate `#A52A2A` en claro, `#C24A4A` en oscuro, `#0033A0`/`#FFD400` en alto contraste).
- **Subtítulo permanente:** `── datos.gov.co` en IBM Plex Mono.
- **Tagline:** *"Datos del Estado, en tus palabras."*
- **Tipografía:** IBM Plex Serif (display), IBM Plex Sans (body/UI), IBM Plex Mono (data, IDs, kickers). Self-hosted, sin Google Fonts.
- **Paletas:** tres modos (claro/papel default, oscuro/tinta, alto contraste AAA con variantes sobre blanco y sobre negro). Definición completa en [`docs/BRAND.md` §3](../BRAND.md).
- **Formas:** border-radius máximo `2px`; bordes hairline `1px` o énfasis `2px`; sin sombras con blur; cuneta de lectura `72ch`.
- **Iconografía:** SVG propio `currentColor` stroke 1.5px square, sin emojis en UI productiva.

## Razón

Decisión tomada en sesión de planificación con el responsable del proyecto (`gerencia@gruporq.co`, 2026-05-20):

- La audiencia número 1 de DatosVivos es la **ciudadanía general colombiana**, no el jurado MinTIC. Lo institucional sin lo cercano se siente burocrático; lo "tecnológico-moderno" sin lo institucional se siente AI-genérico. Civic Editorial sintetiza ambos: rigor periodístico colombiano + accesibilidad de gaceta oficial.
- Los tres pilares declarados del proyecto (soberanía, verificabilidad, interoperabilidad) requieren una superficie visual que **comunique seriedad sin teatralizarla**. Papel y tinta no decoran; argumentan que el contenido es lo importante.
- El rebrand parte de "cero emojis, cero estilo Apple, cero firma IA" como reglas duras. Civic Editorial las absorbe naturalmente — la estética editorial nunca ha usado emojis ni glassmorphism.
- Las paletas y tipografías están **libres de cualquier asociación con AI tooling popular** (Vercel, Linear, Stripe, v0, Bolt, Lovable, ChatGPT). IBM Plex es gobierno-grade, Inter está vedado.

Direcciones alternativas evaluadas y descartadas:

- **Civic Terminal (mono-céntrico, fondo casi-negro):** se sintió demasiado "tech bro", aleja a la ciudadanía general.
- **Civic Modern (sans grotesque + bloques sólidos):** demasiado cercano al look gob.uk + Linear; menos diferenciado.
- **Apple-like minimal:** explícitamente prohibido por el usuario.

## Trade-off

- **Aprendizaje del equipo.** Civic Editorial impone restricciones (sin sombras con blur, sin radius >2px, sin emojis) que un dev acostumbrado a Tailwind defaults tiene que aprender. Mitigación: la lista negra de [`BRAND.md` §11](../BRAND.md) es exhaustiva — si la propuesta viola una regla, se rechaza sin discusión.
- **Costo de mantenimiento.** Cada componente nuevo debe revisarse contra BRAND.md. Mitigación: revisión PR obligatoria con cita explícita *"Cumple BRAND.md §N"*.
- **Riesgo de monotonía visual.** Una paleta restringida (cinco tokens semánticos × dos acentos) puede verse plana. Mitigación: la diferenciación viene de tipografía (Serif vs Sans vs Mono) y de regletas tipo periódico, no de color.
- **Self-hosting de fuentes.** Implica ~600 KB en `/web/public/fonts/` (subset latin-ext de Plex). Aceptable; evita Google Fonts CDN como exige la política de privacidad ciudadana del proyecto.

## Referencias

- [`docs/BRAND.md`](../BRAND.md) — documento operativo del sistema, fuente de verdad
- ADR-011 — migración Streamlit→Next.js que habilita el sistema (ADR temprano no conservado)
- [`docs/accessibility.md`](../accessibility.md) — cruza con §3.4 (alto contraste) y §4.2 (escala tipográfica)
- [`docs/crisp_mlq/05_evaluation.md`](../crisp_mlq/05_evaluation.md) — criterios de evaluación visual (no-AI look, WCAG AA en 3 modos)
