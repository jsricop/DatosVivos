"""Tests para el validador anti-alucinación de Fase D (chips/explain).

Las funciones _validate_numbers + _allowed_numbers viven en api/routes/chips.py
porque eran helpers de un solo endpoint. Importamos directo y testeamos
la lógica pura.
"""

from __future__ import annotations

from api.routes.chips import _allowed_numbers, _normalize_digits, _validate_numbers


def test_normalize_digits():
    assert _normalize_digits("9.192.802.561.842") == "9192802561842"
    assert _normalize_digits("3,567,401,200,000") == "3567401200000"
    assert _normalize_digits("647764.10") == "64776410"
    assert _normalize_digits("-86283") == "86283"


def test_allowed_numbers_extrae_cifras_de_rows():
    rows = [
        {"categoria": "MI CASA YA", "total": "9192802561842"},
        {"categoria": "VIPA", "total": "3567401200000"},
    ]
    allowed = _allowed_numbers(rows)
    assert "9192802561842" in allowed
    assert "3567401200000" in allowed


def test_validate_acepta_cifra_con_separadores_de_miles():
    rows = [{"total": "9192802561842"}]
    flagged = _validate_numbers(
        "El total fue de 9.192.802.561.842 pesos.", rows
    )
    assert flagged == []


def test_validate_flag_cifra_no_presente():
    rows = [{"n": "100"}]
    flagged = _validate_numbers("Hay 100 colegios y 555 alumnos.", rows)
    # 555 NO está → flag.
    assert "555" in flagged
    # 100 sí → no flag.
    assert "100" not in flagged


def test_validate_acepta_anos_1900_2099():
    rows = [{"n": "1"}]
    flagged = _validate_numbers("Datos de 2024 y comparativo con 1995.", rows)
    assert flagged == []


def test_validate_acepta_denominadores_ambient():
    rows = [{"n": "11"}]
    flagged = _validate_numbers(
        "Tasa de 11 por cada 1.000 niños menores de 5 años.", rows
    )
    assert flagged == []


def test_validate_acepta_un_digito_como_cardinal():
    rows = [{"n": "100"}]
    flagged = _validate_numbers("Hay 100 datos en 3 categorías.", rows)
    assert "3" not in flagged
    assert flagged == []


def test_validate_flag_cifra_inventada_grande():
    rows = [{"total": "9192802561842"}]
    # LLM dice 919.280.256.184.200 (cifra distinta, alucinada)
    flagged = _validate_numbers(
        "El monto fue de 919.280.256.184.200 pesos.", rows
    )
    assert flagged  # alguno debe estar flag


def test_validate_no_flag_negativo_si_presente():
    rows = [{"delta": "-50"}]
    flagged = _validate_numbers("La variación fue de -50.", rows)
    # El signo negativo se elimina en _normalize_digits.
    assert flagged == []
