# DatosVivos — Frontend Beta-2 (`web/`)

Interfaz Civic Editorial sobre el motor IA de DatosVivos. Construida con Next.js 15 + React 19 + TypeScript estricto + Tailwind CSS v4.

> Fuente de verdad de la marca: [`docs/BRAND.md`](../docs/BRAND.md). Si algo en este código contradice ese documento, gana el documento.

## Stack

| Capa | Tecnología | Justificación |
|---|---|---|
| Framework | Next.js 15 App Router | RSC + streaming SSE nativo. ADR-011. |
| Lenguaje | TypeScript estricto | `strict: true`, `noUncheckedIndexedAccess`. |
| Estilos | Tailwind CSS v4 + tokens CSS | 3 modos color via `[data-theme]`. BRAND.md §3. |
| Gráficos | Visx (D3 headless) | Sin estilos default. BRAND.md §8.9. |
| Mapas | MapLibre GL JS | Choropleth DIVIPOLA. BRAND.md §8.8. |
| Tablas | TanStack Table v8 | Headless, accesible. BRAND.md §8.7. |
| Primitivas | Radix UI (Dialog, ToggleGroup, Tooltip) | Accesibilidad WCAG nativa. |
| Validación | zod | Compartido client/server. |
| Tests | Playwright + axe-core | E2E en 3 modos color. |

## Comandos

```bash
npm install                  # primera vez
npm run dev                  # dev server en :3001 (turbopack)
npm run build                # producción
npm run typecheck            # tsc --noEmit
npm run lint
npm run test:e2e             # Playwright (requiere `npm run test:e2e:install`)
```

## Estructura

```
src/
  app/                       App Router
    layout.tsx               Root layout + anti-FOUC + carga IBM Plex
    page.tsx                 Home /
    buscar/page.tsx          Resultados /buscar?q=…
    dataset/[id]/page.tsx    Ficha dataset
    acerca/page.tsx          Manifiesto
    accesibilidad/page.tsx   A11yPanel
    api/query/route.ts       SSE proxy → FastAPI Python
  components/                UI components (BRAND.md §8)
  lib/                       Utilities: theme hook, fetch, types
  styles/
    tokens.css               Variables CSS por modo
    globals.css              Reset, typography, fontFace IBM Plex
public/
  fonts/                     IBM Plex Serif/Sans/Mono woff2 (self-hosted)
  icons/                     SVG MVP 16 iconos (BRAND.md §6.2)
  geo/                       Geojson DIVIPOLA
tests/                       Playwright specs
```

## Variables de entorno

```env
API_BASE_URL=http://localhost:8000   # FastAPI Python (api/)
```

## Integración con el motor Python

El frontend NO ejecuta el motor IA. Hace fetch a `api/v1/*` expuesto por FastAPI (`api/main.py`), que internamente orquesta `ai_engine.Analyzer` con streaming SSE. Decisión: [ADR-013](../docs/adr/013-fastapi-sse-vs-mcp-http.md).

## Accesibilidad

WCAG 2.1 AA en los 3 modos color (claro/oscuro/alto contraste). Verificación: `npm run test:e2e` ejecuta axe-core sobre las 5 rutas en cada modo.

## Coexistencia con Streamlit

Streamlit (`../app/`) sigue operativo bajo perfil Docker `legacy` durante 30 días tras cutover. Después se retira (ADR-011 §"Plan de coexistencia").
