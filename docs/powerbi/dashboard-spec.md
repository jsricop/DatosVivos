# Especificación visual — Dashboard Power BI ejecutivo DatosVivos

> Acompaña a [ADR-014](../adr/014-reabrir-powerbi-con-login.md). El equipo ANI usa Power BI Desktop para armar el `.pbix`/`.pbit` siguiendo esta especificación. Las views están declaradas en [`sql-views.sql`](./sql-views.sql); la conexión, en [`connection-string.md`](./connection-string.md).

## Reglas de identidad (BRAND.md)

- **Sin emojis** en cualquier visual del dashboard.
- Tipografía: Power BI Desktop carga Segoe UI por defecto. Cambiar a **IBM Plex Sans** en `Vista → Cambiar tema → Personalizar` para alinear con `web/`. Pesos: Regular para body, SemiBold para títulos.
- Paleta de colores (Power BI → Vista → Cambiar tema → Tema personalizado):
  - Fondo: `#F3EFE3` (papel)
  - Texto principal: `#16130E` (tinta)
  - Texto secundario: `#3B342A`
  - Acento primario (CTA, números KPI): `#A52A2A` (granate)
  - Acento secundario (categorías 2): `#B8860B` (ámbar)
  - Serie 3: `#1F3A5F` (azul tinta)
  - Serie 4: `#5C6B4D` (verde tinta)
  - Serie 5: `#3B342A`
  - Hairline / regletas: `#B7A98B`
  - Verde (status): `#5C6B4D`
  - Ámbar (status): `#B8860B`
  - Rojo (status): `#A52A2A`
- Bordes: 1px hairline color `#B7A98B`. Cero sombras con blur. Cero gradientes.
- Espaciado: padding 16px interior; gap 24px entre visuales.

## Tres páginas obligatorias

### Página 1 — Vista por entidad (entrada)

Filtro implícito por URL: `?filter=Datasets/entity_abbrev eq 'MinSalud'`. Power BI aplica este filtro a TODOS los visuales de la página.

**Layout (1280×720, 12-col grid):**

```
┌─────────────────────────────────────────────────────────────────┐
│  Texto título: "Tablero · {entity_name}"                        │  span 12
├─────────────────────────────────────────────────────────────────┤
│  KPI: Total       │  KPI: Verdes     │  KPI: Consultas   │ KPI: │ span 3+3+3+3
│  datasets         │  (% actualizado) │  últimos 30 días  │ Last │
│  (Card visual)    │  (Card + barra)  │  (Card grande)    │ access│
├──────────────────────────────────┬──────────────────────────────┤
│  Donut: distribución por status  │  Top 5 datasets por consultas│  span 6+6
│  (Slice cards verde/ámbar/rojo)  │  (Tabla con bars condicionales)│
├─────────────────────────────────────────────────────────────────┤
│  Tabla maestra de tus datasets                                  │  span 12
│  Columnas: nombre · categoría · días desde update · status      │
│  · días desde último uso · enlace Socrata                       │
│  Sort default: status DESC (rojos primero)                      │
└─────────────────────────────────────────────────────────────────┘
```

**Visuales:**

1. **KPI Total datasets** — `Card` visual. Medida: `[TotalDatasets]`.
2. **KPI % actualizado** — `Card` con `KPI` indicator. Medida: `[PctActualizado]`. Color condicional: verde si ≥75%, ámbar 50-75%, rojo <50%.
3. **KPI Consultas 30d** — `Card`. Medida: `[ConsultasUltimos30Dias]`. Tendencia chips de Sparkline opcional (Power BI 2024+).
4. **KPI Último acceso** — `Card`. Medida: `[DiasDesdeUltimoAcceso]` con sufijo "días".
5. **Donut estado** — `Donut chart`. Eje: `v_dataset_status[status]`. Valores: `Count of dataset_id`. Colores fijos: verde `#5C6B4D`, ámbar `#B8860B`, rojo `#A52A2A`, gris `#776A55` (desconocido).
6. **Tabla maestra** — `Table` visual. Columnas: `dataset_name`, `category`, `days_since_update`, `status` (como indicador semáforo via formato condicional), `days_since_last_query`, hipervínculo a `socrata_url`. Habilitar `Drill-through` a Página 2.

### Página 2 — Drill-down dataset

Activado por click en una fila de la tabla maestra (Página 1) → drill-through al `dataset_id` seleccionado.

**Layout:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Título: nombre del dataset + ID                                │  span 12
│  Subtítulo: entidad publicadora                                 │
├──────────────────────────────────┬──────────────────────────────┤
│  Ficha técnica (Card stack)      │  Línea temporal de consultas │  span 4+8
│  · ID Socrata                    │  últimos 90 días              │
│  · Categoría                     │  (Line chart con marcadores)  │
│  · Filas (Socrata)               │                              │
│  · Vistas                        │                              │
│  · Última actualización          │                              │
│  · Frecuencia declarada          │                              │
│  · Status semaforizado           │                              │
│  · Botón externo Socrata         │                              │
├──────────────────────────────────┴──────────────────────────────┤
│  Top 5 intents que disparan este dataset                        │  span 6
│  (Bar chart horizontal)                                         │
├──────────────────────────────────┬──────────────────────────────┤
│  Latencia promedio (s)           │  Última consulta             │  span 3+3
│  KPI                             │  (timestamp y consulta)      │
└─────────────────────────────────────────────────────────────────┘
```

### Página 3 — Benchmark público

Sin filtro por entidad. Cualquier funcionario logueado ve esta página.

```
┌─────────────────────────────────────────────────────────────────┐
│  Título: "Benchmark público — uso del catálogo datos.gov.co"    │
├──────────────────────────────────┬──────────────────────────────┤
│  Top 10 entidades por consultas  │  Top 10 datasets más         │
│  (Bar chart vertical)            │  consultados                  │
│                                  │  (Tabla con n_queries)        │
├──────────────────────────────────┴──────────────────────────────┤
│  Mapa coroplético de Colombia    │  Tendencia mensual últimos   │  span 6+6
│  (consultas por dpto, DIVIPOLA)  │  12 meses (Area chart)       │
└─────────────────────────────────────────────────────────────────┘
```

## Medidas DAX clave

```dax
-- Conteos básicos
TotalDatasets = COUNTROWS(v_dataset_status)

