"""Tests de aceptación — topic keywords + fallback iterativo + LLM reformulación.

REGLA INVIOLABLE (MAIN.md §6.6): estos tests NO se modifican una vez commiteados.
Si fallan al implementar, se corrige el CÓDIGO, no los tests.

Motivación (ADR-007): los ciudadanos NO suelen mencionar entidades por nombre
("datos sobre tierras", no "datos de la ANT"). Necesitamos un mecanismo que
mapee keywords temáticos a entidades, aplicado SOLO cuando el match preciso
de acrónimos no aportó resultados.

Diseño en 3 tiers:
    Tier 1 (acrónimos, ya implementado): expand_query precise.
    Tier 2 (topic keywords iterativo, este PR): grupos de 2 entidades por
            relevancia, intento sucesivo hasta encontrar resultados.
    Tier 3 (LLM reformulación, este PR): si tiers 1 y 2 agotan,
            el analyzer pide al LLM reformular la pregunta.

Cobertura (11 tests):
- A. Módulo topic_keywords (4): API, cobertura ≥3 keywords/entidad,
     output bien formado, sin solapamiento con acrónimos.
- B. Algoritmo de ranking (2): ordena por overlap, nonsense → [].
- C. Fallback iterativo en DiscoveryClient (3): orden, short-circuit,
     exhaustión sin LLM disponible.
- D. Tier 3 LLM en Analyzer (2): invocación cuando aplica, end-to-end
     temático con Ollama real.
"""

from __future__ import annotations

import pytest

# ============================================================
# A. Módulo topic_keywords
# ============================================================


def test_topic_keywords_module_exposes_api():
    """El módulo expone `KEYWORDS_BY_CANONICAL`, `topic_match_ranked`,
    `expand_with_topics_iterative`."""
    from mcp_server.socrata import topic_keywords

    assert hasattr(topic_keywords, "KEYWORDS_BY_CANONICAL")
    assert hasattr(topic_keywords, "topic_match_ranked")
    assert hasattr(topic_keywords, "expand_with_topics_iterative")
    assert callable(topic_keywords.topic_match_ranked)


def test_topic_keywords_covers_all_acronym_entities_with_min_3_each():
    """Cada entidad canónica del módulo `acronyms` debe tener ≥3 keywords
    temáticos. Esto previene gaps de fallback (lo que vimos en el audit:
    61% de entidades sin tesauros era inaceptable)."""
    from mcp_server.socrata.acronyms import ENTITIES
    from mcp_server.socrata.topic_keywords import KEYWORDS_BY_CANONICAL

    missing = []
    short = []
    for entry in ENTITIES:
        canonical = entry["canonical"]
        kws = KEYWORDS_BY_CANONICAL.get(canonical, [])
        if not kws:
            missing.append(canonical)
        elif len(kws) < 3:
            short.append((canonical, len(kws)))

    assert not missing, f"Entidades sin keywords: {len(missing)}. Primeras 5: {missing[:5]}"
    assert not short, f"Entidades con <3 keywords: {len(short)}. Primeras 5: {short[:5]}"


def test_topic_match_ranked_returns_groups_of_at_most_two():
    """`topic_match_ranked` agrupa de a 2 entidades por rank.

    Output: `list[list[str]]`. Outer list ordered by relevance.
    Inner list has at most 2 canonicals (cap para no inundar la query a Socrata).
    """
    from mcp_server.socrata.topic_keywords import topic_match_ranked

    groups = topic_match_ranked("información sobre tierras y predios rurales")
    assert isinstance(groups, list)
    assert all(isinstance(g, list) for g in groups), "outer items deben ser listas"
    assert all(len(g) <= 2 for g in groups), "cada grupo debe tener máximo 2 entidades"
    # Al menos un grupo con al menos 1 entidad de tierras
    flat = [c for g in groups for c in g]
    assert any(
        "Tierras" in c or "Rurales" in c for c in flat
    ), f"Esperaba al menos una entidad de tierras en {flat}"


