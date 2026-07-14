"""Diccionario ciudadano ↔ institucional (transversal, 2026-07-13).

El ciudadano no habla el idioma de los datasets: `expandir()` suma los
términos oficiales de forma determinista para el word-boost y el
re-ranking semántico. Ni filtra ni inventa — solo ordena mejor.
"""

from __future__ import annotations

from ai_engine.vocabulario_ciudadano import VOCABULARIO, expandir


def test_colegios_publicos_expande_a_vocabulario_oficial():
    out = expandir("colegios públicos")
    assert "establecimientos educativos" in out
    assert "oficial" in out


def test_multi_palabra_gana_a_termino_suelto():
    # "camas uci" debe traer capacidad instalada, no expandir "camas" suelto.
    out = expandir("cuántas camas UCI hay disponibles")
    assert "capacidad instalada" in out


def test_sin_terminos_ciudadanos_no_expande():
    assert expandir("matrícula establecimientos educativos") == ""
    assert expandir(None) == ""
    assert expandir("") == ""


def test_no_repite_lo_que_ya_esta_en_el_texto():
    out = expandir("robos y hurto en mi barrio")
    assert "hurto" not in out.split()


def test_insensible_a_tildes_y_mayusculas():
    assert "homicidios" in expandir("ASESINATOS en Bogotá")
    assert "desercion escolar" in expandir("cuántos DESERTARON")


def test_respeta_limite_de_terminos():
    out = expandir("plata gastos impuestos deuda sueldo empresas", max_terms=6)
    assert len(out.split()) <= 14  # 6 términos, algunos multi-palabra


def test_no_matchea_subcadenas():
    # "agua" no debe dispararse dentro de "paraguas" ni "aguacate".
    assert "acueducto" not in expandir("paraguas y aguacate")


def test_vocabulario_bien_formado():
    for clave, oficiales in VOCABULARIO.items():
        assert clave == clave.lower(), f"clave con mayúsculas: {clave}"
        assert clave == clave.translate(
            str.maketrans("áéíóúüñ", "aeiouun")
        ), f"clave con tildes: {clave}"
        assert oficiales, f"clave sin términos oficiales: {clave}"
