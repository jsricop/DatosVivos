"""Tests congelados para el boost a datasets DIVIPOLA en el retrieval.

Gap detectado en journey 2026-05-21 (P1 sigue fallando):
- Pregunta "¿Cuántos municipios tiene Antioquia?"
- count_in funciona en GeoResolver.
- PERO el retrieval nunca trae `gdxc-w37w` (DIVIPOLA oficial DANE).
- Cae a datasets que NO tienen columna `cod_dpto`, plantilla SoQL falla,
  query_gen LLM inventa columnas → 0 resultados.

Este módulo prueba la función pura `divipola_boost_amount(question, hit)`
que devuelve el boost (>0) si:
1. La pregunta menciona "municipio(s)" o "departamento(s)" como sustantivo central.
2. El hit es DIVIPOLA (gdxc-w37w o nombre/desc contiene DIVIPOLA).

El boost debe ser suficiente para que un dataset DIVIPOLA con score=0.3 supere
un dataset no-DIVIPOLA con score=0.5.
"""

from __future__ import annotations


def _mock_hit(id: str, name: str, score: float = 0.5, description: str = ""):
    """Crea un SearchResult simple para tests."""
    from ai_engine.vector_index import SearchResult

    return SearchResult(
        id=id, name=name, entity="DANE", score=score,
        description=description, category="poblacion",
    )


def test_boost_se_activa_con_mpios_y_dataset_divipola():
    """'¿cuántos municipios tiene Antioquia?' + gdxc-w37w → boost grande."""
    from ai_engine.analyzer import divipola_boost_amount

    hit = _mock_hit("gdxc-w37w", "DIVIPOLA — Codificación Municipios y Departamentos")
    boost = divipola_boost_amount("¿Cuántos municipios tiene Antioquia?", hit)
    assert boost > 0.2  # suficiente para flipping top-N


def test_boost_se_activa_con_departamentos_plural():
    """'cuántos departamentos hay en Colombia' → boost para DIVIPOLA."""
    from ai_engine.analyzer import divipola_boost_amount

    hit = _mock_hit("gdxc-w37w", "Códigos DIVIPOLA")
    boost = divipola_boost_amount("¿cuántos departamentos hay en Colombia?", hit)
    assert boost > 0.2


def test_boost_no_se_activa_sin_palabra_geo_clave():
    """'Datos de salud en Antioquia' → no boost (no menciona mpios/dptos)."""
    from ai_engine.analyzer import divipola_boost_amount

    hit = _mock_hit("gdxc-w37w", "DIVIPOLA")
    boost = divipola_boost_amount("Datos de salud en Antioquia", hit)
    assert boost == 0.0


def test_boost_no_se_activa_si_hit_no_es_divipola():
    """Pregunta sobre mpios pero hit no es DIVIPOLA → no boost."""
    from ai_engine.analyzer import divipola_boost_amount

    hit = _mock_hit("aaaa-bbbb", "Estadísticas de salud en municipios")
    boost = divipola_boost_amount("¿cuántos municipios tiene Antioquia?", hit)
    assert boost == 0.0


def test_boost_id_exacto_gdxc_w37w_es_prioritario():
    """El ID `gdxc-w37w` recibe boost máximo (es la fuente oficial DANE)."""
    from ai_engine.analyzer import divipola_boost_amount

    hit_official = _mock_hit("gdxc-w37w", "DIVIPOLA")
    hit_similar = _mock_hit("zzzz-yyyy", "DIVIPOLA Histórico")
    boost_official = divipola_boost_amount("¿cuántos municipios tiene Valle?", hit_official)
    boost_similar = divipola_boost_amount("¿cuántos municipios tiene Valle?", hit_similar)
    # El oficial debe ser estrictamente mayor que el similar
    assert boost_official > boost_similar > 0


def test_boost_funciona_con_singular():
    """'cuántos municipios' (sin singular) → boost. También 'municipios de'."""
    from ai_engine.analyzer import divipola_boost_amount

    hit = _mock_hit("gdxc-w37w", "DIVIPOLA")
    # plural sin "cuántos"
    boost = divipola_boost_amount("Lista de municipios de Cundinamarca", hit)
    assert boost > 0.0
