"""Tests congelados para flujo comparativo y fixes de P1.

Cubre:
1. Fix P1: regla anti-capital cuando la pregunta usa plural genérico
   ('municipios de X', 'departamentos').
2. Multi-target: `GeoContext.targets` con lista de territorios.
3. Comparison_mode: 'vs', 'ranking', 'vs_national'.
4. Plantillas SoQL deterministas correspondientes.

§6.6 test-first — frozen.
"""

from __future__ import annotations


# ============================================================
# A. Fix P1 — regla anti-capital
# ============================================================


def test_pregunta_municipios_de_dpto_no_infiere_mpio_capital():
    """'¿Cuántos municipios tiene Antioquia?' debe resolver SOLO al dpto, no a Medellín.

    Antes: GeoResolver tomaba 'Antioquia' → dpto + 'capital Medellín' como mpio.
    Esto llevaba al query_generator a usar codigomunicipio='05001' (Medellín)
    en vez de contar municipios del departamento.
    """
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("¿Cuántos municipios tiene Antioquia?")
    assert ctx is not None
    assert ctx.dpto_code == "05"
    # Regla anti-capital: no asumir mpio cuando se habla de "municipios" plural
    assert ctx.mpio_code is None, (
        f"No debió inferir mpio capital. Got mpio_code={ctx.mpio_code!r}"
    )


def test_pregunta_departamentos_no_resuelve_a_dpto_especifico():
    """'Cuántos departamentos tiene Colombia' no debe pegar a un dpto puntual."""
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("Cuántos departamentos tiene Colombia")
    assert ctx is not None
    # Es pregunta de scope nacional sobre los dptos en sí
    assert ctx.scope == "national"
    assert ctx.dpto_code is None


def test_mpio_explicito_si_se_preserva():
    """Cuando se menciona el municipio explícitamente, sí se resuelve."""
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("Datos de pobreza en Medellín")
    assert ctx is not None
    assert ctx.mpio_code == "05001"
    assert ctx.dpto_code == "05"


# ============================================================
# B. Multi-target — list[GeoTarget] en GeoContext
# ============================================================


def test_comparativa_vs_dos_dptos_produce_dos_targets():
    """'Compara Antioquia y Valle del Cauca' → 2 targets, mode='vs'."""
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("Compara Antioquia y Valle del Cauca en homicidios")
    assert ctx is not None
    assert ctx.comparison_mode == "vs"
    assert len(ctx.targets) == 2
    codes = {t.code for t in ctx.targets}
    assert codes == {"05", "76"}
    levels = {t.level for t in ctx.targets}
    assert levels == {"dpto"}


def test_comparativa_vs_dos_mpios():
    """'Bogotá vs Medellín' → 2 targets nivel mpio (Bogotá es dpto+mpio)."""
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("Bogotá vs Medellín en homicidios")
    assert ctx is not None
    assert ctx.comparison_mode == "vs"
    assert len(ctx.targets) >= 2


def test_ranking_pattern_marks_comparison_mode():
    """'Top 5 departamentos con más universidades' → mode='ranking'."""
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("Top 5 departamentos con más universidades")
    assert ctx is not None
    assert ctx.comparison_mode == "ranking"
    assert ctx.groupby == "cod_dpto"
    # Sin filtro de dpto específico
    assert all(t.level != "dpto" for t in ctx.targets) or not ctx.targets


def test_vs_national_pattern():
    """'Cómo está Medellín respecto al promedio nacional' → mode='vs_national'."""
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("Cómo está Medellín respecto al promedio nacional")
    assert ctx is not None
    assert ctx.comparison_mode == "vs_national"
    # Conserva el target local
    assert any(t.code == "05001" for t in ctx.targets)


def test_pregunta_simple_un_solo_target():
    """Una pregunta sin comparación tiene exactamente 1 target en list."""
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("Datos de pobreza en Antioquia")
    assert ctx is not None
    assert ctx.comparison_mode is None
    assert len(ctx.targets) == 1
    assert ctx.targets[0].code == "05"


def test_backwards_compat_dpto_code_property():
    """dpto_code/mpio_code siguen funcionando (devuelven el primer target del tipo)."""
    from ai_engine.geo_resolver import GeoResolver

    r = GeoResolver()
    ctx = r.resolve("Datos sobre Antioquia")
    assert ctx is not None
    assert ctx.dpto_code == "05"  # legacy accessor sigue funcionando


# ============================================================
# C. Plantillas SoQL deterministas
# ============================================================


def test_build_soql_vs_dos_dptos():
    """Plantilla 'vs' con 2 dptos produce SoQL con IN(...)"""
    from ai_engine.geo_resolver import GeoResolver, build_comparison_soql

    r = GeoResolver()
    ctx = r.resolve("Compara Antioquia y Valle del Cauca")
    soql = build_comparison_soql(ctx, columns={"cod_dpto", "nombre"})
    assert soql is not None
    assert "cod_dpto" in soql.lower()
    assert "in" in soql.lower()
    assert "'05'" in soql
    assert "'76'" in soql
    assert "group by" in soql.lower()


def test_build_soql_ranking_top_n():
    """Plantilla 'ranking' produce GROUP BY + ORDER BY DESC + LIMIT."""
    from ai_engine.geo_resolver import GeoResolver, build_comparison_soql

    r = GeoResolver()
    ctx = r.resolve("Top 5 departamentos con más casos")
    soql = build_comparison_soql(ctx, columns={"cod_dpto"})
    assert soql is not None
    assert "group by cod_dpto" in soql.lower()
    assert "order by" in soql.lower()
    assert "desc" in soql.lower()
    assert "limit 5" in soql.lower() or "limit  5" in soql.lower()


def test_build_soql_returns_none_when_columns_missing():
    """Si el dataset no tiene la columna territorial requerida, plantilla devuelve None."""
    from ai_engine.geo_resolver import GeoResolver, build_comparison_soql

    r = GeoResolver()
    ctx = r.resolve("Compara Antioquia y Valle del Cauca")
    soql = build_comparison_soql(ctx, columns={"otro_campo", "id"})
    assert soql is None


def test_build_soql_returns_none_when_no_comparison_mode():
    """Pregunta normal (sin comparison_mode) → plantilla no aplica."""
    from ai_engine.geo_resolver import GeoResolver, build_comparison_soql

    r = GeoResolver()
    ctx = r.resolve("Datos sobre clima")  # devuelve None
    soql = build_comparison_soql(ctx, columns={"cod_dpto"})
    assert soql is None  # ctx None → None
