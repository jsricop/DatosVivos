"""Tests congelados para validación geográfica de rows.

PROD_IMPROV #5: cuando el usuario pregunta sobre un territorio específico
(ej. "municipios de Antioquia"), verificamos que los rows efectivamente
correspondan a ese territorio. Si no, anotamos warning al ciudadano para
evitar atribución incorrecta de cifras.

Caso real detectado en journey 2026-05-18:
- Pregunta: "¿Cuántos municipios tiene Antioquia?"
- Retrieval trajo dataset de víctimas (no DIVIPOLA).
- SoQL contó víctimas en Antioquia (940.451).
- Narrativa hubiera podido decir "Antioquia tiene 940.451 municipios"
  (atribución silenciosamente incorrecta porque la cifra está en whitelist).

Este módulo agrega `validate_geographic_attribution()` que verifica si
los rows tienen al menos una fila correspondiente al territorio resuelto
por GeoResolver.
"""

from __future__ import annotations


def test_dpto_match_por_columna_cod_dpto():
    """Si los rows tienen `cod_dpto='05'` y el ctx pide Antioquia (05), OK."""
    from ai_engine.geo_resolver import GeoContext, GeoTarget
    from ai_engine.geo_attribution import validate_geographic_attribution

    ctx = GeoContext(
        targets=[GeoTarget(name="Antioquia", code="05", level="dpto")],
        scope="subnational",
    )
    rows = [{"cod_dpto": "05", "n": 125}]
    result = validate_geographic_attribution(rows, ctx)
    assert result.matches is True


def test_dpto_match_por_nombre_columna_dpto():
    """Si la columna es 'departamento' (string) con valor 'Antioquia', OK."""
    from ai_engine.geo_resolver import GeoContext, GeoTarget
    from ai_engine.geo_attribution import validate_geographic_attribution

    ctx = GeoContext(
        targets=[GeoTarget(name="Antioquia", code="05", level="dpto")],
        scope="subnational",
    )
    rows = [{"departamento": "ANTIOQUIA", "casos": 100}]
    result = validate_geographic_attribution(rows, ctx)
    assert result.matches is True


def test_dpto_no_match_dispara_warning():
    """Si los rows son sobre otro dpto (ej. Bogotá) y el ctx pide Antioquia, warning."""
    from ai_engine.geo_resolver import GeoContext, GeoTarget
    from ai_engine.geo_attribution import validate_geographic_attribution

    ctx = GeoContext(
        targets=[GeoTarget(name="Antioquia", code="05", level="dpto")],
        scope="subnational",
    )
    # Rows sobre otro dpto — no aparece '05' ni 'Antioquia'
    rows = [{"cod_dpto": "11", "n": 1000}]
    result = validate_geographic_attribution(rows, ctx)
    assert result.matches is False
    assert "Antioquia" in result.warning


def test_no_geo_ctx_no_dispara_validacion():
    """Sin geo_ctx (preguntas generales) → la validación pasa neutral."""
    from ai_engine.geo_attribution import validate_geographic_attribution

    result = validate_geographic_attribution([{"n": 100}], None)
    assert result.matches is True
    assert result.warning == ""


def test_rows_vacios_pasan_neutral():
    """Sin rows que validar, el resultado es neutral (no warning)."""
    from ai_engine.geo_resolver import GeoContext, GeoTarget
    from ai_engine.geo_attribution import validate_geographic_attribution

    ctx = GeoContext(
        targets=[GeoTarget(name="Antioquia", code="05", level="dpto")],
        scope="subnational",
    )
    result = validate_geographic_attribution([], ctx)
    assert result.matches is True


def test_scope_nacional_pasa_sin_validacion():
    """Si scope='national' (sin target subnacional), no validamos territorio."""
    from ai_engine.geo_resolver import GeoContext
    from ai_engine.geo_attribution import validate_geographic_attribution

    ctx = GeoContext(targets=[], scope="national")
    result = validate_geographic_attribution([{"n": 100}], ctx)
    assert result.matches is True


def test_mpio_match_por_codigo_dane_municipio():
    """Columna `codigo_dane_municipio='05001'` matchea Medellín."""
    from ai_engine.geo_resolver import GeoContext, GeoTarget
    from ai_engine.geo_attribution import validate_geographic_attribution

    ctx = GeoContext(
        targets=[GeoTarget(name="Medellín", code="05001", level="mpio")],
        scope="subnational",
    )
    rows = [{"codigo_dane_municipio": "05001", "casos": 50}]
    result = validate_geographic_attribution(rows, ctx)
    assert result.matches is True


def test_match_case_insensitive_sin_tildes():
    """Match contra columna de nombre debe ser case-insensitive sin tildes."""
    from ai_engine.geo_resolver import GeoContext, GeoTarget
    from ai_engine.geo_attribution import validate_geographic_attribution

    ctx = GeoContext(
        targets=[GeoTarget(name="Medellín", code="05001", level="mpio")],
        scope="subnational",
    )
    # Row con "MEDELLIN" en uppercase sin tilde
    rows = [{"municipio": "MEDELLIN", "n": 10}]
    result = validate_geographic_attribution(rows, ctx)
    assert result.matches is True