DatasetsVerdes =
    CALCULATE(
        COUNTROWS(v_dataset_status),
        v_dataset_status[status] = "verde"
    )

DatasetsAmarillos =
    CALCULATE(
        COUNTROWS(v_dataset_status),
        v_dataset_status[status] = "amarillo"
    )

DatasetsRojos =
    CALCULATE(
        COUNTROWS(v_dataset_status),
        v_dataset_status[status] = "rojo"
    )

PctActualizado =
    DIVIDE([DatasetsVerdes], [TotalDatasets], 0)

-- Consultas
ConsultasTotales = COUNTROWS(queries)

ConsultasUltimos30Dias =
    CALCULATE(
        COUNTROWS(queries),
        queries[timestamp_iso] >= TODAY() - 30
    )

ConsultasUltimos90Dias =
    CALCULATE(
        COUNTROWS(queries),
        queries[timestamp_iso] >= TODAY() - 90
    )

-- Tiempos
DiasDesdeUltimoAcceso =
    DATEDIFF(MAX(queries[timestamp_iso]), TODAY(), DAY)

LatenciaPromedio =
    AVERAGE(queries[elapsed_s])

-- KPI tendencia
TendenciaMensual =
    DIVIDE(
        [ConsultasUltimos30Dias],
        CALCULATE(
            COUNTROWS(queries),
            queries[timestamp_iso] >= TODAY() - 60 &&
            queries[timestamp_iso] < TODAY() - 30
        ),
        1
    ) - 1
```

## Formato condicional clave

**Tabla maestra Página 1 → columna `status`:**

```
'verde'    → fondo #5C6B4D · texto #FFFFFF · etiqueta "Actualizado"
'amarillo' → fondo #B8860B · texto #FFFFFF · etiqueta "En riesgo"
'rojo'     → fondo #A52A2A · texto #FFFFFF · etiqueta "Desactualizado"
'desconocido' → fondo #B7A98B · texto #16130E · etiqueta "Sin fecha"
```

**KPI Página 1 % actualizado → indicador:**

```
< 0.50 → fondo rojo, ícono ▼
0.50-0.75 → fondo ámbar, ícono →
≥ 0.75 → fondo verde, ícono ▲
```

## Relaciones del modelo

```
queries (1) ──< (N) dataset_usage (N) >── (1) datasets (1) >── (1) entities

v_dataset_status     ← lookup, basada en datasets
v_dataset_usage      ← agregado de dataset_usage
v_entity_summary     ← agregado de entities + datasets + dataset_usage
v_top_datasets       ← lookup precomputado
v_queries_daily      ← agregado de queries por fecha
```

Cardinalidades:
- `entities` → `datasets`: 1-N
- `datasets` → `dataset_usage`: 1-N
- `queries` → `dataset_usage`: 1-N

Habilitar **DirectQuery** para que cada filtro consulte Postgres en vivo. Si la latencia molesta, **Import** con refresh cada 60 min vía Power BI Service (gateway).

## Calendario

Crear tabla calculada `dim_date` en DAX para drill por fecha:

```dax
dim_date =
ADDCOLUMNS(
    CALENDAR(DATE(2024, 1, 1), TODAY()),
    "Year", YEAR([Date]),
    "Month", FORMAT([Date], "MMM YYYY"),
    "MonthNum", MONTH([Date]),
    "Quarter", "Q" & ROUNDUP(MONTH([Date]) / 3, 0)
)
```

Relacionar `dim_date[Date]` con `queries[timestamp_iso]` (cast a date) y `v_queries_daily[query_date]`.

## Filtros de URL para publish-to-web

El frontend embebe el iframe con:

```
${PBI_BASE_URL}&filter=Datasets/entity_abbrev eq 'MinSalud'
```

Para que esto funcione:
1. En Power BI Desktop, el campo `entity_abbrev` debe estar en una tabla llamada exactamente `Datasets` (renombrar la view `v_dataset_status` a `Datasets` en el modelo).
2. El campo `entity_abbrev` debe ser visible (no oculto).
3. Publicar con publish-to-web crea una URL pública; el filtro se aplica server-side antes de renderizar.

## Verificación

- [ ] Tres páginas presentes y nombradas `Por entidad`, `Drill-down`, `Benchmark`.
- [ ] Filtro por URL `?filter=Datasets/entity_abbrev eq 'TEST'` aplica correctamente.
- [ ] Drill-through Página 1 → Página 2 funciona sin perder filtro de entidad.
- [ ] Sin emojis ni colores fuera de la paleta declarada.
- [ ] Tipografía IBM Plex Sans (fallback Segoe UI aceptable si IBM Plex no está instalado).
- [ ] Hipervínculos a Socrata abren en nueva pestaña.
- [ ] DirectQuery configurado o Import con refresh ≤ 60 min.
