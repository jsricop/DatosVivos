# Fase 1 — Chips como entrada PRIMARIA

> Estado al 2026-05-23 (commit develop): Fase 1 prereq + Fase 1.1 completas.
> Próxima fase: validación con usuarios reales + Fase 2 (LLM mapper NL→chips).

## Qué cambió

Pivote del audit top-down: en lugar de seguir parchando retrieval ML
open-text sobre 8.396 datasets, hacemos del **QueryBuilderBar (chips
estructurados)** la entrada PRIMARIA. La barra libre `HeroSearch` queda
detrás de un toggle "Modo libre (avanzado)" durante el período de
validación.

**Beneficio clave**: el bug "Estudiantes de Bogotá → UPTC" no puede
ocurrir por diseño. Si el usuario marca `Territorio=Bogotá D.C.`, el
filtro SQL excluye datasets cuya `jurisdiccion_geo_codes` no contiene
"11" (Bogotá).

## Componentes

### Backend (PR #32 + #33)

| Pieza | Archivo | Propósito |
|---|---|---|
| Migration jurisdicción | `db/migrations/002_chip_metadata.sql` | Columnas `jurisdiccion_nivel/_geo_codes/_confidence/_reason/_inferred_at` en `datasets` |
| Script curación | `scripts/curate_chip_metadata.py` | Infiere jurisdicción desde `entity_raw + name` con reglas escalonadas |
| Endpoint listas | `GET /api/v1/chips` (router `api/routes/chips.py`) | Devuelve TEMA/TIPO/TERRITORIO/ENTIDAD dinámicas |
| Endpoint query | `POST /api/v1/query/chips` (same router) | Filtra catálogo deterministically + top-10 candidatos |
| Schemas | `api/models/schemas.py` | `ChipOption`, `ChipsQueryRequest/Response`, `ChipsCandidateDataset` |

### Frontend (PR #33)

| Pieza | Archivo | Propósito |
|---|---|---|
| Home | `web/src/components/HomeSearchPanel.tsx` | Chips arriba, HeroSearch en `<details>` "Modo libre" |
| Render | `web/src/components/ChipsResultView.tsx` (NUEVO) | Top-10 candidatos + mensaje subset + badge ELEGIDO |
| Página | `web/src/app/buscar/page.tsx` | Detecta modo chips (sin `q` con filters) vs modo libre |
| Proxy | `web/src/app/api/chips/route.ts` (NUEVO) | Forward GET/POST a backend |

## Cobertura de jurisdicción curada (2026-05-23)

Sobre los 8.396 datasets de producción:

| Nivel | Datasets | % |
|---|---:|---:|
| municipal | 4637 | 55.2% |
| departamental | 1857 | 22.1% |
| nacional | 1619 | 19.3% |
| distrito_capital | 263 | 3.1% |
| sin clasificar | 20 | 0.2% |

**99.4% high confidence**, 0.4% medium (description match), 0.2% sin clasificar.

Reglas que el script aplica (orden de precedencia):

1. **Municipio específico** — incluye aliases coloquiales (Cali = Santiago de Cali, Cartagena = Cartagena de Indias, etc.).
2. **Dpto NO-Bogotá** gana sobre nacional. Caso: "Contraloría Departamental del Cauca" → Cauca, no nacional.
3. **Nacional** (~55 tokens + ~70 acrónimos). Ignora "Bogotá D.C." como sede física: "Ministerio en Bogotá" → nacional.
4. **Distrito capital** (Bogotá puro, sin nacional ni dpto). 263 datasets quedaron acá (notarías, IDU, secretarías distritales, alcaldía).
5. **Fallback description** — match de dpto en descripción → departamental medium.

Excluidos del catálogo de mpios por ambigüedad: nombres de dpto, nombre del país (Colombia mpio en Huila), ciudades internacionales (Florida, California, Buenos Aires, Argentina, Venecia).

## Flujo end-to-end (validado en producción)

**Combo "Educación + Bogotá" (código 11):**
- 7 datasets en subset
- Top: ETITC, Agencia Distrital Educación Superior, FODESEP. **Ninguno UPTC**.
- Bug original imposible por construcción.

**Combo "Salud + Antioquia" (código 05):**
- 67 datasets en subset
- Top: Gobernación Antioquia, Hospital del Sur, Alcaldía Envigado. **Todos del territorio**.

**Combo solo "Salud" (746 datasets):**
- `chosen_dataset_id: null`
- Mensaje: "Hay 746 datasets. Marcá otro chip para refinar."
- Sugiere: entidad, territorio, tipo.

**Adversarial (sin chips):**
- HTTP 400 "Marcá al menos un chip antes de buscar."

## Pendiente / próximas fases

### Validación
- [ ] **Re-correr `run_eval.py`** post-deploy para confirmar no-regresión en path libre.
- [ ] Smoke con usuarios reales del nuevo flow chips.
- [ ] Expandir `golden_queries.yaml` con `expected_chip_combination` por query.

### Curación residual (deferred)
- 20 datasets sin clasificar (`Red de Salud del Oriente`, `Megabus`, `La Previsora`, etc.).
- Algunos casos `distrito_capital` que son nacional con acrónimo no cubierto (ej. ETITC, FODESEP). Iteración 3 puede agregarlos.
- Estrategia futura: LLM fallback para los `(none)` y `medium`.

### Fase 2 — LLM mapper NL→chips
- Devolver `HeroSearch` como entrada PRIMARIA con el LLM mapeando texto libre a chips automáticamente.
- Convierte un problema OPEN (retrieval ML sobre 8K datasets) en uno CLOSED (clasificar texto a vocabulario finito de chips).

### Limpieza
- Eliminar HeroSearch toggle cuando los chips estén validados (3-4 semanas).
- Quitar tokens del intent_classifier por embeddings legacy si Fase 2 lo reemplaza.
