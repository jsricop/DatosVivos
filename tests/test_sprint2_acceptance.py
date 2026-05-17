"""Tests de aceptación Sprint 2 — DEFINIDOS ANTES DE IMPLEMENTAR.

REGLA INVIOLABLE: estos tests NO se modifican una vez commiteados. Si fallan
al implementar las features, se corrige el CÓDIGO, no los tests. Esto evita
sesgar la verificación final hacia lo que el desarrollador terminó haciendo
en vez de hacia lo que se prometió.

Sprint 2 deliverable (MAIN.md §7): "Índice vectorial + clasificador de intención"
Deadline: 2026-06-01.

Cobertura:
- A. Clasificador de intención (`ai_engine/intent_classifier.py`):
     5 categorías, accuracy ≥ 0.85 sobre held-out set de 30 ejemplos,
     latencia < 100 ms por clasificación.
- B. Índice vectorial (`ai_engine/vector_index.py`):
     cobertura ≥ 1.000 datasets, top-K contiene dataset esperado,
     persistencia a disco, latencia query < 200 ms P50.
- C. Build script (`scripts/build_index.py`):
     idempotente, reporta progreso, ejecuta contra Discovery real.

Cada test arranca con `@pytest.mark.skip("Sprint 2 WIP — ...")`. A medida que
una feature se implementa, se REMUEVE el skip de su test correspondiente.
Al cierre de Sprint 2, todos los skip deben estar removidos y el test verde.

Convención: los assertions concretos NO se relajan. Si la implementación no
alcanza el umbral, se sigue iterando hasta lograrlo.
"""

from __future__ import annotations

import time
from pathlib import Path

# ============================================================
# A. Clasificador de intención
# ============================================================

INTENT_CATEGORIES = {"search", "descriptive", "comparative", "temporal", "cross_source"}

# 30 ejemplos held-out, 6 por categoría. Sin estos en train data.
# Si la implementación los usa para entrenar, el accuracy mide overfit, no generalización.
INTENT_TEST_SET: list[tuple[str, str]] = [
    # search — pregunta por la EXISTENCIA de datos
    ("¿qué datos hay sobre salud?", "search"),
    ("dame los datasets de educación", "search"),
    ("busca información sobre transporte", "search"),
    ("qué hay publicado sobre presupuesto nacional", "search"),
    ("encuentra datos del DANE", "search"),
    ("hay datasets de seguridad ciudadana", "search"),
    # descriptive — pide DESCRIBIR contenido específico
    ("muéstrame los municipios de Antioquia", "descriptive"),
    ("lista las entidades publicadoras", "descriptive"),
    ("dame la lista de departamentos de Colombia", "descriptive"),
    ("muestra los registros del año 2024", "descriptive"),
    ("qué columnas tiene este dataset", "descriptive"),
    ("dime cuántas filas tiene el catálogo DIVIPOLA", "descriptive"),
    # comparative — implica comparación entre entidades/categorías
    ("compara el presupuesto entre departamentos", "comparative"),
    ("cuál tiene más municipios, Antioquia o Boyacá", "comparative"),
    ("diferencia de cobertura entre regiones", "comparative"),
    ("ranking de departamentos por inversión", "comparative"),
    ("qué entidad tiene más datasets publicados", "comparative"),
    ("compara la tasa de desempleo de Bogotá y Medellín", "comparative"),
    # temporal — implica análisis sobre el tiempo
    ("cómo ha evolucionado la cobertura de internet desde 2010", "temporal"),
    ("evolución del PIB nacional en la última década", "temporal"),
    ("tendencia de matrícula escolar 2015 a 2024", "temporal"),
    ("cambio histórico en la población de Cali", "temporal"),
    ("crecimiento del comercio exterior por año", "temporal"),
    ("variación anual de homicidios en Medellín", "temporal"),
    # cross_source — explícitamente pide combinar/relacionar fuentes
    ("relación entre educación y pobreza por departamento", "cross_source"),
    ("cruce de datos de salud con nivel socioeconómico", "cross_source"),
    ("correlación entre inversión pública y resultados PISA", "cross_source"),
    ("combina información del DANE y Mineducación", "cross_source"),
    ("une los datos de presupuesto y ejecución por municipio", "cross_source"),
    ("integra datos del MEN con los del ICFES por colegio", "cross_source"),
]


