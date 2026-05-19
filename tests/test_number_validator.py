"""Tests de aceptación congelados para `_validate_numbers` en analyzer.

Congelados antes de implementar (§6.6 test-first). Cubren el contrato:
- Cifras en whitelist se preservan.
- Cifras fuera de whitelist censuran la oración entera.
- IDs alfanuméricos (gdxc-w37w) no se consideran cifras.
- Si todas las oraciones se censuran, fallback determinista.
- Normalización es-CO (125.000 ≡ 125000).
"""

from __future__ import annotations


def _build_stats(whitelist: set[str], derived: set[str] | None = None):
    """Helper: crea un Statistics minimal para los tests de validación."""
    from ai_engine.stats_computer import Statistics

    return Statistics(
        total_rows=0,
        soql_used="",
        column_summaries=[],
        aggregate_hits=[],
        summary_lines=[],
        whitelist_numbers=frozenset(whitelist),
        derived_numbers=frozenset(derived or set()),
    )


def test_cifra_en_whitelist_se_preserva():
    from ai_engine.analyzer import _validate_numbers

    stats = _build_stats({"125"})
    text = "Antioquia tiene 125 municipios según el dataset."
    result = _validate_numbers(text, stats)
    assert "125" in result
    assert "no verificable" not in result.lower()


def test_cifra_fuera_de_whitelist_censura_la_oracion():
    from ai_engine.analyzer import _validate_numbers

    stats = _build_stats({"125"})
    text = "Antioquia tiene 92 municipios."
    result = _validate_numbers(text, stats)
    assert "92" not in result, f"La cifra 92 no debería estar: {result!r}"


def test_multiple_oraciones_solo_la_problematica_se_censura():
    from ai_engine.analyzer import _validate_numbers

    stats = _build_stats({"125"})
    text = (
        "Antioquia tiene 125 municipios según DIVIPOLA. "
        "Además, registra 999 habitantes según un dato falso. "
        "El dataset es publicado por el DANE."
    )
    result = _validate_numbers(text, stats)
    assert "125" in result
    assert "999" not in result
    # La frase del DANE no tiene cifras → se preserva
    assert "DANE" in result


def test_texto_sin_cifras_pasa_intacto():
    from ai_engine.analyzer import _validate_numbers

    stats = _build_stats(set())
    text = "Este dataset describe la división política administrativa de Colombia."
    result = _validate_numbers(text, stats)
    assert result.strip() == text.strip()


def test_cifra_formato_es_co_matchea_whitelist_canonica():
    """'125.000' (es-CO) en texto debe matchear whitelist con '125000' canónico."""
    from ai_engine.analyzer import _validate_numbers

    # En la whitelist se guarda la forma canónica
    stats = _build_stats({"125000"})
    text = "El total de personas atendidas asciende a 125.000 según el DANE."
    result = _validate_numbers(text, stats)
    assert "125.000" in result, f"Esperaba preservar '125.000': {result!r}"


def test_id_alfanumerico_no_se_considera_cifra():
    """`gdxc-w37w` contiene dígitos pero es un ID, no una cifra."""
    from ai_engine.analyzer import _validate_numbers

    stats = _build_stats(set())  # whitelist vacía
    text = "Consulta el dataset gdxc-w37w del DANE."
    result = _validate_numbers(text, stats)
    # No debe censurarse — gdxc-w37w no es una cifra estadística
    assert "gdxc-w37w" in result
    assert "no verificable" not in result.lower()


def test_todas_oraciones_censuradas_devuelve_fallback():
    from ai_engine.analyzer import _validate_numbers

    stats = _build_stats(set())  # whitelist vacía
    text = "Antioquia tiene 92 municipios. El DANE reportó 1.500 casos."
    result = _validate_numbers(text, stats)
    # Cuando todo se censura → fallback determinista mencionando el bloque
    assert (
        "datos verificados" in result.lower()
        or "bloque" in result.lower()
        or "no verificable" in result.lower()
    ), f"Esperaba fallback determinista: {result!r}"


def test_cifra_en_derived_numbers_tambien_se_preserva():
    from ai_engine.analyzer import _validate_numbers

    stats = _build_stats(whitelist={"125"}, derived={"50.0", "33.3"})
    text = "El delta entre periodos fue de 50.0 unidades."
    result = _validate_numbers(text, stats)
    assert "50.0" in result, f"Esperaba preservar derivado: {result!r}"
