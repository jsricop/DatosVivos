"""Tests de aceptación congelados para StatsComputer.

Congelados antes de implementar (§6.6 test-first). Solo se ajustan si tienen
un error conceptual demostrable.

Cubren:
- Agregaciones simples (count, group by, sum, etc.)
- Auto-cast de strings de SODA a tipos numéricos/fecha
- Construcción de whitelist_numbers y derived_numbers
- Normalización de números formato es-CO
- Determinismo (mismas entradas → mismas salidas)
"""

from __future__ import annotations


def test_count_star_with_single_row_populates_whitelist():
    """SoQL `SELECT count(*) AS n` con 1 fila → whitelist incluye el conteo."""
    from ai_engine.stats_computer import StatsComputer

    rows = [{"n": "125"}]
    soql = "SELECT count(*) AS n WHERE cod_dpto = '05'"
    stats = StatsComputer.compute(rows, soql)

    assert stats.total_rows == 1
    assert "125" in stats.whitelist_numbers
    # En aggregate_hits se debe reflejar el count total
    assert any("125" in line for line in stats.aggregate_hits)
    assert any("125" in line for line in stats.summary_lines)


def test_group_by_with_five_categories_lists_top_values():
    """5 filas agrupadas → top_values ordenado por conteo descendente."""
    from ai_engine.stats_computer import StatsComputer

    rows = [
        {"cod_dpto": "05", "n": "125"},
        {"cod_dpto": "11", "n": "20"},
        {"cod_dpto": "25", "n": "116"},
        {"cod_dpto": "76", "n": "42"},
        {"cod_dpto": "08", "n": "46"},
    ]
    soql = "SELECT cod_dpto, count(*) AS n GROUP BY cod_dpto"
    stats = StatsComputer.compute(rows, soql)

    assert stats.total_rows == 5
    # Whitelist incluye todos los conteos
    for n in ("125", "20", "116", "42", "46"):
        assert n in stats.whitelist_numbers, f"Falta {n} en whitelist"
    # Si hay summary de columna n, sus stats deben verse
    summary_text = "\n".join(stats.summary_lines)
    assert "125" in summary_text
    assert "20" in summary_text


def test_empty_rows_produces_zero_total_and_empty_whitelist():
    """Rows vacíos → total_rows=0, summary explicativo, whitelist vacía."""
    from ai_engine.stats_computer import StatsComputer

    stats = StatsComputer.compute([], "SELECT * LIMIT 0")
    assert stats.total_rows == 0
    assert stats.whitelist_numbers == frozenset()
    # Debe haber al menos una línea explicando que no hay filas
    assert any("filas" in s.lower() or "registros" in s.lower() for s in stats.summary_lines)


def test_autocast_string_to_numeric_computes_mean():
    """SODA devuelve strings; pandas autocast a numéricos → mean correcto."""
    from ai_engine.stats_computer import StatsComputer

    rows = [{"valor": "125.50"}, {"valor": "200"}]
    stats = StatsComputer.compute(rows, "SELECT valor")

    assert stats.total_rows == 2
    # Mean = 162.75 — debe aparecer normalizado en whitelist
    assert "162.75" in stats.whitelist_numbers
    # Min/max también
    assert "125.5" in stats.whitelist_numbers or "125.50" in stats.whitelist_numbers
    assert "200" in stats.whitelist_numbers or "200.0" in stats.whitelist_numbers


def test_es_co_formatting_in_summary_lines():
    """Los summary_lines deben formatearse en es-CO (miles con punto, decimal con coma)."""
    from ai_engine.stats_computer import StatsComputer

    rows = [{"v": "162748.5"}, {"v": "162748.5"}]
    stats = StatsComputer.compute(rows, "SELECT v")
    text = "\n".join(stats.summary_lines)
    # Debe aparecer "162.748,5" en algún summary_line (formato es-CO)
    assert "162.748,5" in text or "162.748,50" in text, (
        f"Formato es-CO no encontrado en summary_lines: {stats.summary_lines}"
    )


def test_normalize_number_canonicalizes_es_co_variants():
    """`_normalize_number` debe tratar '125.000', '125000', '125 000' como iguales."""
    from ai_engine.stats_computer import _normalize_number

    assert _normalize_number("125.000") == _normalize_number("125000")
    assert _normalize_number("125 000") == _normalize_number("125000")
    # Decimal con coma equivale a decimal con punto
    assert _normalize_number("12,5") == _normalize_number("12.5")
    # Caso simple
    assert _normalize_number("125") == "125"


def test_temporal_series_derived_numbers():
    """Serie temporal de años produce delta y count en derived_numbers."""
    from ai_engine.stats_computer import StatsComputer

    rows = [
        {"anio": "2020"},
        {"anio": "2021"},
        {"anio": "2022"},
        {"anio": "2023"},
        {"anio": "2024"},
    ]
    stats = StatsComputer.compute(rows, "SELECT anio")

    # Delta 2024 - 2020 = 4
    assert "4" in stats.derived_numbers or "4" in stats.whitelist_numbers
    # n_períodos = 5
    assert "5" in stats.whitelist_numbers


def test_determinism_same_inputs_produce_same_output():
    """Dos invocaciones con mismos inputs → mismos resultados (sin LLM, sin random)."""
    from ai_engine.stats_computer import StatsComputer

    rows = [{"x": "10"}, {"x": "20"}, {"x": "30"}]
    soql = "SELECT x"
    a = StatsComputer.compute(rows, soql)
    b = StatsComputer.compute(rows, soql)
    assert a.total_rows == b.total_rows
    assert a.whitelist_numbers == b.whitelist_numbers
    assert a.summary_lines == b.summary_lines
    assert a.aggregate_hits == b.aggregate_hits