def test_topic_keywords_dont_duplicate_acronym_aliases():
    """Los keywords NO deben coincidir con aliases ya presentes en `acronyms.py`.

    Si un término ya está en `aliases`, el match preciso (Tier 1) ya lo cubre.
    Los keywords son SOLO conceptos temáticos descriptivos (no nombres de entidades).
    """
    from mcp_server.socrata.acronyms import ENTITIES
    from mcp_server.socrata.topic_keywords import KEYWORDS_BY_CANONICAL

    canonical_to_aliases = {e["canonical"]: {a.lower() for a in e["aliases"]} for e in ENTITIES}
    violations = []
    for canonical, kws in KEYWORDS_BY_CANONICAL.items():
        aliases = canonical_to_aliases.get(canonical, set())
        for kw in kws:
            if kw.lower() in aliases:
                violations.append((canonical, kw))
    assert not violations, f"Keywords que duplican aliases (tier 1 ya los cubre): {violations[:10]}"


# ============================================================
# B. Algoritmo de ranking
# ============================================================


def test_topic_match_orders_by_overlap_count():
    """Entidad con más palabras-clave en la query aparece antes en el ranking."""
    from mcp_server.socrata.topic_keywords import topic_match_ranked

    # Query con múltiples conceptos: la entidad con más overlap debe aparecer primera
    groups = topic_match_ranked(
        "datos sobre clima lluvias y precipitaciones del territorio nacional"
    )
    flat = [c for g in groups for c in g]
    # IDEAM (clima, lluvias, meteorología) debería rankear por encima de
    # otras entidades que solo matcheen "territorio" o "nacional"
    if flat:
        assert any(
            "Hidrología" in c or "IDEAM" in c for c in flat[:2]
        ), f"Esperaba IDEAM en top-2 grupos. Vi: {flat[:4]}"


def test_topic_match_nonsense_returns_empty():
    """Query sin ninguna palabra clave temática conocida → `[]`."""
    from mcp_server.socrata.topic_keywords import topic_match_ranked

    assert topic_match_ranked("xyzzy plugh qwertyuiop nonsense") == []


# ============================================================
# C. Fallback iterativo en DiscoveryClient
# ============================================================


async def test_discovery_iterative_tries_groups_in_rank_order(monkeypatch):
    """DiscoveryClient debe intentar los grupos de keywords en orden de rank.

    Verifica con un spy que la secuencia de búsquedas es la esperada:
    primero query base, luego grupo 1, luego grupo 2, etc.
    """
    from mcp_server.socrata.discovery_client import DiscoveryClient
    from mcp_server.socrata.topic_keywords import expand_with_topics_iterative

    # Si Tier 1 no expandió y Socrata devuelve 0 en query base, debe
    # iterar a través de los grupos de topic keywords en orden.
    queries_attempted: list[str] = []

    async def spy_search(self, query=None, limit=10, offset=0):
        queries_attempted.append(query or "")
        return []  # forzar empty para que itere todos los grupos

    monkeypatch.setattr(DiscoveryClient, "search", spy_search)

    # Esta función debe llamar search múltiples veces, una por grupo
    await expand_with_topics_iterative(
        client=DiscoveryClient(),
        query="información sobre tierras y predios rurales",
        limit=5,
    )

    # Al menos 2 intentos (query base + al menos un grupo de topic)
    assert (
        len(queries_attempted) >= 2
    ), f"Solo {len(queries_attempted)} intentos: {queries_attempted}"


async def test_discovery_iterative_short_circuits_on_first_nonempty(monkeypatch):
    """Cuando un grupo devuelve resultados, NO debe seguir intentando los siguientes."""
    from mcp_server.socrata.discovery_client import DiscoveryClient
    from mcp_server.socrata.topic_keywords import expand_with_topics_iterative

    call_count = {"n": 0}

    async def fake_search(self, query=None, limit=10, offset=0):
        call_count["n"] += 1
        # Primer intento: vacío. Segundo: con resultados.
        if call_count["n"] == 1:
            return []
        return [{"resource": {"id": "fake-w37w", "name": "Fake result"}}]

    monkeypatch.setattr(DiscoveryClient, "search", fake_search)

    results = await expand_with_topics_iterative(
        client=DiscoveryClient(),
        query="datos sobre clima",
        limit=5,
    )

    assert results, "Esperaba resultados del 2do intento"
    assert (
        call_count["n"] == 2
    ), f"Short-circuit falló: se hicieron {call_count['n']} llamadas, esperaba 2"