def test_intent_classifier_returns_one_of_five_categories():
    """El clasificador SIEMPRE devuelve una de las 5 categorías oficiales."""
    from ai_engine.intent_classifier import IntentClassifier

    clf = IntentClassifier()
    for question, _ in INTENT_TEST_SET[:10]:
        result = clf.classify(question)
        assert result in INTENT_CATEGORIES, (
            f"Categoría inválida {result!r} para {question!r}. "
            f"Esperaba una de {INTENT_CATEGORIES}."
        )


def test_intent_classifier_accuracy_at_least_85_percent():
    """Sobre 30 ejemplos held-out, accuracy ≥ 0.85 (al menos 26 correctos)."""
    from ai_engine.intent_classifier import IntentClassifier

    clf = IntentClassifier()
    correct = 0
    mistakes: list[tuple[str, str, str]] = []
    for question, expected in INTENT_TEST_SET:
        predicted = clf.classify(question)
        if predicted == expected:
            correct += 1
        else:
            mistakes.append((question, expected, predicted))
    accuracy = correct / len(INTENT_TEST_SET)
    assert accuracy >= 0.85, (
        f"Accuracy {accuracy:.2%} < 0.85.\n"
        f"Aciertos: {correct}/{len(INTENT_TEST_SET)}.\n"
        f"Errores ({len(mistakes)}): {mistakes[:5]}{'...' if len(mistakes) > 5 else ''}"
    )


def test_intent_classifier_latency_under_100ms():
    """Una clasificación toma menos de 100 ms (P50 sobre 20 muestras)."""
    from ai_engine.intent_classifier import IntentClassifier

    clf = IntentClassifier()
    # warmup — primera llamada puede cargar embeddings desde disco
    clf.classify("warmup query")

    latencies: list[float] = []
    for _ in range(20):
        start = time.monotonic()
        clf.classify("¿cuáles departamentos tienen más datasets de salud?")
        latencies.append(time.monotonic() - start)
    latencies.sort()
    p50 = latencies[10]
    assert p50 < 0.1, f"Latencia P50 {p50*1000:.0f}ms ≥ 100ms"


# ============================================================
# B. Índice vectorial
# ============================================================

# Queries NL → dataset_id que DEBE aparecer en top-K resultados.
# Estos IDs son estables en datos.gov.co; si alguno desaparece, ajustar test.
VECTOR_INDEX_CANONICAL_QUERIES: list[tuple[str, str, int]] = [
    ("código de municipios DIVIPOLA", "gdxc-w37w", 5),
    ("división política administrativa de Colombia departamentos", "vcjz-niiq", 5),
]


def test_vector_index_covers_at_least_1000_datasets():
    """El índice persistido contiene al menos 1.000 datasets del catálogo (~8.000 total)."""
    from ai_engine.vector_index import VectorIndex

    idx = VectorIndex.load()
    n = len(idx)
    assert n >= 1000, f"Cobertura insuficiente: {n} datasets indexados, esperaba ≥ 1.000"


def test_vector_index_finds_canonical_datasets_in_top_k():
    """Para cada query canónica, el dataset esperado aparece en el top-K."""
    from ai_engine.vector_index import VectorIndex

    idx = VectorIndex.load()
    failures = []
    for query, expected_id, k in VECTOR_INDEX_CANONICAL_QUERIES:
        results = idx.search(query, k=k)
        ids = [r.id if hasattr(r, "id") else r["id"] for r in results]
        if expected_id not in ids:
            failures.append((query, expected_id, ids))
    assert not failures, f"Datasets esperados no encontrados en top-K: {failures}"


def test_vector_index_persists_across_restart():
    """Cargar el índice, descartarlo, volver a cargar → mismo tamaño y mismas búsquedas."""
    from ai_engine.vector_index import VectorIndex

    idx1 = VectorIndex.load()
    count_initial = len(idx1)
    results1 = idx1.search("educación", k=3)
    ids1 = [r.id if hasattr(r, "id") else r["id"] for r in results1]
    del idx1

    idx2 = VectorIndex.load()
    count_after = len(idx2)
    results2 = idx2.search("educación", k=3)
    ids2 = [r.id if hasattr(r, "id") else r["id"] for r in results2]

    assert (
        count_initial == count_after
    ), f"Tamaño cambió tras reload: {count_initial} → {count_after}"
    assert ids1 == ids2, f"Resultados cambiaron tras reload:\n  Antes: {ids1}\n  Después: {ids2}"


