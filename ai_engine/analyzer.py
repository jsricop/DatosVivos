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
import re
from dataclasses import dataclass, field
from typing import Any

from ai_engine.geo_resolver import GeoContext, GeoResolver, build_comparison_soql
from ai_engine.intent_classifier import IntentClassifier
from ai_engine.llm_backend import LLMBackend
from ai_engine.query_generator import QueryGenerator
from ai_engine.stats_computer import Statistics, StatsComputer, _normalize_number
from ai_engine.vector_index import SearchResult, VectorIndex
from mcp_server.socrata.discovery_client import DiscoveryClient
from mcp_server.socrata.metadata_client import MetadataClient
from mcp_server.socrata.soda_client import SodaClient

log = logging.getLogger(__name__)

# Boost aplicado al score del vector index cuando el mismo dataset aparece
# en la Discovery API. Empírico — ver journey evaluation 2026-05-18.
DISCOVERY_BOOST = 0.05

# Boost aplicado a hits cuyo nombre/descripción mencione el territorio resuelto
# por GeoResolver. Mismo orden de magnitud que DISCOVERY_BOOST — efectos
# acumulables si un dataset aparece en Discovery Y menciona el territorio.
GEO_BOOST = 0.08

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

    async def analyze(self, question: str) -> AnalysisResult:
        """Pipeline completo. Devuelve resultado estructurado."""
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
            if soql_result is not None:
                soql, rows = soql_result
                narrative, stats = await self._narrate_with_data(
                    question, hits[0], soql, rows
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
        # si geo_ctx menciona un territorio que aparece en el nombre/desc.
        geo_tokens = self._geo_match_tokens(geo_ctx)
        boosted: list[SearchResult] = []
        for h in vector_hits:
            score_delta = 0.0
            if h.id in discovery_ids:
                score_delta += DISCOVERY_BOOST
            if geo_tokens:
                haystack = (h.name + " " + (h.description or "")).lower()
                if any(tok in haystack for tok in geo_tokens):
                    score_delta += GEO_BOOST
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
            raw = await self.llm.generate(prompt, max_tokens=10, temperature=0.0)
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
    ) -> tuple[str, list[dict[str, Any]]] | None:
        """Para intents no-search: obtener schema, generar SoQL, ejecutar.

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
                    return templated_soql, rows[:50]
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "SoQL determinista falló (%s): %s — caigo a query_gen LLM",
                        templated_soql,
                        exc,
                    )

        # --- (2) Fallback: query_gen LLM con hints de geo si aplican ---
        # Construir la pregunta-con-geo-hint para el query_generator.
        question_for_gen = question
        if geo_ctx is not None:
            hint_parts: list[str] = []
            if geo_ctx.mpio_code and "cod_mpio" in col_names:
                hint_parts.append(
                    f"WHERE cod_mpio = '{geo_ctx.mpio_code}' "
                    f"(corresponde a {geo_ctx.mpio_name})"
                )
            elif geo_ctx.dpto_code and "cod_dpto" in col_names:
                hint_parts.append(
                    f"WHERE cod_dpto = '{geo_ctx.dpto_code}' "
                    f"(corresponde a {geo_ctx.dpto_name})"
                )
            if geo_ctx.groupby and geo_ctx.groupby in col_names:
                hint_parts.append(f"GROUP BY {geo_ctx.groupby}")
            if hint_parts:
                question_for_gen = (
                    f"{question}\n\nPISTA (DIVIPOLA): usa exactamente "
                    + "; ".join(hint_parts)
                    + " sobre las columnas reales del esquema."
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

        try:
            rows = await self.soda.query(dataset_id=top.id, soql_query=soql)
        except Exception as exc:  # noqa: BLE001
            log.warning("SodaClient.query falló (%s): %s", soql, exc)
            return None

        # Cap rows para no inflar narrativa.
        return soql, rows[:50]

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
        raw = await self.llm.generate(prompt, max_tokens=300)
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
        raw = await self.llm.generate(prompt, max_tokens=250)
        return _validate_numbers(raw, None)

    async def _narrate_with_data(
        self,
        question: str,
        top: SearchResult,
        soql: str,
        rows: list[dict[str, Any]],
    ) -> tuple[str, Statistics]:
        """Genera narrativa con cifras 100% verificables.

        Diseño (post-journey 2026-05-18):
        - StatsComputer calcula deterministicamente toda cifra a partir de
          los rows con pandas.
        - El LLM recibe los rows + la **ficha de cifras autorizadas** y
          produce una interpretación cualitativa.
        - `_validate_numbers` censura cualquier cifra que el LLM mencione
          fuera de la whitelist.
        - El bloque "📊 Datos verificados" se concatena al final, siempre
          presente, generado por pandas.

        Returns:
            (narrative_text, statistics) — el text incluye el bloque de
            datos verificados; statistics queda disponible para la UI.
        """
        entity = top.entity or "entidad no declarada"
        stats = StatsComputer.compute(rows, soql)

        # 0 filas: no llamamos al LLM. Respuesta determinista.
        if stats.total_rows == 0:
            text = (
                f"La consulta al dataset {top.name} ({top.id}) no devolvió "
                f"filas. Esto suele significar que el filtro fue demasiado "
                f"estricto o que el dataset no contiene registros que "
                f"coincidan con tu pregunta. Entidad publicadora: {entity}.\n\n"
                f"📊 **Datos verificados**\n"
                f"- {stats.summary_lines[0]}\n"
                f"- SoQL ejecutado: `{soql}`"
            )
            return text, stats

        rows_preview = rows[:20]
        rows_text = "\n".join(f"  - {r}" for r in rows_preview)
        numbered_summary = "\n".join(
            f"  ({i + 1}) {line}" for i, line in enumerate(stats.summary_lines)
        )

        prompt = (
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
        raw = await self.llm.generate(prompt, max_tokens=400)
        narrative = _validate_numbers(raw, stats)

        # Bloque determinista al final — siempre visible, intocable.
        verified_block = (
            "\n\n📊 **Datos verificados** (calculados con pandas sobre los rows reales):\n"
            + "\n".join(f"- {line}" for line in stats.summary_lines)
            + f"\n- SoQL ejecutado: `{soql}`"
            + f"\n- Entidad publicadora: {entity}"
        )
        return narrative + verified_block, stats

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
                self.llm.generate(prompt, max_tokens=100, temperature=0.3),
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