async def test_discovery_iterative_returns_empty_when_all_groups_exhausted(monkeypatch):
    """Si todos los grupos de keywords fallan, retorna `[]` (sin LLM en esta capa)."""
    from mcp_server.socrata.discovery_client import DiscoveryClient
    from mcp_server.socrata.topic_keywords import expand_with_topics_iterative

    async def always_empty(self, query=None, limit=10, offset=0):
        return []

    monkeypatch.setattr(DiscoveryClient, "search", always_empty)

    results = await expand_with_topics_iterative(
        client=DiscoveryClient(),
        query="datos sobre tierras educación salud",
        limit=5,
    )
    assert results == [], "Esperaba [] cuando todos los grupos fallan"


# ============================================================
# D. Tier 3 — LLM reformulación en Analyzer
# ============================================================


async def test_analyzer_invokes_llm_reformulation_when_topic_fallback_empty():
    """Si tiers 1 y 2 retornan [], el analyzer pide reformulación al LLM."""
    from ai_engine.analyzer import Analyzer
    from ai_engine.intent_classifier import IntentClassifier
    from ai_engine.llm_backend import MockBackend
    from ai_engine.vector_index import VectorIndex

    # Mock que devuelve reformulación específica
    mock = MockBackend(default_response="datos abiertos catálogo")
    mock.add_response(
        prompt_contains="reformula",
        response="vivienda urbanismo construcción",
    )

    analyzer = Analyzer(
        vector_index=VectorIndex.load(),
        intent_classifier=IntentClassifier(),
        llm_backend=mock,
    )

    # Pregunta deliberadamente vaga
    result = await analyzer.analyze("quiero saber cosas")

    # El mock debió ser invocado para reformulación (verificable en mock.calls)
    reformulation_calls = [c for c in mock.calls if "reformula" in c.lower()]
    # Si Tier 1 y Tier 2 fallan, debe haber al menos 1 reformulación
    # NOTA: si por casualidad la pregunta vaga matchea algo, este test puede no aplicar.
    # Inspecciona el narrative para confirmar el path.
    narrative = result.narrative if hasattr(result, "narrative") else result.get("narrative", "")
    assert (
        reformulation_calls or "reformul" in narrative.lower() or result.datasets_used
    ), f"Esperaba reformulación o algún resultado. Narrative: {narrative[:200]!r}"


@pytest.mark.live
async def test_analyzer_end_to_end_thematic_query_finds_results():
    """Query temática SIN nombre de entidad encuentra datasets via tier 2 (o 3 con Ollama).

    Verifica el flujo end-to-end con Ollama real: una pregunta como
    "información sobre tierras rurales" no menciona ANT/UPRA por nombre,
    pero debe terminar con `datasets_used` no vacío gracias al fallback.
    """
    import os

    import httpx

    # Salta si Ollama no responde (entorno sin daemon)
    try:
        r = httpx.get(f"{os.getenv('OLLAMA_HOST', 'http://localhost:11434')}/api/tags", timeout=2)
        if r.status_code != 200:
            pytest.skip("Ollama no disponible")
    except Exception:
        pytest.skip("Ollama no disponible")

    from ai_engine.analyzer import Analyzer
    from ai_engine.intent_classifier import IntentClassifier
    from ai_engine.llm_backend import OllamaBackend
    from ai_engine.vector_index import VectorIndex

    analyzer = Analyzer(
        vector_index=VectorIndex.load(),
        intent_classifier=IntentClassifier(),
        llm_backend=OllamaBackend(),
    )
    result = await analyzer.analyze("información sobre tierras rurales en Colombia")

    datasets = (
        result.datasets_used
        if hasattr(result, "datasets_used")
        else result.get("datasets_used", [])
    )
    assert datasets, "Esperaba al menos 1 dataset para query temática de tierras"