def test_vector_index_query_latency_under_200ms_p50():
    """Una búsqueda toma < 200 ms (P50 sobre 20 muestras), excluyendo warmup."""
    from ai_engine.vector_index import VectorIndex

    idx = VectorIndex.load()
    idx.search("warmup", k=5)  # warmup

    latencies: list[float] = []
    queries = [
        "educación primaria",
        "casos covid en Bogotá",
        "presupuesto nacional",
        "exportaciones por departamento",
        "tasa de desempleo",
    ] * 4  # 20 queries
    for q in queries:
        start = time.monotonic()
        idx.search(q, k=5)
        latencies.append(time.monotonic() - start)
    latencies.sort()
    p50 = latencies[10]
    assert p50 < 0.2, f"Latencia P50 {p50*1000:.0f}ms ≥ 200ms"


def test_vector_index_low_confidence_on_nonsense_query():
    """Una query sin sentido NO debe devolver resultados con alta confianza."""
    from ai_engine.vector_index import VectorIndex

    idx = VectorIndex.load()
    # asumimos que `search` puede devolver objetos con `.score` o el cliente
    # expone un `search_with_scores`. La API exacta se decide en implementación.
    results = idx.search("qslsdkjfgh1234nonsense", k=5)
    # Esperamos: lista vacía, o todos los scores por debajo del umbral usual de relevancia
    if results:
        scores = [r.score if hasattr(r, "score") else r.get("score") for r in results]
        # Umbral conservador: para cosine similarity, < 0.3 indica match débil
        max_score = max(s for s in scores if s is not None)
        assert max_score < 0.5, (
            f"Query nonsense devolvió match con score {max_score} ≥ 0.5 — "
            f"esperaba todos < 0.5 o lista vacía"
        )


# ============================================================
# C. Build script
# ============================================================


def test_build_index_script_is_idempotent(tmp_path: Path):
    """Correr build_index dos veces no duplica entradas ni rompe el índice.

    Acepta hasta 10% de crecimiento en disco entre corridas (puede haber
    metadata accesoria pero no debe doblarse el tamaño).
    """
    from scripts.build_index import build_index

    idx_path = tmp_path / "vector_index"
    build_index(output_path=idx_path, limit=200)  # subset para no demorar el test
    n_first = sum(p.stat().st_size for p in idx_path.rglob("*") if p.is_file())

    build_index(output_path=idx_path, limit=200)
    n_second = sum(p.stat().st_size for p in idx_path.rglob("*") if p.is_file())

    assert n_second <= n_first * 1.1, (
        f"Segunda corrida creció demasiado (no es idempotente): "
        f"{n_first} bytes → {n_second} bytes"
    )


def test_build_index_reports_progress(tmp_path: Path, capsys):
    """El script debe imprimir progreso, no quedarse silencioso 10 minutos."""
    from scripts.build_index import build_index

    build_index(output_path=tmp_path / "vector_index", limit=50)
    captured = capsys.readouterr()
    output = captured.out + captured.err
    # Heurística: debería haber al menos una línea con número que indique progreso
    has_progress_signal = any(
        keyword in output.lower()
        for keyword in ["progreso", "indexed", "indexados", "%", "datasets"]
    )
    assert (
        has_progress_signal
    ), f"Sin señal de progreso en stdout/stderr (primeros 500 chars):\n{output[:500]}"


def test_build_index_handles_discovery_api_errors_gracefully(tmp_path: Path, monkeypatch):
    """Si Discovery falla intermitentemente, el build reintenta y al final NO crashea.

    Simula: la primera llamada a Discovery falla con timeout, las siguientes OK.
    Esperado: build_index completa sin excepción (con retry exponencial interno).
    """
    import httpx

    from mcp_server.socrata.discovery_client import DiscoveryClient
    from scripts.build_index import build_index

    original_search = DiscoveryClient.search
    call_count = {"n": 0}

    async def flaky_search(self, query=None, limit=10, offset=0):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise httpx.TimeoutException("simulated transient timeout")
        return await original_search(self, query=query, limit=limit, offset=offset)

    monkeypatch.setattr(DiscoveryClient, "search", flaky_search)

    # No debe lanzar excepción a pesar del primer timeout
    n = build_index(output_path=tmp_path / "vector_index", limit=20)
    assert n >= 1, "Build no recuperó del timeout transitorio"
