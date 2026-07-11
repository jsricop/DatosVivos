# Lecciones aprendidas — DatosVivos

Las lecciones se anotan en orden cronológico inverso (más reciente primero).
Cada entrada es brevísima — el detalle vive en commits, ADRs y reportes.

## 2026-06-08 — Hito R + Follow-ups: refinamiento decisor y curación federados

### Audit "100% match con Socrata" ≠ "datos útiles para el decisor"

Hito Q.7 firmó las 34 cols de `v_dataset_status` al 100% match Socrata. Diez
días después, una mirada desde la perspectiva del Director reveló que columnas
firmadas al 100% nativos estaban **al 0% en federados CKAN** (3.801 Bogotá +
768 Cali + 56 Valle): el harvester ignoraba 80% de la metadata expuesta. La
métrica correcta para tablero del Director es **cobertura global por columna,
dividida por bucket de fuente** — no match agregado contra Socrata.

### NULL como señal real vs NULL como bug

`number_of_comments=NULL` en un dataset sin actividad ≠ `cobertura_geografica=NULL`
en CKAN sin curar. El primero queda (insight: solo 68/23.854 datasets reciben
comentarios — "Socrata como red social no funcionó"). El segundo se cura.
**Distinguir es la base de la honestidad del tablero.**

### "Descentralizada" en `entities.kind`: divipola = sede, no jurisdicción

El campo `divipola_municipio` para entities `kind='descentralizada'` es la
SEDE FÍSICA, no la jurisdicción de los datos. IGAC tiene sede en Bogotá pero
sus 5.750 datasets cubren todo el país. Curar automáticamente por divipola
de descentralizadas inventaría jurisdicción incorrecta. **Solución: reglas
explícitas por nombre de entity (14 casos cubren 7.728 datasets), no patrones
genéricos.**

### Harvester con dispatcher por API ≠ harvester por protocolo

`harvest_ckan.py` (CKAN) y `harvest_dcat.py` (DCAT JSON-LD) son scripts
separados que comparten helpers (`_normalize_license_id`). Razón: MEDATA usa
Drupal+DKAN con `/data.json` Project Open Data v1.1, NO CKAN. Mezclar protocolos
en un dispatcher mete `if portal in CKAN_PORTALS` que crece linealmente con cada
nuevo protocolo. Un script por protocolo escala mejor.

### Vistas paralelas `_decisor` para coexistencia sin downtime

PowerBI tiene queries M pegadas a nombres de columna. Eliminar `view_count`
rompe el .pbix aunque el dato esté en `page_views_total`. Solución: crear
`v_dataset_status_decisor` curada y endpoint `/datasets_decisor.csv` nuevo,
manteniendo vistas viejas 2-4 semanas para migración gradual. Reversibilidad
gratuita: rollback = cambiar el path del CSV en el modelo M.

### Header HTTP `Last-Modified` > columna `last_refreshed_at` en CSV

Telemetría ETL no pertenece a las filas del dataset. Servirla como header
HTTP estándar (RFC 7231) permite que cualquier cliente lea frescura sin
necesidad de columna por fila, manteniendo el CSV semánticamente limpio.

### CKAN Bogotá: `update_frequencies` es STRING, no array

Bug que mató cobertura en cosecha inicial (`isinstance(ufs, list)` falla
con `'Anual'`). Suportar ambos tipos en harvesters CKAN es regla de oro:
los portales son heterogéneos incluso dentro del mismo estándar.

## 2026-05-29 — Hito Q + Hito 1 + Reto F.4/F.5 + Fase D + Fase 2

### Patrón "subcadena genérica gana a la específica" — bug class real

Tres sitios distintos del ETL usaban substring match sin orden ni word
boundary: `parse_frequency_days` (LIKE '%mes%' atrapaba 'semestral'),
`_find_by_token` (claves `domain_metadata`), `_build_entity_resolver`
(abbrev "ica" matcheaba "antioquica"). **Reasignó 2.687 datasets mal
atribuidos** (30% del catálogo). Fix: regla específica antes de la
genérica, word boundary, length DESC.

### Auditoría externa contra fuente es indispensable

Validación columna×Socrata reveló que 8 entidades con 3-4 char abbrevs
atribuían falsamente datasets a ICA (1.774), ANI (352), INS (273). El
ETL "funcionaba" — los datos eran erróneos. **Sin auditoría contra
fuente, los bugs silenciosos se vuelven mitología organizacional**.

### DCAT ≠ Información-de-Datos en domain_metadata

Federados publicados via DCAT usan claves `Common-Core_*` (ISO 8601 para
frecuencia, `R/P1Y` etc.); nativos colombianos usan
`Información-de-Datos_Frecuencia-de-Actualización`. ~320 federados
quedaban con semáforo en fallback fijo hasta que parse_frequency_days
aprendió ISO 8601 (Migración 011).

