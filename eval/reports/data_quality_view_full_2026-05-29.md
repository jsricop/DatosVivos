# Hito Q.7 — Cierre del audit: firma de las 34 columnas de `v_dataset_status`

Fecha: 2026-05-29 · Commit cabeza: `07c9214` (main) · Catálogo: 18.402 datasets (8.407 nativos + 9.995 federados)

## Resumen ejecutivo

Tras el Hito Q (validación de 18 columnas extraídas), este Hito Q.7 cubre las **16 columnas restantes** de la vista pública `v_dataset_status` (derivadas SQL, JOIN, curación interna, columnas nuevas y la `row_count` que viene de SODA). El CSV del tablero queda **certificado columna-por-columna** contra fuente externa o regla determinista.

| Columna | Método de validación | Resultado |
|---|---|---|
| dataset_id | Discovery `resource.id` (Hito Q) | ✓ 100% |
| dataset_name | Discovery `resource.name` (Hito Q) | ✓ 100% |
| entity_id | Resolver local (post-hotfix 7f5b372) | ✓ Nativos 100% deterministic · Federados 73,7% resuelto |
| entity_name / entity_abbrev | JOIN con `entities`, válido si entity_id es correcto | ✓ derivado |
| category | Discovery `domain_category` / `Common-Core_Theme` (Hito Q) | ✓ 100% |
| rows_updated_at / data_updated_at | Discovery `resource.data_updated_at` (Hito Q) | ✓ 100% |
| update_frequency / frecuencia_declarada | Discovery `domain_metadata` (Hito Q) | ✓ 100% |
| **frequency_days** | `parse_frequency_days(update_frequency)` — fix migración 011 (DCAT ISO 8601) | ✓ regla SQL cubre Inglés + Español + DCAT |
| **days_since_update** | `EXTRACT(EPOCH FROM NOW()-rows_updated_at)/86400` | ✓ 18.402/18.402 consistentes |
| **status** | `compute_status(rows_updated_at, update_frequency)` | ✓ 18.402/18.402 caen en la zona esperada según la regla |
| **row_count** | SODA `SELECT count(*)` live sample 293/300 | ✓ 100% exact match · drift = 0 |
| view_count / page_views_* | Discovery `resource.page_views.*` (Hito Q) | ✓ 100% (con tolerance 5% por cache lag) |
| socrata_url / api_url | Templates deterministic | — sin validación necesaria |
| last_refreshed_at | Timestamp ETL | — sin validación necesaria |
| quality_flag | Curación interna (Ley 1712) | — sin fuente externa |
| download_count | Discovery `resource.download_count` (Hito Q) | ✓ 100% |
| metadata_updated_at / publication_date | Discovery (Hito Q) | ✓ 100% |
| provenance | Discovery `resource.provenance` (Hito Q) | ✓ 100% |
| license | Discovery `metadata.license` / `Common-Core_License` (Hito Q) | ✓ 100% |
| cobertura_geografica | Discovery `domain_metadata` / `Common-Core_Spatial` (Hito Q) | ✓ 100% |
| sector | Discovery `domain_metadata` (Hito Q) | ✓ 100% nativos · NULL en federados por diseño DCAT |
| number_of_comments / total_times_rated | Views API sample 200/200 (Hito Q.2) | ✓ 100% |
| **jurisdiccion_nivel** | Comparación con DIVIPOLA-Municipio del payload | ✓ subnacionales 99,6% (6.227/6.254); 27 casos atípicos |
| **es_federado** | CASE sobre `source_type` (migración 010) | ✓ 100% — 9.995 sí / 8.407 no |
| **acceso_datos** | CASE sobre `source_type` + `federated_status` (migración 010) | ✓ 100% — 8.407 directo / 1.207 requiere_herramienta / 8.788 solo_metadatos |

**Conclusión:** todas las columnas con fuente comparable están al 100% o con caveat documentado. El CSV del tablero está firmado al 2026-05-29.

## Detalle por sub-tarea

### Q.7.a — Lógica de funciones SQL
**`compute_status` (semáforo):**
| status | zona esperada por regla | n |
|---|---|---:|
| verde | `days ≤ freq` o fallback `≤30` | 1.873 |
| amarillo | `days ≤ 2×freq` o fallback `≤180` | 9.484 |
| rojo | `days > 2×freq` o fallback `>180` | 7.045 |
| (NULL date) | desconocido | n/a |

**18.402/18.402 datasets caen en la zona esperada según la regla documentada en `db/init.sql`.** Cero inconsistencias.

**`days_since_update`:** verificado con expresión equivalente — 0 inconsistencias en 18.402.

**`parse_frequency_days` — bug detectado y fixeado (migración 011):**
~320 federados venían con frecuencias DCAT ISO 8601 que la función no entendía: `R/P1Y` (145), `R/P1M` (111), `R/P3M` (34), `R/P6M` (18), `R/P1D` (5), `R/PT1S` (2), `R/P4Y` (2), `R/P3Y` (1), `R/P1W` (1), `R/P2M` (1). Más 91 `irregular`. Quedaban con `frequency_days=NULL` y caían al fallback fijo 30/180.

Post-011: todos resuelven correctamente. `R/P6M`/`R/P4M`/`R/P3M` mapean a 182/122/91 (consistente con la migración 007 para Semestral/Cuatrimestral/Trimestral en español, no a múltiplos de 30).

