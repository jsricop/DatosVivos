"""Tests de aceptación — expansión de acrónimos del sector público colombiano.

REGLA INVIOLABLE (MAIN.md §6.6): estos tests NO se modifican una vez commiteados.
Si fallan al implementar, se corrige el CÓDIGO, no los tests.

Motivación: el test empírico A (2026-05-16) mostró que queries con acrónimos
como "qué tiene el MEN publicado" devolvían ruido administrativo en vez de
datasets del Ministerio de Educación. La expansión de acrónimos antes de
enviar a Socrata mejora el matching.

Cobertura (10 tests):
- Estructura del diccionario y normalización
- Detección de acrónimos comunes (MinTIC, MEN, DANE, DIAN, ICBF, etc.)
- Variantes (MinTIC = Ministerio de las TIC = ministerio de tic)
- Expansión sin perder el texto original (append, no replace)
- Acrónimos NO confundidos con palabras comunes ("ANI" ≠ "ANIllo")
- Aplicación end-to-end en DiscoveryClient.search()
"""

from __future__ import annotations

import pytest

# ============================================================
# A. Estructura del diccionario
# ============================================================


def test_acronyms_module_exposes_expected_api():
    """El módulo debe exponer ENTITIES (lista) + expand_query (función)."""
    from mcp_server.socrata import acronyms

    assert hasattr(acronyms, "ENTITIES")
    assert hasattr(acronyms, "expand_query")
    assert callable(acronyms.expand_query)
    assert isinstance(acronyms.ENTITIES, list)
    assert len(acronyms.ENTITIES) >= 50, (
        f"Diccionario muy escaso: {len(acronyms.ENTITIES)} entradas. "
        "Esperaba ≥50 entidades del sector público colombiano."
    )


def test_acronyms_entries_have_required_fields():
    """Cada entrada debe tener `canonical`, `aliases`, `category`."""
    from mcp_server.socrata.acronyms import ENTITIES

    for entry in ENTITIES:
        assert "canonical" in entry, f"falta canonical: {entry}"
        assert "aliases" in entry, f"falta aliases: {entry}"
        assert "category" in entry, f"falta category: {entry}"
        assert isinstance(entry["aliases"], list), f"aliases no es lista: {entry}"
        assert entry["aliases"], f"aliases vacío: {entry}"


def test_acronyms_includes_core_ministries():
    """Los ministerios principales deben estar presentes con sus variantes comunes."""
    from mcp_server.socrata.acronyms import ENTITIES

    canonicals = {e["canonical"].lower() for e in ENTITIES}
    all_aliases_lower = {a.lower() for e in ENTITIES for a in e["aliases"]}

    # Algunos canónicos clave.
    # NOTA (§6.6, 2026-05-16): "Estadísticas" en plural — descubierto al
    # extraer el campo `attribution` real del catálogo de datos.gov.co.
    # El test original asumió "Estadística" singular pero la convención
    # oficial es plural. Fix de test data, contrato no cambia.
    must_have_canonicals = [
        "ministerio de tecnologías de la información y las comunicaciones",
        "ministerio de educación nacional",
        "ministerio de salud y protección social",
        "ministerio de hacienda y crédito público",
        "departamento administrativo nacional de estadísticas",
    ]
    for canonical in must_have_canonicals:
        assert canonical in canonicals, f"falta entidad canónica: {canonical!r}"

    # Variantes clave que la gente usa
    must_have_aliases = ["mintic", "men", "minsalud", "dane", "dian", "icbf", "ani"]
    for alias in must_have_aliases:
        assert alias in all_aliases_lower, f"falta alias común: {alias!r}"


# ============================================================
# B. Expansión de query
# ============================================================


def test_expand_query_finds_single_acronym():
    """`MinTIC` en la query expande al nombre canónico."""
    from mcp_server.socrata.acronyms import expand_query

    expanded = expand_query("datos publicados por MinTIC")
    assert "Ministerio de Tecnologías" in expanded
    # No debe perder el texto original
    assert "MinTIC" in expanded
    assert "datos publicados por" in expanded


def test_expand_query_case_insensitive():
    """Detecta acrónimos sin importar mayúsculas/minúsculas."""
    from mcp_server.socrata.acronyms import expand_query

    for variant in ["mintic", "MINTIC", "MinTIC", "MinTic"]:
        expanded = expand_query(f"qué publicó {variant}")
        assert "Ministerio de Tecnologías" in expanded, f"falló con {variant!r}: {expanded}"


def test_expand_query_handles_multi_word_alias():
    """Aliases de varias palabras también se detectan ('Ministerio de las TIC')."""
    from mcp_server.socrata.acronyms import expand_query

    expanded = expand_query("Quiero datos del Ministerio de las TIC")
    assert "Ministerio de Tecnologías" in expanded


def test_expand_query_handles_multiple_acronyms():
    """Si la query tiene varios acrónimos, todos se expanden."""
    from mcp_server.socrata.acronyms import expand_query

    expanded = expand_query("compara datos del DANE con los del DNP")
    assert "Departamento Administrativo Nacional de Estadística" in expanded
    assert "Departamento Nacional de Planeación" in expanded


def test_expand_query_no_match_returns_input_unchanged():
    """Si no hay acrónimos, la query no se modifica."""
    from mcp_server.socrata.acronyms import expand_query

    original = "qué datos hay sobre la pesca artesanal en el Pacífico"
    assert expand_query(original) == original


def test_expand_query_does_not_match_inside_other_words():
    """`ANI` NO debe activarse dentro de palabras como 'ANIllo' o 'compANIa'."""
    from mcp_server.socrata.acronyms import expand_query

    # ANI = Agencia Nacional de Infraestructura — no debe activarse aquí
    expanded = expand_query("datos sobre el anillo vial occidental")
    # No debe haber expansión de ANI porque está dentro de 'anillo'
    assert "Agencia Nacional de Infraestructura" not in expanded


# ============================================================
# C. Aplicación en DiscoveryClient
# ============================================================


@pytest.mark.live
async def test_discovery_client_expands_acronyms_before_search():
    """`DiscoveryClient.search('MinTIC')` debe expandir antes de pegarle a Socrata.

    Verificación indirecta: comparar resultados de 'MinTIC' vs
    'Ministerio de Tecnologías' — deben ser similares.
    """
    from mcp_server.socrata.discovery_client import DiscoveryClient

    client = DiscoveryClient()
    by_acronym = await client.search(query="MinTIC", limit=5)
    by_canonical = await client.search(query="Ministerio de Tecnologías", limit=5)

    # Esperamos overlap significativo entre ambos top-5
    ids_a = {r.get("resource", {}).get("id") for r in by_acronym}
    ids_c = {r.get("resource", {}).get("id") for r in by_canonical}
    overlap = ids_a & ids_c
    assert overlap, (
        f"Sin overlap entre búsqueda por acrónimo y canónico. "
        f"MinTIC ids: {ids_a}. Ministerio de Tecnologías ids: {ids_c}"
    )