### `federation` ≠ ingestión completa

datos.gov.co federa solo el 13% del catálogo de Bogotá Datos Abiertos
(276 de 2.112). El resto vive en CKAN distrital. Estrategia: harvesting
directo CKAN (Reto F.5) **subió el catálogo de 18.402 a 23.027 datasets
(+25%)** en una sesión.

### DuckDB sobre CSV remoto es game-changer

OData ignora `$apply`; pandas explota en RAM con archivos grandes; cargar
14.000 CSVs a Postgres es operativamente caro. **DuckDB + `httpfs` + cache
disk-backed** ejecuta agregaciones server-side sobre CSVs remotos sin
infraestructura adicional. Speedup de 66% en queries repetidas vía cache.

### LLM razona, motor verifica — anti-alucinación es código, no prompt

Confiar en "no inventes números" del prompt NO funciona (qwen2.5:7b
inventó cifras en Ranking durante el smoke). Lo que funcionó: validator
post-LLM que extrae todo número de la respuesta y verifica que aparezca
en `rows`. **Patrón generalizable**: para cualquier output LLM sobre
datos, validar deterministamente que las afirmaciones cuantitativas
correspondan al substrato.

### Pre-formatear cifras grandes baja alucinación de magnitud

LLM no cuenta ceros bien. Si pasamos "9.192.802.561.842" pre-formateado
con separadores, lo replica fielmente; si pasamos "9192802561842",
puede generar 919.280.256.184.200 (×100) o 9.192.802 (÷1M). **El
contexto numérico legible reduce errores de magnitud sin tocar el modelo**.

### LLM hallucina territorios — guardrail post-LLM lo blinda

Mapper NL→chips eligió "08=Atlántico" para "Mapa de homicidios por
departamento" (sin nombrar uno). Fix: guardrail determinista que solo
acepta el territorio/entidad inferido si su label aparece en el query
original. **El prompt es la primera línea; el guardrail es la última**.

### Cache CSV federado vs cron diario

Trade-off: TTL del cache 24h alineado con cron diario del ETL. Si bajamos
TTL a 1h, primer-query siempre rápida pero overhead de descargas; si
subimos a 7d, riesgo de servir datos stale. **24h es el sweet spot
operacional**.

### `dataset_id` VARCHAR(20) sobrevive a CKAN UUIDs

Pensamos que IDs CKAN (36 hex chars) no cabrían. Solución: `<prefix><16hex>`
= 20 chars exactos. **VARCHAR(20) no necesitó ALTER — y eso evitó tener
que dropear/recrear views dependientes (v_dataset_status,
v_entity_summary)**.

### Telemetría hash del NL > query texto

Almacenar el texto de la query NL en logs viola privacidad y crea
basura. Almacenar sha1(40 chars) permite deduplicar y detectar queries
recurrentes problemáticas sin guardar el texto. Suficiente para
observabilidad, respetuoso del ciudadano.

### Tests unitarios mientras corre un script de 25 min

Mientras `backfill_license_id` corría en background, escribimos 36
unit tests para los módulos del día. **Paralelizar trabajo IO-bound
con trabajo cognitivo independiente acelera la entrega**.

### docs/ gitignored: el costo de la decisión

Documentación interna no entra a git → no llega a CI, no hace PR review,
no se sincroniza con quien clona el repo. **Compensar con un comando
manual `make docs-publish` que copie docs/ a un canal interno (Notion,
Confluence)**. (Pendiente.)

## 2026-07-10 — Pivote panorama-decisor y publicación de la documentación

### La home cuenta la historia del activo, no de la herramienta

El buscador era la entrada primaria, pero el activo más valioso resultó ser el
**catálogo curado consolidado** (6 portales, semáforo, territorio). Invertir la
jerarquía (panorama → tablero → buscador, ADR-023) hizo visible el hallazgo
central — 71 % del catálogo desactualizado — que la home anterior escondía.
**El orden de la información ES una decisión de producto.**

### docs/ gitignored: la deuda se cobró

El concurso exige repo auditable con documentación pública. La decisión de
ignorar `docs/` completo obligó a una revisión de seguridad archivo por archivo
antes de publicar (se encontró topología operativa en `etl_cron_devops.md`, que
quedó excluido). **Separar desde el día uno "documentación del producto"
(pública) de "runbooks de operación" (privados)** evita esta auditoría de pánico.

### Los claims que el roadmap va a volver falsos, se retiran antes

"El modelo corre localmente" era cierto, pero la migración a la API de Claude
está decidida. Retirarlo de web y docs ANTES de migrar evita el momento en que
la documentación miente. **Documentar capacidades intercambiables
(`LLM_BACKEND`), no implementaciones puntuales.**
