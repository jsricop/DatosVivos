"""Tests de reproducibilidad para `scripts/`.

Verifican que los scripts auxiliares funcionan desde un estado limpio
(tmp_path) sin depender del estado del índice persistente en producción.

Cubre gap detectado en auditoría 2026-05-16: los scripts se corrieron
manualmente una sola vez; sin tests, era posible que un clon limpio del
repo no reprodujera la generación.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.live
@pytest.mark.integration
def test_build_index_creates_loadable_index_from_clean_state(tmp_path: Path):
    """`scripts/build_index.py` produce un índice cargable desde cero.

    Usa un tmp_path limpio (no toca `data/vector_index` de producción).
    Limita a 30 datasets para que el test sea rápido (~10s).
    """
    from ai_engine.vector_index import VectorIndex
    from scripts.build_index import build_index

    index_path = tmp_path / "test_index"

    # Ejecutar build desde estado limpio
    n_indexed = build_index(output_path=index_path, limit=30, page_size=30)
    assert n_indexed >= 20, f"build_index indexó {n_indexed}, esperaba ≥ 20"

    # Verificar que el índice es cargable y funcional
    idx = VectorIndex(path=index_path)
    assert len(idx) >= 20
    # Una búsqueda básica debe funcionar (aunque con 30 datasets puede dar pocos hits)
    results = idx.search("colombia datos", k=3)
    # No exigimos resultados específicos (índice pequeño), solo que no crashee
    assert isinstance(results, list)


@pytest.mark.live
@pytest.mark.integration
def test_extract_topic_keywords_generates_valid_data_module(tmp_path: Path):
    """`scripts/extract_topic_keywords.py` produce un módulo Python válido.

    Construye un índice mini (10 datasets) en tmp_path, corre la extracción,
    verifica que el archivo de salida es importable y tiene la estructura
    esperada.
    """
    import importlib.util
    import sys

    from scripts.build_index import build_index
    from scripts.extract_topic_keywords import (
        extract_keywords_per_entity,
        write_data_module,
    )

    # 1. Mini-índice de 30 datasets
    index_path = tmp_path / "test_index"
    build_index(output_path=index_path, limit=30, page_size=30)

    # 2. Extraer keywords
    keywords = extract_keywords_per_entity(
        chroma_path=index_path,
        top_k=5,
        min_len=4,
        min_freq=1,  # min_freq=1 porque corpus es pequeño
    )
    # El resultado puede ser un dict pequeño (pocas entidades matcheadas)
    # pero NO debe crashear.
    assert isinstance(keywords, dict)

    # 3. Escribir módulo de datos
    output_module = tmp_path / "generated_keywords.py"
    write_data_module(keywords, output_module)
    assert output_module.exists()

    # 4. Importar el módulo generado y validar estructura
    spec = importlib.util.spec_from_file_location("generated_keywords", output_module)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["generated_keywords"] = module
    spec.loader.exec_module(module)

    assert hasattr(module, "KEYWORDS_BY_CANONICAL")
    data = module.KEYWORDS_BY_CANONICAL
    assert isinstance(data, dict)
    # Sintáctica/estructural: si hay entradas, cada valor es lista de strings
    for canonical, kws in data.items():
        assert isinstance(canonical, str)
        assert isinstance(kws, list)
        assert all(isinstance(k, str) for k in kws)
