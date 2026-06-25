"""Orquestador end-to-end: pregunta NL → análisis estructurado.

Pipeline (Sprint 5, post-journey-evaluation 2026-05-18):

1. `IntentClassifier` categoriza la pregunta (search, descriptive, comparative, ...)
2. **Retrieval híbrido**: `VectorIndex` + `DiscoveryClient` corren en paralelo;
   los datasets que aparecen en ambas listas reciben boost.
3. **Re-ranker LLM** (mitigación 2): de los top-K candidatos, el LLM elige el
   mejor (o pide reformular). Si rerank falla, se mantiene el orden original.
4. Para intent ≠ search: **ejecuta SoQL** vía `QueryGenerator` + `SodaClient`
   sobre el top dataset (mitigación 4). Si falla, narrativa basada solo en metadata.
5. **Narrativa constreñida** (mitigación 1): prompts que prohíben inventar
   países, cifras o contexto fuera de la metadata real del dataset.
6. Tier 3 fallback: si NADA supera el threshold, reformula con LLM.

Diseño:
- Inyección de dependencias en `__init__` — facilita testing con mocks
- Clientes de Socrata (Discovery, Metadata, Soda) y QueryGenerator son
  opcionales: si no se inyectan, se construyen con defaults. Esto preserva
  los tests legacy que solo inyectaban (vector, classifier, llm).
- Todo paso "nuevo" está envuelto en try/except con fallback al comportamiento
  anterior. Imposible regresión silenciosa: errores quedan en logs.
- Retorna `AnalysisResult` dataclass — interfaz estable para Streamlit.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

from typing import AsyncIterator, Literal

from ai_engine.curated_columns import load_curated_columns
from ai_engine.query_constraints import QueryConstraints, extract_constraints
from ai_engine.soql_templates import build_soql
from ai_engine.soql_verifier import verify_execution, verify_static
from ai_engine.geo_attribution import validate_geographic_attribution
from ai_engine.geo_resolver import GeoContext, GeoResolver, build_comparison_soql
from ai_engine.intent_classifier import IntentClassifier
from ai_engine.llm_backend import LLMBackend, model_for_task
from ai_engine.query_generator import QueryGenerator
from ai_engine.stats_computer import Statistics, StatsComputer, _normalize_number
from ai_engine.vector_index import SearchResult, VectorIndex
from mcp_server.socrata.discovery_client import DiscoveryClient
from mcp_server.socrata.metadata_client import MetadataClient
from mcp_server.socrata.soda_client import SodaClient

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class NarrativeStreamEvent:
    """Evento emitido por `_narrate_with_data_stream`.

    `kind`:
      - "summary": chunk del resumen (3 frases, sin bloque verificado).
      - "extended": chunk de la narrativa completa (incluye bloque verificado al cierre).
      - "extended_correction": versión censurada del extended (si hubo cifras no autorizadas).
      - "stats": evento final con el Statistics calculado.
    `done`: True si es el último chunk de ese kind.
    `stats`: solo para kind="stats".
    """

    kind: Literal["summary", "extended", "extended_correction", "stats"]
    text: str
    done: bool = False
    stats: Statistics | None = None


# Boost aplicado al score del vector index cuando el mismo dataset aparece
# en la Discovery API. Empírico — ver journey evaluation 2026-05-18.
DISCOVERY_BOOST = 0.05

# Boost aplicado a hits cuyo nombre/descripción mencione el territorio resuelto
# por GeoResolver. Mismo orden de magnitud que DISCOVERY_BOOST — efectos
# acumulables si un dataset aparece en Discovery Y menciona el territorio.
GEO_BOOST = 0.08

# Boost FUERTE a DIVIPOLA cuando la pregunta pide conteo de mpios/dptos.
# Razón: el journey 2026-05-21 mostró que sin este boost el retrieval trae
# datasets temáticos de Antioquia (víctimas, contratación, salud) que NO
# tienen columna `cod_dpto` correcta, hace fallar la plantilla SoQL del
# count_in y el LLM 3B inventa columnas → 0 resultados a P1 (Antioquia=125).
# Es alto a propósito (~5x DISCOVERY_BOOST) para que un DIVIPOLA con score
# bajo supere datasets temáticos con score alto en este caso específico.
DIVIPOLA_BOOST = 0.30
# Boost extra cuando el ID es exacto al oficial DANE (`gdxc-w37w`).
DIVIPOLA_BOOST_OFFICIAL_EXTRA = 0.10

# Regex que detecta cuándo la pregunta pide conteo de mpios/dptos como
# entidades geográficas (no como filtro temático).
import re as _re
_DIVIPOLA_QUESTION_PATTERN = _re.compile(
    r"\b(municipios?|departamentos?)\b",
    _re.IGNORECASE,
)

# IDs de datasets oficiales DIVIPOLA conocidos (mantener corto y verificado).
_DIVIPOLA_OFFICIAL_IDS = frozenset({
    "gdxc-w37w",  # DANE — Codificación de la División Político Administrativa
})


def divipola_boost_amount(question: str, hit) -> float:
    """Boost extra para datasets DIVIPOLA cuando la pregunta es conteo geo.

    Activación:
    - Pregunta menciona "municipio(s)" o "departamento(s)" como palabra clave.
    - Hit es el ID oficial DIVIPOLA o tiene "DIVIPOLA" en nombre/descripción.

    Devuelve 0.0 si no aplica.
    """
    if not _DIVIPOLA_QUESTION_PATTERN.search(question):
        return 0.0
    is_official = hit.id in _DIVIPOLA_OFFICIAL_IDS
    haystack = (hit.name + " " + (getattr(hit, "description", "") or "")).upper()
    has_divipola = "DIVIPOLA" in haystack
    if not (is_official or has_divipola):
        return 0.0
    boost = DIVIPOLA_BOOST
    if is_official:
        boost += DIVIPOLA_BOOST_OFFICIAL_EXTRA
    return boost

# Intents que disparan ejecución de SoQL contra el top dataset (no solo narrar metadata).
INTENTS_REQUIRING_DATA = {"descriptive", "comparative", "temporal", "cross_source"}

# URL canónica del catálogo público para que el ciudadano pueda acceder al dataset.
# datos.gov.co expone `/d/{id}` como página humana del dataset (incluye descarga).
DATASET_PAGE_URL = "https://www.datos.gov.co/d/{id}"
DATASET_API_URL = "https://www.datos.gov.co/resource/{id}.json"


@dataclass
class DatasetReference:
    """Referencia citable a un dataset usado en la respuesta.

    Permite que la interfaz construya enlaces verificables — el ciudadano
    puede abrir la fuente y reusar los datos. Trazabilidad por diseño.
    """

    id: str
    name: str
    entity: str | None
    url: str  # página humana en datos.gov.co
    api_url: str  # endpoint JSON SODA

    def __getitem__(self, key: str):
        return getattr(self, key)


def _build_reference(hit_id: str, name: str, entity: str | None) -> DatasetReference:
    return DatasetReference(
        id=hit_id,
        name=name or hit_id,
        entity=entity,
        url=DATASET_PAGE_URL.format(id=hit_id),
        api_url=DATASET_API_URL.format(id=hit_id),
    )


@dataclass
class AnalysisResult:
    """Resultado estructurado del análisis. Estable para Streamlit/Power BI."""

    question: str
    intent: str
    datasets_used: list[str] = field(default_factory=list)
    dataset_references: list[DatasetReference] = field(default_factory=list)
    soql_executed: str | None = None
    rows: list[dict[str, Any]] = field(default_factory=list)
    narrative: str = ""
    statistics: Statistics | None = None
    geo_context: GeoContext | None = None
    # Top hit del retrieval (SearchResult, con description). Útil para que el
    # caller invoque `_narrate_with_data_stream` en modo streaming si quiere
    # emitir tokens al cliente conforme llegan. Si `narrative` está vacío y
    # `top_hit` no es None, el caller debe invocar el stream para generarla.
    top_hit: SearchResult | None = None
    # Score del top hit del retrieval (post-boost). Lo usa el refusal (ADR-022 §3)
    # para rehusar cuando la confianza de recuperación es baja, y la telemetría.
    top_hit_score: float | None = None
    # Verificación de la consulta generada (ADR-022 Fase 3). `soql_verified=True`
    # por defecto para los caminos que no generan SoQL (search/metadata).
    soql_verified: bool = True
    soql_repairs: int = 0
    soql_layer_failed: str | None = None  # 'syntax'|'execution'|'semantic' si no verificó
    soql_fallback: str | None = None  # "template" si se degradó al motor determinista
    columns_used: list[str] = field(default_factory=list)
    # Refusal (ADR-022 Fase 4): el sistema rehúsa afirmar una cifra no verificable.
    refusal: bool = False
    refusal_reason: str | None = None

    def __getitem__(self, key: str):
        # Soporte dict-like para tests que usan result["intent"], etc.
        return getattr(self, key)

    def get(self, key: str, default=None):
        return getattr(self, key, default)


# ----------------------------------------------------------------------
# Post-validador de cifras (whitelist enforcement)
# ----------------------------------------------------------------------

# Token que parece una cifra: secuencia con dígitos y posibles separadores
# es-CO o ingleses. Excluimos secuencias precedidas por letra o guion (IDs
# como `gdxc-w37w` no son cifras estadísticas).
_NUMBER_IN_TEXT_RE = re.compile(
    r"(?<![A-Za-z0-9_-])-?\d[\d\.,]*"
)

# Sentinelas para sustitución de oraciones censuradas.
_CENSURE_MARKER = "[afirmación no verificable retirada por el sistema de seguridad]"
_FALLBACK_TEXT = (
    "Consulta el bloque de datos verificados a continuación para obtener "
    "las cifras de tu consulta."
)


def _split_into_sentences(text: str) -> list[str]:
    """Divide texto en oraciones preservando puntuación. Pragmático, no perfecto."""
    if not text:
        return []
    # Marcar separadores conservando el delimitador.
    parts = re.split(r"(?<=[\.\?\!])\s+", text.strip())
    return [p for p in parts if p.strip()]


def _validate_numbers(text: str, stats: Statistics | None) -> str:
    """Censura oraciones con cifras fuera de la whitelist.

    - Si `stats` es None o vacío, exige que el texto NO tenga cifras
      (defensa para `_narrate_search_results` / `_narrate_metadata_only`).
    - Las cifras en `stats.whitelist_numbers` o `stats.derived_numbers`
      (normalizadas) son citables.
    - Si todas las oraciones se censuran, devuelve un fallback determinista.
    - Errores de normalización: log warning y dejar la cifra pasar (mejor
      texto con cifra que texto vacío).
    """
    if not text:
        return text

    if stats is None:
        whitelist: frozenset[str] = frozenset()
        derived: frozenset[str] = frozenset()
    else:
        whitelist = stats.whitelist_numbers
        derived = stats.derived_numbers

    sentences = _split_into_sentences(text)
    kept: list[str] = []
    for sentence in sentences:
        numbers = _NUMBER_IN_TEXT_RE.findall(sentence)
        bad = False
        for n in numbers:
            if _number_in_whitelist(n, whitelist, derived):
                continue
            log.info("Cifra censurada: %r en oración: %r", n, sentence[:120])
            bad = True
            break
        if not bad:
            kept.append(sentence)

    if not kept:
        return _FALLBACK_TEXT
    return " ".join(kept)


def _number_in_whitelist(
    raw: str, whitelist: frozenset[str], derived: frozenset[str]
) -> bool:
    """True si `raw` (cifra extraída del texto) está autorizada en whitelist/derived.

    Prueba múltiples representaciones para robustez:
    - raw tal cual (puede coincidir con el formato que el LLM copió de la ficha).
    - canonical via `_normalize_number`.
    - representación integer si la canónica es entero (ej. "50.0" → "50").
    - representación con `.0` si la canónica es entero (ej. "50" → "50.0").
    """
    candidates = {raw, raw.strip()}
    try:
        canonical = _normalize_number(raw)
    except Exception as exc:  # noqa: BLE001
        log.warning("normalize_number failed (%s) for %r — dejo pasar", exc, raw)
        return True  # mejor permisivo que romper
    if canonical:
        candidates.add(canonical)
        try:
            as_float = float(canonical)
            if as_float.is_integer():
                candidates.add(str(int(as_float)))
                candidates.add(str(int(as_float)) + ".0")
            else:
                candidates.add(str(as_float))
        except ValueError:
            pass
    return any(c in whitelist or c in derived for c in candidates if c)


_REFUSAL_MESSAGE = (
    "No puedo darte una cifra confiable para esta pregunta con los datos "
    "disponibles. Encontré datasets relacionados, pero no logré construir una "
    "consulta verificada que la responda con precisión. DatosVivos prefiere "
    "decir esto a darte un número que podría estar respondiendo otra cosa. "
    "Probá reformular (por ejemplo, especificando el periodo, el territorio o la "
    "medida exacta) o revisá los datasets citados abajo."
)


@dataclass
class SoqlOutcome:
    """Resultado del bucle de generación+verificación de SoQL (ADR-022 Fase 3-5).

    Lo produce `_execute_soql`; lo consumen la construcción del `AnalysisResult`,
    el evento `interpretation` ("esto entendí", Fase 5) y la decisión de
    refusal/degradación (Fase 4).
    """

    soql: str
    rows: list[dict[str, Any]]
    verified: bool
    repairs: int = 0
    layer_failed: str | None = None
    fallback: str | None = None  # "template" cuando se degradó al motor determinista
    refused: bool = False  # True si se rehúsa afirmar cifra (no verificable)
    refusal_reason: str | None = None  # "unverifiable" | "missing_columns" | ...
    columns_used: list[str] = field(default_factory=list)
    constraints: QueryConstraints | None = None
    curated_columns: list[dict[str, Any]] = field(default_factory=list)


class Analyzer:
    """Orquesta el motor de IA: intent → recuperación → re-ranking → SoQL → narrativa."""

    def __init__(
        self,
        vector_index: VectorIndex,
        intent_classifier: IntentClassifier,
        llm_backend: LLMBackend,
        *,
        top_k_datasets: int = 5,
        discovery_client: DiscoveryClient | None = None,
        metadata_client: MetadataClient | None = None,
        soda_client: SodaClient | None = None,
        query_generator: QueryGenerator | None = None,
        geo_resolver: GeoResolver | None = None,
        enable_hybrid_retrieval: bool = True,
        enable_rerank: bool = True,
        enable_soql_execution: bool = True,
        enable_geo_context: bool = True,
    ) -> None:
        self.vector_index = vector_index
        self.intent_classifier = intent_classifier
        self.llm = llm_backend
        self.top_k_datasets = top_k_datasets

        # Clientes Socrata — defaults seguros (no se conectan hasta que se usan).
        self.discovery = discovery_client or DiscoveryClient()
        self.metadata = metadata_client or MetadataClient()
        self.soda = soda_client or SodaClient()
        self.query_gen = query_generator or QueryGenerator(backend=llm_backend)
        self.geo_resolver = geo_resolver or GeoResolver()

        self.enable_hybrid_retrieval = enable_hybrid_retrieval
        self.enable_rerank = enable_rerank
        self.enable_soql_execution = enable_soql_execution
        self.enable_geo_context = enable_geo_context

        # Reparaciones máximas del bucle de verificación (ADR-022 Fase 3).
        # 1 intento inicial + N reparaciones = hasta N+1 llamadas LLM peor caso.
        self._max_query_repairs = int(os.getenv("QUERY_MAX_REPAIRS", "4"))
        # Rehusar (no afirmar cifra) cuando la consulta no se verifica ni se puede
        # degradar a template (ADR-022 Fase 4, "precisión sobre cobertura").
        self._refuse_unverified = os.getenv("QUERY_REFUSE_UNVERIFIED", "1") not in ("0", "false", "False")

    async def analyze(
        self, question: str, *, defer_narrative: bool = False
    ) -> AnalysisResult:
        """Pipeline completo. Devuelve resultado estructurado.

        `defer_narrative=True`: skip la llamada LLM para narrative cuando el
        path es `intent ∈ INTENTS_REQUIRING_DATA + SoQL exitoso`. El caller
        recibe `top_hit` poblado y debe invocar `_narrate_with_data_stream`
        para emitir tokens al cliente (modo streaming SSE). Útil para
        `api/routes/query.py` que prefiere TTFB ≤ 1s sobre tener la narrativa
        ya armada.
        Otros paths (no_matches, narrate_metadata_only, narrate_search) NO
        difieren — generan narrativa inline para mantener simplicidad.
        """
        question = (question or "").strip()
        if not question:
            return AnalysisResult(
                question="",
                intent="search",
                narrative="Pregunta vacía — provee una consulta en lenguaje natural.",
            )

        intent = self.intent_classifier.classify(question)
        log.info("Intent: %s | Pregunta: %s", intent, question[:80])

        # 0) Resolver contexto geográfico (opt-in por contenido).
        geo_ctx: GeoContext | None = None
        if self.enable_geo_context:
            try:
                geo_ctx = self.geo_resolver.resolve(question)
                if geo_ctx is not None:
                    log.info(
                        "GeoContext: dpto=%s mpio=%s scope=%s groupby=%s",
                        geo_ctx.dpto_code,
                        geo_ctx.mpio_code,
                        geo_ctx.scope,
                        geo_ctx.groupby,
                    )
            except Exception as exc:  # noqa: BLE001
                log.warning("GeoResolver falló (%s); sigo sin contexto geo.", exc)

        # 1) Retrieval híbrido (vector + Discovery en paralelo).
        hits = await self._retrieve(question, geo_ctx)
        reformulated_query: str | None = None

        # 2) Tier 3 fallback: si vector y discovery vinieron vacíos, reformulamos.
        if not hits:
            reformulated_query = await self._llm_reformulate(question)
            if reformulated_query and reformulated_query.strip() != question:
                log.info("Tier 3 fallback: query reformulada por LLM → %r", reformulated_query)
                hits = await self._retrieve(reformulated_query, geo_ctx)

        if not hits:
            return AnalysisResult(
                question=question,
                intent=intent,
                datasets_used=[],
                dataset_references=[],
                narrative=self._deterministic_no_matches(question),
                geo_context=geo_ctx,
            )

        # 3) Re-ranking con LLM (elige el top-1 más relevante para la pregunta).
        if self.enable_rerank and len(hits) > 1:
            try:
                hits = await self._rerank_with_llm(question, hits)
            except Exception as exc:  # noqa: BLE001 — rerank no debe tumbar el pipeline
                log.warning("Rerank LLM falló (%s); manteniendo orden vector.", exc)

        # Si el rerank dijo "NINGUNO" (hits == []), caemos a no_matches igual
        # que en el path inicial. Antes este caso producía IndexError.
        if not hits:
            return AnalysisResult(
                question=question,
                intent=intent,
                datasets_used=[],
                dataset_references=[],
                narrative=self._deterministic_no_matches(question),
                geo_context=geo_ctx,
            )

        datasets_used = [h.id for h in hits]
        dataset_references = [_build_reference(h.id, h.name, h.entity) for h in hits]

        # 4) Si intent requiere DATOS (no solo catálogo), ejecutar SoQL.
        if intent in INTENTS_REQUIRING_DATA and self.enable_soql_execution:
            soql_result = await self._execute_soql(question, hits[0], geo_ctx)
            if soql_result is not None and soql_result.refused:
                # ADR-022 Fase 4: rehusar es preferible a afirmar una cifra que
                # responde otra pregunta. No se ejecuta ni se narra una cifra.
                return AnalysisResult(
                    question=question,
                    intent=intent,
                    datasets_used=datasets_used,
                    dataset_references=dataset_references,
                    narrative=_REFUSAL_MESSAGE,
                    geo_context=geo_ctx,
                    top_hit=hits[0],
                    top_hit_score=hits[0].score,
                    soql_verified=False,
                    soql_layer_failed=soql_result.layer_failed,
                    refusal=True,
                    refusal_reason=soql_result.refusal_reason,
                )
            if soql_result is not None:
                soql, rows = soql_result.soql, soql_result.rows
                if defer_narrative:
                    # Modo streaming: el caller invoca `_narrate_with_data_stream`.
                    # No llamamos al LLM acá — solo computamos stats con pandas
                    # (rápido, determinista) para que el caller los emita en el
                    # bloque verificado.
                    stats = StatsComputer.compute(rows, soql)
                    return AnalysisResult(
                        question=question,
                        intent=intent,
                        datasets_used=datasets_used,
                        dataset_references=dataset_references,
                        soql_executed=soql,
                        rows=rows,
                        narrative="",  # caller emitirá streaming
                        statistics=stats,
                        geo_context=geo_ctx,
                        top_hit=hits[0],
                        top_hit_score=hits[0].score,
                        soql_verified=soql_result.verified,
                        soql_repairs=soql_result.repairs,
                        soql_layer_failed=soql_result.layer_failed,
                        soql_fallback=soql_result.fallback,
                        columns_used=soql_result.columns_used,
                    )
                narrative, stats = await self._narrate_with_data(
                    question, hits[0], soql, rows, geo_ctx=geo_ctx
                )
                return AnalysisResult(
                    question=question,
                    intent=intent,
                    datasets_used=datasets_used,
                    dataset_references=dataset_references,
                    soql_executed=soql,
                    rows=rows,
                    narrative=narrative,
                    statistics=stats,
                    geo_context=geo_ctx,
                    top_hit=hits[0],
                    top_hit_score=hits[0].score,
                    soql_verified=soql_result.verified,
                    soql_repairs=soql_result.repairs,
                    soql_layer_failed=soql_result.layer_failed,
                    soql_fallback=soql_result.fallback,
                    columns_used=soql_result.columns_used,
                )
            # Si SoQL falló, caemos al placeholder constreñido.
            narrative = await self._narrate_metadata_only(question, intent, hits)
            return AnalysisResult(
                question=question,
                intent=intent,
                datasets_used=datasets_used,
                dataset_references=dataset_references,
                narrative=narrative,
                geo_context=geo_ctx,
            )

        # 5) Para intent=search, la respuesta es el catálogo + narrativa de catálogo.
        if intent == "search":
            narrative = await self._narrate_search_results(question, hits)
            return AnalysisResult(
                question=question,
                intent=intent,
                datasets_used=datasets_used,
                dataset_references=dataset_references,
                narrative=narrative,
                geo_context=geo_ctx,
            )

        # Fallback (no debería ocurrir si INTENTS_REQUIRING_DATA cubre todo lo no-search).
        narrative = await self._narrate_metadata_only(question, intent, hits)
        return AnalysisResult(
            question=question,
            intent=intent,
            datasets_used=datasets_used,
            dataset_references=dataset_references,
            narrative=narrative,
            geo_context=geo_ctx,
        )

    # ------------------------------------------------------------
    # Retrieval híbrido (mitigación 3)
    # ------------------------------------------------------------

    async def _retrieve(
        self, question: str, geo_ctx: GeoContext | None = None
    ) -> list[SearchResult]:
        """Recupera del vector index y, en paralelo, de Discovery API.

        Boost aplicado a IDs que aparezcan en ambas listas — están indicados
        tanto por similitud semántica como por matching directo de Socrata.

        Si `geo_ctx` resolvió un departamento/municipio, agregamos un boost
        adicional a los hits cuyo nombre/descripción mencione ese territorio.
        """
        vector_hits = self.vector_index.search(question, k=self.top_k_datasets)

        # Inyección forzada de DIVIPOLA cuando el patrón de pregunta lo
        # justifica. El embedding semántico NO asocia "DIVIPOLA" con
        # preguntas tipo "¿cuántos municipios tiene Antioquia?", entonces
        # gdxc-w37w nunca aparece en top-k aunque sea la fuente correcta.
        # Inyectamos manualmente al inicio para que el boost lo eleve a top.
        if _DIVIPOLA_QUESTION_PATTERN.search(question):
            already_present = any(h.id == "gdxc-w37w" for h in vector_hits)
            if not already_present:
                divipola_hit = self.vector_index.get_by_id("gdxc-w37w")
                if divipola_hit is not None:
                    vector_hits = [divipola_hit] + vector_hits
                    log.info("Inyectado gdxc-w37w (DIVIPOLA) al retrieval para pregunta de conteo geo")

        if not self.enable_hybrid_retrieval:
            return vector_hits

        try:
            # Timeout corto: si Discovery no responde rápido, seguimos solo con vector.
            # Esto también protege tests offline / sandboxed.
            discovery_results = await asyncio.wait_for(
                self.discovery.search(query=question, limit=10),
                timeout=5.0,
            )
        except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001
            log.warning("Discovery API falló o timeout (%s); usando solo vector.", exc)
            return vector_hits

        discovery_ids = set()
        for r in discovery_results:
            resource = r.get("resource") or {}
            did = resource.get("id")
            if did:
                discovery_ids.add(did)

        if not discovery_ids:
            return vector_hits

        # Boost a hits que también aparecen en Discovery + boost geográfico
        # si geo_ctx menciona un territorio que aparece en el nombre/desc +
        # boost FUERTE a DIVIPOLA si la pregunta pide conteo de mpios/dptos +
        # **penalty si entity menciona OTRO territorio** que no es el del ctx
        # (fix #3 atribución geográfica 2026-05-22: "Estudiantes de Bogotá"
        # traía UPTC = Boyacá. La entity "Universidad Pedagógica y Tecnológica
        # de Colombia" no menciona Bogotá pero el embedding semántico la
        # priorizaba). Penalty alto baja datasets institucionales que NO son
        # del territorio preguntado.
        geo_tokens = self._geo_match_tokens(geo_ctx)
        other_territory_tokens = self._other_territory_tokens(geo_ctx)
        boosted: list[SearchResult] = []
        for h in vector_hits:
            score_delta = 0.0
            if h.id in discovery_ids:
                score_delta += DISCOVERY_BOOST
            entity_lc = (h.entity or "").lower()
            name_desc_lc = (h.name + " " + (h.description or "")).lower()
            if geo_tokens:
                if any(tok in name_desc_lc for tok in geo_tokens):
                    score_delta += GEO_BOOST
            # Penalty si entity menciona explícitamente otro depto/mpio.
            if other_territory_tokens and any(
                tok in entity_lc for tok in other_territory_tokens
            ):
                score_delta -= GEO_BOOST  # mismo orden de magnitud que el boost positivo
            score_delta += divipola_boost_amount(question, h)
            if score_delta:
                boosted.append(
                    SearchResult(
                        id=h.id,
                        name=h.name,
                        entity=h.entity,
                        score=h.score + score_delta,
                        description=h.description,
                        category=h.category,
                    )
                )
            else:
                boosted.append(h)

        # Re-ordenar por score (estable).
        boosted.sort(key=lambda r: r.score, reverse=True)
        return boosted

    @staticmethod
    def _geo_match_tokens(geo_ctx: GeoContext | None) -> list[str]:
        """Tokens en lowercase que indican mención del territorio en metadata."""
        if geo_ctx is None:
            return []
        tokens: set[str] = set()
        if geo_ctx.dpto_name:
            tokens.add(geo_ctx.dpto_name.lower())
        if geo_ctx.mpio_name:
            tokens.add(geo_ctx.mpio_name.lower())
        return [t for t in tokens if t]

    @staticmethod
    def _other_territory_tokens(geo_ctx: GeoContext | None) -> list[str]:
        """Departamentos colombianos QUE NO SON el del ctx. Útil para penalizar
        datasets cuya entity claramente menciona otro territorio.

        Ej: pregunta "Estudiantes de Bogotá" → ctx.dpto=Bogotá. Si entity dice
        "Universidad Pedagógica y Tecnológica de Colombia" (no menciona otro
        territorio explícitamente), penalty no se aplica. Pero si dice
        "Gobernación de Boyacá" o "Universidad del Valle", sí.
        """
        if geo_ctx is None:
            return []
        # Lista corta de dptos con nombres potencialmente ambiguos en
        # entity strings (capitales del país que tienden a aparecer en
        # nombres de universidades, gobernaciones, etc.).
        all_dpto_names = {
            "antioquia", "atlántico", "atlantico", "bogotá", "bogota",
            "bolívar", "bolivar", "boyacá", "boyaca", "caldas", "caquetá",
            "caqueta", "cauca", "cesar", "córdoba", "cordoba", "cundinamarca",
            "chocó", "choco", "huila", "guajira", "magdalena", "meta",
            "nariño", "narino", "norte de santander", "quindío", "quindio",
            "risaralda", "santander", "sucre", "tolima", "valle del cauca",
            "valle", "arauca", "casanare", "putumayo", "amazonas", "guainía",
            "guainia", "guaviare", "vaupés", "vaupes", "vichada", "san andrés",
            "san andres",
        }
        excluded = set()
        if geo_ctx.dpto_name:
            excluded.add(geo_ctx.dpto_name.lower())
        if geo_ctx.mpio_name:
            excluded.add(geo_ctx.mpio_name.lower())
        return sorted(all_dpto_names - excluded)

    # ------------------------------------------------------------
    # Re-ranker LLM (mitigación 2)
    # ------------------------------------------------------------

    async def _rerank_with_llm(
        self, question: str, hits: list[SearchResult]
    ) -> list[SearchResult]:
        """Pide al LLM que elija el mejor de los hits para la pregunta.

        Si el LLM no produce un índice válido, devuelve el orden original.
        Si el LLM dice explícitamente "ninguno", devuelve la lista vacía.
        """
        if not hits:
            return hits
        items = "\n".join(
            f"  [{i}] {h.id} — {h.name} (entidad: {h.entity or 'N/D'})"
            for i, h in enumerate(hits[: self.top_k_datasets])
        )
        prompt = (
            "Eres un experto en datos abiertos de Colombia. De la siguiente "
            "lista de datasets candidatos, elige el más relevante para la "
            "pregunta del ciudadano. Responde SOLO con el número entre "
            "corchetes (ej: 2) o la palabra NINGUNO si ninguno aplica.\n\n"
            f"Pregunta: {question!r}\n\n"
            f"Candidatos:\n{items}\n\n"
            "Respuesta (solo el número o NINGUNO):"
        )
        try:
            raw = await self.llm.generate(
                prompt,
                max_tokens=10,
                model=model_for_task("rerank"),
                temperature=0.0,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Rerank LLM error: %s", exc)
            return hits

        raw_clean = (raw or "").strip().upper()
        if raw_clean.startswith("NINGUNO") or raw_clean.startswith("NONE"):
            # Antes devolvíamos []; en sesión exploratoria 2026-05-18 detectamos
            # falsos negativos del LLM 3B (decía 'NINGUNO' aunque el retrieval
            # traía datasets relevantes — caso P6 'Cuántas instituciones de
            # salud hay en Chocó' devolvió 0 datasets de la nada).
            # Mitigación: conservar el top-1 con disclaimer. El threshold del
            # vector index (min_score=0.83) ya filtró ruido antes de llegar acá.
            log.info(
                "Rerank LLM dice 'NINGUNO'; conservando top-1 (el LLM 3B "
                "tiende a falsos negativos)."
            )
            return hits[:1]

        m = re.search(r"\d+", raw_clean)
        if not m:
            log.info("Rerank LLM no devolvió índice parseable (%r); mantengo orden.", raw)
            return hits
        idx = int(m.group())
        if 0 <= idx < len(hits):
            chosen = hits[idx]
            others = [h for i, h in enumerate(hits) if i != idx]
            return [chosen, *others]
        log.info("Rerank LLM índice fuera de rango (%d); mantengo orden.", idx)
        return hits

    # ------------------------------------------------------------
    # Ejecución de SoQL (mitigación 4)
    # ------------------------------------------------------------

    async def _execute_soql(
        self, question: str, top: SearchResult, geo_ctx: GeoContext | None = None
    ) -> "SoqlOutcome | None":
        """Para intents no-search: obtener schema, generar SoQL, verificar, ejecutar.

        Si `geo_ctx` resolvió un territorio, agregamos al prompt una pista
        explícita con el código DIVIPOLA para que el LLM use ese filtro
        (en lugar de inventar columnas).

        Devuelve (soql, rows) si la cadena completa funciona; None si falla
        cualquier paso. Los errores se loggean y caen al narrative-de-metadata.
        """
        try:
            meta = await self.metadata.get(top.id)
        except Exception as exc:  # noqa: BLE001
            log.warning("Metadata API falló para %s: %s", top.id, exc)
            return None

        try:
            sample_rows = await self.soda.query(dataset_id=top.id, limit=2)
        except Exception as exc:  # noqa: BLE001
            log.warning("Sample query falló para %s: %s", top.id, exc)
            sample_rows = []

        schema = {
            "columns": meta.get("columns") or [],
            "sample_rows": sample_rows,
        }
        if not schema["columns"]:
            log.warning("Schema vacío para %s; no se puede generar SoQL.", top.id)
            return None

        # Columnas con tipo semántico (ADR-022 Fase 1): fuente de verdad
        # `dataset_columns_curated`; si el dataset no está curado, se clasifica
        # al vuelo desde la Metadata API. Las consume el verificador de 3 capas
        # (Fase 2) y la degradación a template determinista (Fase 4).
        schema["curated_columns"] = load_curated_columns(top.id, schema["columns"])

        col_names = {
            (c.get("field_name") or c.get("fieldName") or c.get("name") or "").lower()
            for c in schema["columns"]
        }

        # --- (1) Plantilla determinista para comparativas ---
        # Si geo_ctx tiene comparison_mode, intentar SoQL pre-construido sin LLM.
        if geo_ctx is not None and geo_ctx.comparison_mode is not None:
            templated_soql = build_comparison_soql(geo_ctx, col_names)
            if templated_soql:
                log.info(
                    "SoQL determinista (mode=%s): %s",
                    geo_ctx.comparison_mode,
                    templated_soql,
                )
                try:
                    rows = await self.soda.query(
                        dataset_id=top.id, soql_query=templated_soql
                    )
                    # Plantilla determinista (build_comparison_soql) → correcta por
                    # construcción. ADR-022: devolver SoqlOutcome verificado, no una
                    # tupla (el caller espera SoqlOutcome).
                    return SoqlOutcome(
                        soql=templated_soql,
                        rows=rows[:50],
                        verified=True,
                        fallback="template",
                        constraints=extract_constraints(
                            question,
                            has_geo_filter=bool(
                                geo_ctx and (geo_ctx.dpto_code or geo_ctx.mpio_code)
                            ),
                        ),
                        curated_columns=schema.get("curated_columns", []),
                    )
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "SoQL determinista falló (%s): %s — caigo a query_gen LLM",
                        templated_soql,
                        exc,
                    )

        # --- (2) Fallback: query_gen LLM con hints de geo si aplican ---
        # Construir la pregunta-con-geo-hint para el query_generator.
        # Fix #2 atribución (2026-05-22): cobertura ampliada de columnas
        # territoriales (codigo_dane_departamento, departamento, etc.) +
        # hint reforzado como OBLIGATORIO para que el LLM no ignore el
        # filtro geográfico (causa raíz del bug "Estudiantes Bogotá → 6
        # de UPTC Boyacá").
        question_for_gen = question
        if geo_ctx is not None and (geo_ctx.dpto_code or geo_ctx.mpio_code):
            hint_parts: list[str] = []
            # Buscar la columna territorial disponible en el dataset.
            mpio_code_cols = ("cod_mpio", "codigo_mpio", "codigo_municipio", "codigo_dane_municipio")
            mpio_name_cols = ("municipio", "nombre_municipio", "nom_mpio", "mpio_nombre")
            dpto_code_cols = ("cod_dpto", "codigo_dpto", "codigo_departamento", "codigo_dane_departamento")
            dpto_name_cols = ("departamento", "nombre_departamento", "nom_dpto", "depto", "depa_nombre")

            if geo_ctx.mpio_code:
                col = next((c for c in mpio_code_cols if c in col_names), None)
                if col:
                    hint_parts.append(
                        f"WHERE {col} = '{geo_ctx.mpio_code}' (DIVIPOLA "
                        f"para {geo_ctx.mpio_name})"
                    )
                else:
                    col = next((c for c in mpio_name_cols if c in col_names), None)
                    if col:
                        hint_parts.append(
                            f"WHERE lower({col}) = '{(geo_ctx.mpio_name or '').lower()}'"
                        )
            elif geo_ctx.dpto_code:
                col = next((c for c in dpto_code_cols if c in col_names), None)
                if col:
                    hint_parts.append(
                        f"WHERE {col} = '{geo_ctx.dpto_code}' (DIVIPOLA "
                        f"para {geo_ctx.dpto_name})"
                    )
                else:
                    col = next((c for c in dpto_name_cols if c in col_names), None)
                    if col:
                        hint_parts.append(
                            f"WHERE upper({col}) = '{(geo_ctx.dpto_name or '').upper()}'"
                        )
            if geo_ctx.groupby and geo_ctx.groupby in col_names:
                hint_parts.append(f"GROUP BY {geo_ctx.groupby}")
            if hint_parts:
                question_for_gen = (
                    f"{question}\n\n"
                    f"FILTRO GEOGRÁFICO OBLIGATORIO: el ciudadano preguntó "
                    f"por **{geo_ctx.mpio_name or geo_ctx.dpto_name}**. "
                    f"Tu SoQL DEBE incluir: "
                    + "; ".join(hint_parts)
                    + ". Sin este WHERE, el resultado NO corresponde a la "
                    f"pregunta y será rechazado."
                )

        try:
            qr = await self.query_gen.generate(question_for_gen, schema)
        except Exception as exc:  # noqa: BLE001
            log.warning("QueryGenerator falló: %s", exc)
            return None

        soql = (qr.soql or "").strip()
        if not soql or soql == "SELECT * LIMIT 1":
            log.info("SoQL fallback vacío para %s; usando narrativa de metadata.", top.id)
            return None

        # --- Bucle de verificación + reparación (ADR-022 Fase 2-3) ---
        # Verifica que el SoQL responde la pregunta (capa 1 sintaxis + capa 3
        # restricciones semánticas) y, si no, lo repara de forma dirigida (sin
        # regenerar desde cero) hasta `_max_query_repairs` veces.
        curated = schema.get("curated_columns", [])
        constraints = extract_constraints(
            question,
            has_geo_filter=bool(geo_ctx and (geo_ctx.dpto_code or geo_ctx.mpio_code)),
        )
        verified = False
        repairs = 0
        layer_failed: str | None = None
        columns_used: list[str] = []
        for attempt in range(self._max_query_repairs + 1):
            vr = verify_static(
                soql, valid_cols=col_names, curated_columns=curated,
                constraints=constraints,
            )
            columns_used = sorted(vr.columns_referenced)
            if vr.ok:
                verified = True
                break
            layer_failed = vr.layer_failed
            if attempt >= self._max_query_repairs:
                break
            try:
                repaired = await self.query_gen.repair(
                    question_for_gen, schema, soql, vr.error_message
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("Reparación LLM falló (%s): %s", top.id, exc)
                break
            if not repaired or repaired == soql or repaired == "SELECT * LIMIT 1":
                break
            soql = repaired
            repairs += 1

        # Capa 2 (ejecución barata, LIMIT 0) solo si pasó la estática: detecta
        # SoQL semánticamente OK pero que Socrata rechaza, y permite una reparación.
        if verified:
            ev = await verify_execution(soql, soda_client=self.soda, dataset_id=top.id)
            if not ev.ok and repairs < self._max_query_repairs:
                layer_failed = ev.layer_failed
                try:
                    repaired = await self.query_gen.repair(
                        question_for_gen, schema, soql, ev.error_message
                    )
                    if repaired and repaired != soql:
                        soql = repaired
                        repairs += 1
                        rv = verify_static(
                            soql, valid_cols=col_names, curated_columns=curated,
                            constraints=constraints,
                        )
                        columns_used = sorted(rv.columns_referenced)
                        if rv.ok:
                            ev2 = await verify_execution(
                                soql, soda_client=self.soda, dataset_id=top.id
                            )
                            verified = ev2.ok
                            layer_failed = None if ev2.ok else ev2.layer_failed
                        else:
                            verified = False
                            layer_failed = rv.layer_failed
                except Exception as exc:  # noqa: BLE001
                    log.warning("Reparación post-ejecución falló (%s): %s", top.id, exc)
                    verified = False
            elif not ev.ok:
                verified = False
                layer_failed = ev.layer_failed

        fallback: str | None = None
        if not verified:
            # (a) Degradación a template determinista (ADR-022 Fase 4): correcto por
            # construcción si la pregunta encaja en una de las 5 formas TIPO. NO se
            # degrada si la pregunta exige filtro geográfico — los templates no
            # filtran por valor y devolverían el total nacional como si fuera el
            # territorio (reintroduciría el bug de alcance equivocado).
            if constraints.tipo and not constraints.requires_geo_filter:
                built = build_soql(constraints.tipo, curated)
                if not built.error and built.soql:
                    log.info(
                        "Degradación a template TIPO=%s (%s): %s",
                        constraints.tipo, top.id, built.soql,
                    )
                    soql = built.soql
                    columns_used = list(built.columns_used)
                    verified = True
                    fallback = "template"
                    layer_failed = None

        if not verified:
            # (b) No verificable ni degradable → "precisión sobre cobertura":
            # rehusar afirmar una cifra dudosa cuando la consulta está rota
            # (sintaxis/ejecución) o cuando el dataset está curado (alta confianza
            # en los tipos). Si la falla es semántica sobre columnas SOLO inferidas
            # (sin curación), ser conservador y ejecutar marcando verified=False.
            authoritative = any(c.get("source") == "curated" for c in curated)
            should_refuse = self._refuse_unverified and (
                layer_failed in ("syntax", "execution") or authoritative
            )
            if should_refuse:
                log.warning(
                    "Rehúso por consulta no verificable [%s] %s", layer_failed, top.id
                )
                return SoqlOutcome(
                    soql=soql,
                    rows=[],
                    verified=False,
                    repairs=repairs,
                    layer_failed=layer_failed,
                    refused=True,
                    refusal_reason="unverifiable",
                    columns_used=columns_used,
                    constraints=constraints,
                    curated_columns=curated,
                )
            log.warning(
                "SoQL NO verificado [%s] %s tras %d reparación(es): %s — ejecuto "
                "(curación inferida, refusal conservador)",
                layer_failed, top.id, repairs, soql,
            )

        try:
            rows = await self.soda.query(dataset_id=top.id, soql_query=soql)
        except Exception as exc:  # noqa: BLE001
            log.warning("SodaClient.query falló (%s): %s", soql, exc)
            return None

        return SoqlOutcome(
            soql=soql,
            rows=rows[:50],
            verified=verified,
            repairs=repairs,
            layer_failed=None if verified else layer_failed,
            fallback=fallback,
            columns_used=columns_used,
            constraints=constraints,
            curated_columns=curated,
        )

    # ------------------------------------------------------------
    # Narrativas constreñidas (mitigación 1)
    # ------------------------------------------------------------

    _ANTI_HALLUCINATION_RULES = (
        "REGLAS ESTRICTAS:\n"
        "- Todo dato es del CATÁLOGO COLOMBIANO datos.gov.co. NO menciones "
        "otros países (Ecuador, Perú, Venezuela, etc.) salvo que aparezcan "
        "literalmente en la metadata listada arriba.\n"
        "- NO inventes cifras, fechas, totales ni categorías que no estén en "
        "los metadatos o filas proporcionadas.\n"
        "- Si la pregunta no es respondible con los datos disponibles, dilo "
        "explícitamente en una frase.\n"
        "- Responde en español, 3-5 frases máximo, sin markdown.\n"
    )

    async def _narrate_search_results(self, question: str, hits: list[SearchResult]) -> str:
        """LLM resume los datasets recuperados como respuesta a la pregunta.

        Aplica `_validate_numbers` con whitelist vacía: si el LLM intenta
        mencionar cifras, se censuran (este branch es solo catálogo, no datos).
        """
        items = "\n".join(
            f"- {h.id}: {h.name} (entidad: {h.entity or 'N/D'})" for h in hits[:5]
        )
        prompt = (
            f"Un ciudadano colombiano preguntó: {question!r}\n"
            f"Datasets más relevantes encontrados en datos.gov.co (catálogo colombiano):\n"
            f"{items}\n\n"
            f"{self._ANTI_HALLUCINATION_RULES}"
            "Indica qué datasets pueden servirle y por qué. NO incluyas cifras "
            "ni estadísticas — solo describe qué contiene cada dataset."
        )
        raw = await self.llm.generate(
            prompt, max_tokens=300, model=model_for_task("narrative")
        )
        return _validate_numbers(raw, None)

    def _deterministic_no_matches(self, question: str) -> str:
        """Respuesta SIN LLM cuando no hay datasets relevantes.

        Razón (journey 2026-05-18): Qwen 3B ignoraba la instrucción
        "NO inventes datasets" y producía datasets ficticios (ej. ecuatorianos
        cuando se preguntaba por Ecuador). Una respuesta determinista garantiza
        cero alucinación en este caso.
        """
        return (
            f"No encontré datasets relevantes en el catálogo de datos.gov.co "
            f"para tu consulta: «{question}». Te sugiero reformular con "
            f"palabras clave más específicas (por ejemplo, nombre del tema, "
            f"entidad publicadora, departamento o municipio). Recuerda que el "
            f"catálogo cubre datos públicos colombianos."
        )

    async def _narrate_metadata_only(
        self, question: str, intent: str, hits: list[SearchResult]
    ) -> str:
        """Fallback cuando SoQL no se ejecutó (o el intent no requería datos).

        Sin rows ejecutados, aplica `_validate_numbers` con whitelist vacía:
        cualquier cifra que el LLM mencione se censura.
        """
        top = hits[0]
        entity = top.entity or "entidad no declarada"
        desc = (top.description or "")[:300]
        prompt = (
            f"Pregunta del ciudadano colombiano: {question!r} (tipo: {intent}).\n"
            f"Dataset más relevante encontrado:\n"
            f"  - ID: {top.id}\n"
            f"  - Nombre: {top.name}\n"
            f"  - Entidad publicadora: {entity}\n"
            f"  - Descripción: {desc}\n\n"
            f"{self._ANTI_HALLUCINATION_RULES}"
            "Indica al ciudadano qué información contiene este dataset y "
            "sugiérele consultarlo. NO incluyas cifras ni estadísticas."
        )
        raw = await self.llm.generate(
            prompt, max_tokens=250, model=model_for_task("narrative")
        )
        return _validate_numbers(raw, None)

    # ------------------------------------------------------------
    # Narrativa: builders de prompt + bloque verificado
    # ------------------------------------------------------------

    @staticmethod
    def _build_summary_prompt(
        question: str,
        top: SearchResult,
        stats: Statistics,
        rows: list[dict[str, Any]],
    ) -> str:
        """Prompt CORTO para resumen ejecutivo (≤3 frases, ~120 tokens)."""
        numbered = "\n".join(
            f"  ({i + 1}) {line}" for i, line in enumerate(stats.summary_lines)
        )
        return (
            f"Pregunta del ciudadano colombiano: «{question}»\n"
            f"Dataset: {top.name}\n"
            f"Cifras autorizadas (calculadas con pandas):\n{numbered}\n\n"
            f"Responde en español, MÁXIMO 2-3 frases. Cita la cifra principal "
            f"de la lista. NO inventes números. Sin markdown, sin viñetas."
        )

    @staticmethod
    def _build_extended_prompt(
        question: str,
        top: SearchResult,
        stats: Statistics,
        rows: list[dict[str, Any]],
    ) -> str:
        """Prompt EXTENDIDO (narrativa interpretativa, 3-5 frases, ~400 tokens)."""
        entity = top.entity or "entidad no declarada"
        rows_preview = rows[:20]
        rows_text = "\n".join(f"  - {r}" for r in rows_preview)
        numbered_summary = "\n".join(
            f"  ({i + 1}) {line}" for i, line in enumerate(stats.summary_lines)
        )
        return (
            f"Pregunta del ciudadano colombiano: «{question}»\n"
            f"Dataset: {top.name} ({top.id}) — entidad publicadora: {entity}\n"
            f"Descripción del dataset: {(top.description or '')[:300]}\n\n"
            f"Filas devueltas por la consulta ({len(rows)} en total, "
            f"primeras {len(rows_preview)}):\n{rows_text}\n\n"
            f"CIFRAS AUTORIZADAS (calculadas con pandas sobre los rows reales — "
            f"son las ÚNICAS que puedes usar):\n{numbered_summary}\n\n"
            f"REGLAS ESTRICTAS:\n"
            f"- Puedes citar cualquiera de las cifras autorizadas, en cualquier orden.\n"
            f"- NO inventes ningún número que no esté en esa lista.\n"
            f"- Tu rol es INTERPRETAR cualitativamente: qué significa, tendencias, "
            f"comparaciones cualitativas, utilidad para el ciudadano. "
            f"NO repitas la tabla — el sistema la mostrará en un bloque aparte.\n"
            f"- 3-5 frases en español, sin markdown, sin viñetas.\n"
            f"- Catálogo es colombiano; NO menciones otros países salvo que "
            f"aparezcan literalmente arriba.\n"
        )

    def _build_verified_block(
        self,
        soql: str,
        rows: list[dict[str, Any]],
        stats: Statistics,
        top: SearchResult,
        geo_ctx: GeoContext | None,
    ) -> str:
        """Bloque determinista de "Datos verificados" que va al final del extended.

        Pandas-driven: cifras de stats + SoQL ejecutado + entidad publicadora +
        opcional advertencia de atribución geográfica (PROD_IMPROV #5).
        """
        entity = top.entity or "entidad no declarada"
        geo_warning_line = ""
        try:
            attr = validate_geographic_attribution(rows, geo_ctx)
            if not attr.matches and attr.warning:
                geo_warning_line = f"\n- {attr.warning}"
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "validate_geographic_attribution falló (%s); sigo sin warning", exc
            )
        return (
            "\n\n📊 **Datos verificados** (calculados con pandas sobre los rows reales):\n"
            + "\n".join(f"- {line}" for line in stats.summary_lines)
            + f"\n- SoQL ejecutado: `{soql}`"
            + f"\n- Entidad publicadora: {entity}"
            + geo_warning_line
        )

    async def _narrate_with_data_stream(
        self,
        question: str,
        top: SearchResult,
        soql: str,
        rows: list[dict[str, Any]],
        geo_ctx: GeoContext | None = None,
    ) -> AsyncIterator["NarrativeStreamEvent"]:
        """Versión streaming de la narrativa: emite eventos summary + extended.

        Diseño (TTFB ≤ 1s, plan 2026-05-22):
        - 1ª llamada LLM con prompt corto (max_tokens=120) → emite tokens de
          summary conforme llegan.
        - 2ª llamada LLM con prompt completo (max_tokens=400) → emite tokens
          de extended conforme llegan.
        - Al final del extended, emite el bloque "Datos verificados"
          determinista (pandas).
        - Si `_validate_numbers` censura cifras del extended completo, emite
          un evento `extended_correction` con la versión censurada.
        - El último evento es `stats` con el Statistics calculado (para que el
          caller pueda almacenarlo aparte si necesita).

        Caso 0 rows: emite respuesta determinista en summary, omite extended.
        """
        entity = top.entity or "entidad no declarada"
        stats = StatsComputer.compute(rows, soql)

        if stats.total_rows == 0:
            text = (
                f"La consulta al dataset {top.name} ({top.id}) no devolvió "
                f"filas. Esto suele significar que el filtro fue demasiado "
                f"estricto o que el dataset no contiene registros que "
                f"coincidan con tu pregunta. Entidad publicadora: {entity}."
            )
            yield NarrativeStreamEvent("summary", text, done=True)
            verified_zero = (
                "\n\n📊 **Datos verificados**\n"
                f"- {stats.summary_lines[0]}\n"
                f"- SoQL ejecutado: `{soql}`"
            )
            yield NarrativeStreamEvent("extended", verified_zero, done=True)
            yield NarrativeStreamEvent("stats", "", done=True, stats=stats)
            return

        # Summary streaming. Una sola llamada LLM por query — el extended es
        # determinista (summary + bloque verificado pandas) para evitar la
        # saturación de Ollama con dos llamadas paralelas competiendo por
        # CPU. Esto mantiene TTFB <3s y garantiza que el `event: done`
        # llegue rápido tras el último token del summary.
        summary_prompt = self._build_summary_prompt(question, top, stats, rows)
        summary_buf = ""
        try:
            stream = self.llm.generate_stream(
                summary_prompt,
                max_tokens=180,
                model=model_for_task("narrative"),
            )
            async for tok in stream:
                summary_buf += tok
                yield NarrativeStreamEvent("summary", tok, done=False)
        except Exception as exc:  # noqa: BLE001
            log.warning("Summary LLM stream falló (%s)", exc)
        yield NarrativeStreamEvent("summary", "", done=True)

        # Validación post-LLM. Si hay corrección, emitir evento de reemplazo.
        try:
            validated = _validate_numbers(summary_buf, stats)
            if validated != summary_buf and validated:
                yield NarrativeStreamEvent(
                    "extended_correction", validated, done=False
                )
                summary_buf = validated
        except Exception as exc:  # noqa: BLE001
            log.warning("_validate_numbers falló (%s); sigo sin corrección", exc)

        # Bloque determinista de datos verificados.
        try:
            verified_block = self._build_verified_block(
                soql, rows, stats, top, geo_ctx
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("_build_verified_block falló (%s); sigo sin bloque", exc)
            verified_block = ""

        # Extended = summary completo + verified_block (sin segunda llamada LLM).
        # El ciudadano que expande `<details>` ve: la misma narrativa que el
        # summary + la trazabilidad determinista pandas. Sin doble inferencia,
        # latencia mínima.
        extended_full = (summary_buf or "") + verified_block
        yield NarrativeStreamEvent("extended", extended_full, done=True)

        # Stats al final (canal lateral, opcional para el caller).
        yield NarrativeStreamEvent("stats", "", done=True, stats=stats)

    async def _narrate_with_data(
        self,
        question: str,
        top: SearchResult,
        soql: str,
        rows: list[dict[str, Any]],
        geo_ctx: GeoContext | None = None,
    ) -> tuple[str, Statistics]:
        """Versión sync (legacy compat): consume el stream y acumula extended.

        Mantenida para tests y callers que esperan `(narrative_text, stats)`
        en lugar de stream. Internamente usa `_narrate_with_data_stream`.
        El `summary` se descarta (los callers legacy esperaban solo el extended
        con el bloque verificado).
        """
        extended_buf = ""
        correction_buf: str | None = None
        stats: Statistics | None = None
        async for event in self._narrate_with_data_stream(
            question, top, soql, rows, geo_ctx
        ):
            if event.kind == "extended":
                extended_buf += event.text
            elif event.kind == "extended_correction":
                correction_buf = event.text
            elif event.kind == "stats":
                stats = event.stats
        narrative = correction_buf if correction_buf is not None else extended_buf
        assert stats is not None  # _narrate_with_data_stream siempre emite stats
        return narrative, stats

    # ------------------------------------------------------------
    # Tier 3 fallback (reformulación)
    # ------------------------------------------------------------

    async def _llm_reformulate(self, question: str) -> str | None:
        """Tier 3 fallback (ADR-007): pide al LLM reformular la pregunta con
        keywords alternativos cuando el match preciso y la búsqueda temática
        no produjeron resultados.

        Devuelve `None` si el LLM no produjo nada útil.
        """
        prompt = (
            f"Reformula esta pregunta usando 3-5 palabras clave alternativas "
            f"en español que un sistema de búsqueda de datos abiertos colombianos "
            f"podría encontrar mejor. Devuelve SOLO las palabras clave separadas "
            f"por espacios, sin explicación.\n\n"
            f"Pregunta original: {question!r}\n\n"
            f"Palabras clave alternativas:"
        )
        # Timeout duro: la P30 del journey 2026-05-18 ("Quiero saber sobre Ecuador")
        # se quedó atascada 67 min en este path. Para beta limitamos a 60 s.
        try:
            response = await asyncio.wait_for(
                self.llm.generate(
                    prompt,
                    max_tokens=100,
                    model=model_for_task("reformulate"),
                    temperature=0.3,
                ),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            log.warning("LLM reformulation timeout (>60s) — devuelvo None")
            return None
        except Exception as exc:  # noqa: BLE001 — fallback debe ser robusto
            log.warning("LLM reformulation failed: %s", exc)
            return None
        result = (response or "").strip()
        if not result or len(result) > 300:
            return None
        return result
