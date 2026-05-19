"""Tests congelados para GeoResolver.

Cubre las 5 filas de la matriz de comportamiento (acuerdo con usuario, 2026-05-18):

1. Sin geo → None (no interfiere con preguntas generales)
2. Mención "Colombia"/"nacional" → scope=national, sin filtro
3. Departamento ("Antioquia") → dpto_code
4. Breakdown ("por departamento") → groupby
5. Municipio ("Quibdó") → mpio_code

Más: sinónimos, fuzzy match leve, falsos positivos.

§6.6 test-first — frozen.
"""

from __future__ import annotations


def test_pregunta_sin_geo_devuelve_none():
    """Pregunta general sin territorio → resolver no interfiere."""
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    assert r.resolve("Datos sobre educación superior") is None
    assert r.resolve("Información sobre vacunación") is None
    assert r.resolve("Quiero datos") is None


def test_mencion_colombia_marca_scope_nacional():
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("Inflación en Colombia")
    assert ctx is not None
    assert ctx.scope == "national"
    assert ctx.dpto_code is None
    assert ctx.mpio_code is None
    assert ctx.groupby is None


def test_departamento_resuelve_a_codigo_divipola():
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("¿Cuántos municipios tiene Antioquia?")
    assert ctx is not None
    assert ctx.dpto_code == "05"
    assert ctx.dpto_name.lower() == "antioquia"
    assert ctx.mpio_code is None


def test_breakdown_por_departamento_marca_groupby():
    """'por departamento' debe activar groupby, no filtro WHERE."""
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("Casos de dengue por departamento")
    assert ctx is not None
    assert ctx.groupby == "cod_dpto"
    # Como no nombra dpto específico, dpto_code debe estar vacío
    assert ctx.dpto_code is None


def test_breakdown_por_municipio_marca_groupby_mpio():
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("Homicidios por municipio")
    assert ctx is not None
    assert ctx.groupby == "cod_mpio"


def test_municipio_capital_resuelve_dpto_y_mpio():
    """Bogotá es capital y dpto simultáneamente (DIVIPOLA caso especial)."""
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("Datos de homicidios en Bogotá")
    assert ctx is not None
    # Bogotá D.C. dpto code = '11'
    assert ctx.dpto_code == "11"


def test_municipio_no_capital_resuelve_dpto_padre():
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("Pobreza en Quibdó")
    assert ctx is not None
    # Quibdó está en Chocó (27), código mpio 27001
    assert ctx.dpto_code == "27"
    assert ctx.mpio_code == "27001"


def test_sinonimos_bogota_distrito_capital():
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    for variant in ("Bogotá D.C.", "Bogotá DC", "Distrito Capital", "Bogota"):
        ctx = r.resolve(f"Información sobre {variant}")
        assert ctx is not None, f"Falló para variante {variant!r}"
        assert ctx.dpto_code == "11"


def test_fuzzy_tolera_typo_simple():
    """'Medeyín' (typo) debe matchear Medellín."""
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("Datos sobre Medeyín")
    # Debe resolver con confianza menor pero sí matchear
    assert ctx is not None
    assert ctx.mpio_code == "05001"  # Medellín


def test_no_falso_positivo_para_paises_extranjeros():
    """'Ecuador' o 'Perú' no deben gatillar matches DIVIPOLA."""
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    # "Ecuador" como país NO debe matchear ningún dpto colombiano
    ctx = r.resolve("Quiero saber sobre Ecuador")
    assert ctx is None or ctx.dpto_code is None


def test_dpto_canonico_devuelve_nombre_oficial():
    """Resolver debe devolver el nombre oficial DIVIPOLA, no la grafía del usuario."""
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("PIB de antioquia")  # minúscula y sin tilde
    assert ctx is not None
    assert ctx.dpto_name == "Antioquia"  # nombre canónico


def test_resolver_devuelve_scope_subnacional_con_dpto():
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("Educación en Cundinamarca")
    assert ctx is not None
    assert ctx.scope == "subnational"
    assert ctx.dpto_code == "25"


def test_multiples_dptos_se_incluyen_como_targets():
    """Comparativa 'Antioquia y Valle' debe incluir ambos como targets.

    Cambio post-Opción A (2026-05-18): el primer dpto sigue siendo accesible
    vía `dpto_code` por retrocompat, pero ambos viven en `targets` y el
    comparison_mode se marca como 'vs'.
    """
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("Compara Antioquia y Valle del Cauca")
    assert ctx is not None
    assert ctx.comparison_mode == "vs"
    assert ctx.dpto_code in ("05", "76")
    codes = {t.code for t in ctx.targets}
    assert codes == {"05", "76"}