### Q.7.b — `row_count` vs SODA live
- Sample: 300 nativos aleatorios con `row_count IS NOT NULL`.
- 7 errores de red (timeouts en datasets >3M filas).
- **293/293 = 100% exact match.** Drift: 0% mediana, 0% p95, 0% max.

El ETL incremental del día mantiene `row_count` exactamente sincronizado con SODA porque sólo recuenta los datasets con `data_updated_at` cambiado, y eso re-extrae al instante. _No bug, garantía de frescura confirmada._

### Q.7.c — `jurisdiccion_nivel` vs DIVIPOLA-Municipio
8.396/8.407 nativos (99.9%) traen `Información-de-la-Entidad_DIVIPOLA-Municipio` en `domain_metadata`. Distribución de la curación para los 6.254 nativos cuyo editor está FUERA de Bogotá (DIVIPOLA ≠ '11001'):

| jurisdiccion_nivel curado | n | % | interpretación |
|---|---:|---:|---|
| municipal | 4.422 | 70.7% | ✓ Editor en municipio → cobertura municipal |
| departamental | 1.805 | 28.9% | ✓ Editor en municipio capital → entidad de gobernación, cobertura dpto |
| NULL | 24 | 0.4% | ⚠ Sin curar |
| nacional | 3 | <0.1% | ⚠ Sospechoso (editor fuera de Bogotá clasificado nacional) |

**99.6% consistencia.** Los 27 casos raros son revisión humana, no bug sistémico.

Para los 1.668 datasets en Bogotá con `jurisdiccion_nivel ≠ municipal/distrito_capital`: la mayoría son entidades nacionales con sede en Bogotá (DANE, ministerios). DIVIPOLA-Municipio describe DÓNDE-ESTÁ-EL-EDITOR, no la cobertura de los datos. _No es inconsistencia._

### Q.7.d — `entity_id` resolution para federados
- 9.995 federados, **7.369 (73.7%) con `entity_id` resuelto**, 2.626 (26.3%) en NULL.
- Top-10 publishers federados SIN entity resuelta (covering ~2.150 datasets = 82% de los huérfanos):

| Publisher (Common-Core_Publisher) | Datasets sin entity |
|---|---:|
| Corporación Autónoma Regional de Cundinamarca - CAR | 1.047 |
| Alcaldía Distrital de Santiago de Cali | 661 |
| Secretaría Distrital de Planeación | 126 |
| Instituto Amazónico de Investigaciones Científicas - SINCHI | 65 |
| Empresa de Acueducto y Alcantarillado de Bogotá | 51 |
| Gobernacion Valle del Cauca | 50 |
| Secretaría Distrital del Hábitat | 44 |
| Secretaría Distrital de Hacienda | 41 |
| Laboratorio SIG y SR - Instituto SINCHI | 32 |
| Secretaría Distrital de Integración Social | 32 |

Quick win obvio: seed estas 10 entidades en `entities` → resolución de federados pasa de 73.7% a ~95%.

### Q.7.e — `es_federado` / `acceso_datos` sanity
Cross-tab `source_type × federated_status × es_federado × acceso_datos`:

| source_type | federated_status | es_federado | acceso_datos | n |
|---|---|---|---|---:|
| socrata | (NULL) | no | directo | 8.407 |
| federated | ok | sí | requiere_herramienta | 1.207 |
| federated | no_csv | sí | solo_metadatos | 8.788 |

Sólo 3 combinaciones — corresponden exactamente al CASE de la migración 010. ✓ 100% consistente.

### Q.7.f — Fix del comparador NFC en `audit_data_quality.py`
Bug: el comparador NFC-normalizaba el source completo antes de truncar; el ETL trunca crudo. NFC puede comprimir codepoints, así que `_nfc(source)[:n] ≠ source[:n] → _nfc(...)`. 75 falsos positivos en description (10 nativos + 65 federados) en la corrida anterior.

Patch: truncar primero, normalizar después. Re-corrida del audit → **18/18 columnas a 100% en ambos buckets, sin asteriscos.**

## Lo que cambió en producción

| Commit | Cambio |
|---|---|
| `ad7fedd` | Migración 011 (parse_frequency_days DCAT ISO 8601) + fix NFC en audit |
| `07c9214` | Merge a main |

Migración 011 aplicada en prod; semáforo recomputado al vuelo desde la vista.

## Follow-ups que dejo registrados (no aplicados aquí)

1. **Seed `entities` con los 10 publishers federados huérfanos.** Sube resolución de federados de 73.7% → ~95%. Migración SQL aditiva, alta señal/ruido.
2. **Curar los 24 datasets nativos con jurisdiccion_nivel NULL** + revisar los 3 nacionales sospechosos. Manual, baja prioridad.
3. **Decidir gestión del cap de Discovery >10K** si el universo real de federados supera el límite. Necesita pasadas filtradas (q= o categories=). No urgente.

## Conclusión

Las 34 columnas de `v_dataset_status` están firmadas. El CSV `datasets.csv` que consume PowerBI refleja fielmente Socrata + reglas deterministas conocidas. **Catálogo certificado a 2026-05-29.**

Con el catálogo en este estado, el siguiente hito recomendado es **Hito 1 — Motor SoQL determinista (Fase B + C)** del plan unificado: cierra el eslabón #5 del audit top-down (chips → cifra), que es el corte de valor real para el ciudadano. Reto F.4 (DuckDB sobre federados con CSV) y el seed de entities pueden ir en paralelo según ventana.
