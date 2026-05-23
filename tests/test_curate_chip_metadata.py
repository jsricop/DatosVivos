"""Tests para `scripts/curate_chip_metadata.infer_jurisdiccion`.

Cubre casos que aprendimos en el dry-run de Fase 1 prereq:
- precedencia mpio > dpto-no-Bogotá > nacional > dpto-Bogotá (distrito)
- entidades nacionales con "Bogotá D.C." en el nombre → nacional (no distrito)
- entidades departamentales con "Departamental" en el nombre → dpto (no nacional)
- mpios ambiguos con nombre de país/dpto excluidos del catálogo
- aliases coloquiales de capitales (Cali, Cartagena, etc.)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.curate_chip_metadata import infer_jurisdiccion


def _case(entity, expected_nivel, expected_codes=None):
    nivel, codes, conf, reason = infer_jurisdiccion(entity, "", None)
    assert nivel == expected_nivel, (
        f"entity={entity!r} → got {nivel}, expected {expected_nivel}. reason={reason}"
    )
    if expected_codes is not None:
        assert codes == expected_codes, f"codes mismatch: got {codes}, expected {expected_codes}"


# ---------- Distrito capital ----------

def test_secretaria_distrito_capital():
    _case("Secretaría de Educación del Distrito", "distrito_capital", ["11"])


def test_alcaldia_mayor_bogota():
    _case("Alcaldía Mayor de Bogotá D.C.", "distrito_capital", ["11"])


# ---------- Departamental ----------

def test_gobernacion_boyaca():
    _case("Gobernación de Boyacá", "departamental", ["15"])


def test_universidad_del_valle():
    _case("Universidad del Valle", "departamental", ["76"])


def test_contraloria_departamental_cauca():
    """Caso crítico: tiene 'contraloria' (nacional token) PERO también 'Cauca'
    (dpto). El dpto NO-Bogotá debe ganar."""
    _case("Contraloría Departamental del Cauca", "departamental", ["19"])


# ---------- Municipal ----------

def test_alcaldia_medellin():
    _case("Alcaldía de Medellín", "municipal", ["05001"])


def test_personeria_cali_alias():
    """Cali es alias de Santiago de Cali — debe matchear."""
    _case("Personería Municipal de Cali", "municipal", ["76001"])


def test_alcaldia_cartagena_alias():
    _case("Alcaldía de Cartagena", "municipal", ["13001"])


# ---------- Nacional ----------

def test_ministerio_de_salud():
    _case("Ministerio de Salud y Protección Social", "nacional", [])


def test_universidad_nacional_de_colombia():
    """UNAL: 'Colombia' como mpio está excluido; debe matchear 'Nacional'."""
    _case("Universidad Nacional de Colombia", "nacional", [])


def test_dane_acronimo():
    _case("DANE - Departamento Administrativo Nacional", "nacional", [])


def test_ministerio_con_sede_bogota_dc():
    """Caso crítico: entity dice 'Bogotá D.C.' (sede física) pero es nacional.
    Bogotá-como-dpto NO debe vencer a 'nacional'."""
    _case("Ministerio de Salud, Bogotá D.C.", "nacional", [])


def test_ins_con_sede_bogota_dc():
    _case("Instituto Nacional de Salud - INS, Bogotá D.C.", "nacional", [])


# ---------- Edge cases ----------

def test_uptc_sin_geo_explicita_queda_none():
    """UPTC NO menciona Boyacá en el entity. Es honesto devolver None y
    pasarlo a curación manual o LLM. Mejor None que un falso positivo."""
    nivel, codes, conf, reason = infer_jurisdiccion(
        "Universidad Pedagógica y Tecnológica de Colombia", "", None
    )
    assert nivel is None
    assert conf == "none"


def test_colombia_como_mpio_excluido():
    """'Colombia' es mpio en Huila pero también nombre del país. Excluido
    para evitar falsos positivos masivos."""
    nivel, codes, conf, _ = infer_jurisdiccion("República de Colombia", "", None)
    assert nivel is None


def test_armenia_capital_quindio_excluida_como_mpio():
    """'Armenia' es ambigua (mpio en Antioquia + capital Quindío). Excluida
    del catálogo para evitar matches espurios. Tampoco está como dpto."""
    nivel, codes, conf, _ = infer_jurisdiccion("Cualquier entidad de Armenia", "", None)
    assert nivel is None
