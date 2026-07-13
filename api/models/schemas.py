"""Modelos Pydantic para requests y responses de la API.

Contratos versionados bajo `/api/v1`. Si cambias acá, también cambia los
tipos espejo en `web/src/lib/types.ts`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Intent = Literal["search", "descriptive", "comparative", "temporal", "cross_source"]
Axis = Literal["tema", "tipo", "territorio", "entidad"]


class QueryRequest(BaseModel):
    """Cuerpo del POST /api/v1/query."""

    q: str = Field(..., min_length=1, max_length=500, description="Pregunta en lenguaje natural")
    filters: dict[str, list[str]] | None = Field(default=None)


class DatasetCitation(BaseModel):
    """Referencia citable a un dataset (alineado con AnalysisResult.dataset_references)."""

    index: int
    id: str
    name: str
    entity: str | None = None
    url: str
    api_url: str


class PopularQuery(BaseModel):
    question: str
    count: int
    intent: Intent | None = None


class SuggestOption(BaseModel):
    value: str
    label: str
    count: int | None = None
    kicker: str | None = None


class SuggestResponse(BaseModel):
    axis: Axis
    options: list[SuggestOption]


class DivipolaItem(BaseModel):
    code: str
    name: str
    dpto_code: str | None = None


class DivipolaResponse(BaseModel):
    departments: list[DivipolaItem] | None = None
    municipios: list[DivipolaItem] | None = None


class DatasetColumn(BaseModel):
    field_name: str
    name: str
    data_type: str
    description: str | None = None


class DatasetMetadata(BaseModel):
    id: str
    name: str
    entity: str | None
    description: str
    columns: list[DatasetColumn]
    row_count: int | None = None
    last_updated: str | None = None
    url: str
    api_url: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    backend: str
    detail: str | None = None


# ============================================================
# Fase 1 — Chips como entrada PRIMARIA (ADR-018 cuando exista)
# ============================================================


ChipTipo = Literal["Cuántos", "Total", "Comparar", "Ranking", "Tendencia", "Mapa"]


class ChipOption(BaseModel):
    """Opción de un chip (valor seleccionable). `value` es lo que viaja al
    backend; `label` es lo que ve el usuario."""

    value: str
    label: str
    # Información extra opcional para tooltips o cards.
    count: int | None = None  # cuántos datasets aplican a este chip
    hint: str | None = None


class ChipsResponse(BaseModel):
    """GET /api/v1/chips — listas dinámicas para la UI."""

    tema: list[ChipOption]          # desde DISTINCT datasets.category
    tipo: list[ChipOption]          # hardcoded 5
    territorio: list[ChipOption]    # Nacional + 32 dptos + macroregiones
    entidad: list[ChipOption]       # top-N por uso telemetría


class ChipsQueryRequest(BaseModel):
    """POST /api/v1/query/chips — combinación de chips elegida por el usuario."""

    tema: str | None = None         # category de Socrata
    tipo: ChipTipo | None = None
    territorio: str | None = None   # código DIVIPOLA "11", "05001", "macro:caribe", "nacional"
    entidad: str | None = None      # entity_id como string
    # Sub-tags refinadores (capa 2, ver GET /api/v1/chips/refine). Multi =
    # intersection: el dataset debe tener TODOS los tags marcados.
    subtags: list[str] | None = None
    refinador: str | None = Field(default=None, max_length=200,
                                  description="Texto libre opcional, refina dentro del subset")
    # Si el usuario explícitamente marcó un dataset (botón "Era este"):
    force_dataset_id: str | None = None


class ChipsRefineResponse(BaseModel):
    """GET /api/v1/chips/refine — capa 2 sub-tags refinadores del subset.

    `subtags` viene ordenado por frecuencia DESC, filtrado de tags
    administrativos genéricos (ver `_TAG_STOPLIST` en api/routes/chips.py).
    Vacío si el subset es >500 datasets (demasiado ruido) o 0.
    """

    subset_total: int                # # datasets que matchean los chips capa 1
    subtags: list[ChipOption]        # tags top con count


class ChipsCandidateDataset(BaseModel):
    """Dataset dentro del subset filtrado por chips."""

    dataset_id: str
    name: str
    entity: str | None
    category: str | None
    row_count: int | None
    view_count: int | None
    last_updated: str | None
    url: str
    api_url: str
    jurisdiccion_nivel: str | None
    jurisdiccion_geo_codes: list[str] | None
    # Score compuesto que decidió el ORDER BY (A.2). Sirve para auditar la
    # decisión del top-1 sin abrir Postgres. null si no calculable.
    score: float | None = None


class ChipsQueryResponse(BaseModel):
    """Respuesta inicial del POST /chips — la narrativa final llega vía SSE
    si el cliente pide streaming en un endpoint posterior."""

    total_in_subset: int           # # de datasets que matchean los chips
    candidates: list[ChipsCandidateDataset]  # top-N para mostrar
    chosen_dataset_id: str | None  # el seleccionado para ejecutar SoQL
    suggested_chips: list[str] | None = None  # ["entidad", "territorio"] si subset>10
    message: str | None = None     # ej. "Hay 746 datasets de Salud. Marcá otro chip para refinar."


# ============================================================
# Hito 1 / Fase B — Motor SoQL determinista
# ============================================================


SemanticType = Literal["geo", "fecha", "metrica", "dimension", "exclude"]
Confidence = Literal["high", "medium", "low"]


class CuratedColumn(BaseModel):
    """Una columna de un dataset, con su clasificación semántica curada
    (`dataset_columns_curated`, ver migración 004)."""

    col_name: str
    socrata_data_type: str | None = None
    socrata_description: str | None = None
    semantic_type: SemanticType
    semantic_subtype: str | None = None
    confidence: Confidence


class DatasetCuratedColumns(BaseModel):
    """GET /api/v1/datasets/{id}/columns — columnas tipadas para construir
    SoQL determinista por TIPO. `by_type` es un índice por semantic_type
    ordenado por confidence DESC (high → medium → low) para que el
    selector tome la columna más confiable primero."""

    dataset_id: str
    columns: list[CuratedColumn]
    by_type: dict[SemanticType, list[str]]


class ChipsExecuteRequest(BaseModel):
    """POST /api/v1/query/chips/execute — ejecutar la consulta SoQL sobre
    el dataset elegido + TIPO. Sin LLM: build_soql + SodaClient."""

    dataset_id: str
    tipo: ChipTipo
    # Territorio opcional como filtro adicional (DIVIPOLA code o "macro:*").
    territorio: str | None = None


class ChipsExecuteResponse(BaseModel):
    """Respuesta del ejecutor SoQL determinista."""

    dataset_id: str
    tipo: ChipTipo
    soql: str                   # query exacta enviada a SODA (para transparencia)
    columns_used: list[str]     # columnas que el template eligió
    rows: list[dict]            # filas crudas de SODA
    row_count: int              # len(rows), por conveniencia del cliente
    error: str | None = None    # mensaje si no se pudo construir o ejecutar


# ============================================================
# Hito 1 / Fase D — Narrativa LLM "Explicar" (ADR-017)
# ============================================================


class ChipsExplainRequest(BaseModel):
    """POST /api/v1/query/chips/explain — pide narrativa LLM sobre el
    resultado YA verificado. La cifra/filas vienen del cliente para evitar
    re-ejecutar (idempotente) y para que el LLM tenga el contexto exacto
    que el ciudadano está viendo en pantalla."""

    dataset_id: str
    dataset_name: str               # nombre legible
    tipo: ChipTipo
    rows: list[dict]                # filas tal como el motor las devolvió
    columns_used: list[str] = []


class ChipsFromNLRequest(BaseModel):
    """POST /api/v1/chips/from-nl — texto libre → combinación de chips
    pre-marcada. La respuesta es lo que el frontend usará como query params
    para navegar a /buscar."""

    q: str = Field(..., min_length=1, max_length=300)


class ChipsFromNLResponse(BaseModel):
    """Combinación inferida por el LLM. Cualquier campo puede ser null si
    el LLM no infirió con confianza."""

    tema: str | None = None
    tipo: ChipTipo | None = None
    territorio: str | None = None  # código DIVIPOLA o "macro:*"
    entidad: str | None = None     # entity_id como string
    refinador: str | None = None
    # Aviso para el usuario cuando la pregunta necesita algo que el sistema
    # no puede adivinar (p. ej. "mi ciudad" sin decir cuál).
    hint: str | None = None


class ChipsExplainResponse(BaseModel):
    """Texto corto explicando la cifra. El campo `hallucinated_numbers` lista
    los números que aparecieron en la respuesta pero NO están en `rows` —
    si no es vacío, la narrativa se censura."""

    dataset_id: str
    tipo: ChipTipo
    narrative: str                  # 2-3 frases; vacío si hubo hallucinación
    hallucinated_numbers: list[str] = []
    model: str                      # ej. "qwen2.5:3b-instruct"
    error: str | None = None


class CatalogStats(BaseModel):
    """GET /api/v1/stats/catalog — conteos del catálogo agregados desde la
    misma vista que alimenta el tablero Power BI (`v_dataset_status_decisor`),
    para que frontend y tablero nunca se desfasen. Todo es COUNT en vivo."""

    total: int                      # total de datasets en el catálogo
    nativos: int                    # es_federado='no' (Socrata datos.gov.co)
    federados: int                  # es_federado='sí' (CKAN/DCAT/IGAC)
    directo: int                    # acceso_datos='directo'
    requiere_herramienta: int       # acceso_datos='requiere_herramienta'
    solo_metadatos: int             # acceso_datos='solo_metadatos'
    consultable_tabla: int          # directo + requiere_herramienta
    util: int                       # quality_flag NULL/'ok' (no administrativo)
    admin: int                      # quality_flag='admin_only' (Ley 1712)


class SectorCount(BaseModel):
    """Agregado por sector administrativo (solo datasets con sector conocido)."""

    sector: str
    n_datasets: int
    n_entidades: int                # entidades distintas que publican en el sector


class DeptCount(BaseModel):
    """Agregado por departamento DIVIPOLA (datasets con jurisdicción identificada)."""

    codigo: str                     # DIVIPOLA 2 dígitos ("11", "05", ...)
    nombre: str                     # "Bogotá D.C.", "Antioquia", ...
    n_datasets: int


class PortalCount(BaseModel):
    """Agregado por portal de origen del catálogo integrado."""

    portal: str                     # hostname ("datos.gov.co", "datos.cali.gov.co", ...)
    n_datasets: int


class YearCumulative(BaseModel):
    """Punto de la línea de tiempo del catálogo: acumulado a fin de ese año."""

    anio: int
    acumulado: int


class PanoramaStats(BaseModel):
    """GET /api/v1/stats/panorama — panorama nacional para la home (ADR-023).

    Línea editorial sobre el CATÁLOGO COMPLETO (decisión 2026-07-10): `total`
    coincide con /stats/catalog. La división temáticos/administrativos
    (Ley 1712) se expone en `composicion` como una dimensión más del panorama.
    """

    total: int                      # todos los datasets del catálogo
    n_entidades: int                # entidades distintas que publican
    composicion: dict[str, int]     # tematicos / administrativos (Ley 1712)
    semaforo: dict[str, int]        # verde / amarillo / rojo / desconocido
    acceso: dict[str, int]          # directo / requiere_herramienta / solo_metadatos
    por_sector: list[SectorCount]   # top 10 por n_datasets
    por_departamento: list[DeptCount]  # hasta 33, orden n_datasets desc
    por_portal: list[PortalCount]   # catálogo integrado: nacional + territoriales
    nacional_sin_geo: int           # sin códigos DIVIPOLA (alcance nacional)
    generated_at: str               # ISO del momento de cómputo (caché TTL)
    # ISO de finished_at de la última corrida del ETL: la fecha que ve el
    # usuario en "Actualizado ...". generated_at es del caché, no del dato.
    last_etl_at: str | None = None
    # Línea de tiempo: acumulado de datasets por año de creación en su portal
    # de origen (para los anteriores al registro de DatosVivos es un estimado;
    # los años ≤2015 se agrupan en el primer punto).
    crecimiento: list[YearCumulative] = []
