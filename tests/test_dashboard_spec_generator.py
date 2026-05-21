"""Tests de aceptación de DashboardSpecGenerator — DEFINIDOS ANTES DE IMPLEMENTAR.

REGLA INVIOLABLE (MAIN.md §6.6): estos tests NO se modifican una vez commiteados.

Cubre PLAN_DASHBOARD.md §9.1 (8 escenarios) + casos edge de validación:

A. Generación por intent
   1. count + 1 fila → KPI sin charts.
   2. temporal + columna anio + métrica → incluye LineChart.
   3. geo + cod_mpio + métrica → incluye ChoroplethMap level=mpio.
   4. ranking + groupby → BarChart con sort=desc + limit.
B. Robustez
   5. Spec con columna inexistente → block se descarta, el resto se conserva.
   6. LLM devuelve JSON malformado dos veces → generator devuelve None.
   7. Rows vacíos → None.
   8. Determinismo: misma pregunta + mismos rows + temperature=0 → mismo spec.
C. Validación Pydantic
   9. DashboardSpec con 0 blocks → ValidationError.
   10. Block type inválido → ValidationError.

Sin LLM real: MockBackend con respuestas pre-grabadas vía `add_response`.
"""

from __future__ import annotations

import json

import pytest

from ai_engine.llm_backend import MockBackend


# ============================================================
# Helpers — mínimo necesario para que los tests sean legibles
# ============================================================


def _rows_temporal() -> list[dict]:
    return [
        {"anio": 2020, "cod_mpio": "05001", "casos": 1200},
        {"anio": 2021, "cod_mpio": "05001", "casos": 1100},
        {"anio": 2022, "cod_mpio": "05001", "casos": 980},
        {"anio": 2020, "cod_mpio": "05088", "casos": 320},
        {"anio": 2021, "cod_mpio": "05088", "casos": 310},
        {"anio": 2022, "cod_mpio": "05088", "casos": 290},
    ]


def _rows_count_single() -> list[dict]:
    return [{"total": 125}]


def _rows_ranking() -> list[dict]:
    return [
        {"entidad": "MinSalud", "contratos": 320},
        {"entidad": "MinEducación", "contratos": 280},
        {"entidad": "Policía Nacional", "contratos": 210},
        {"entidad": "DANE", "contratos": 95},
        {"entidad": "DNP", "contratos": 60},
    ]


# ============================================================
# A. Generación por intent
# ============================================================


@pytest.mark.asyncio
async def test_count_single_row_yields_only_kpi():
    """Pregunta de conteo con 1 fila → solo KPI, sin charts."""
    from ai_engine.dashboard_spec_generator import DashboardSpecGenerator

    llm = MockBackend()
    llm.add_response(
        prompt_contains="cuántos municipios",
        response=json.dumps(
            {
                "version": "1",
                "title": "Municipios de Antioquia",
                "layout": "stack",
                "blocks": [
                    {
                        "type": "kpi",
                        "title": "Total",
                        "value_from": "total",
                        "format": "number_es_co",
                    }
                ],
            }
        ),
    )
    gen = DashboardSpecGenerator(llm=llm)
    spec = await gen.generate(
        question="¿Cuántos municipios tiene Antioquia?",
        intent="descriptive",
        dataset_name="DIVIPOLA",
        columns=["total"],
        rows=_rows_count_single(),
    )
    assert spec is not None
    assert len(spec.blocks) == 1
    assert spec.blocks[0].type == "kpi"


@pytest.mark.asyncio
async def test_temporal_intent_includes_line_chart():
    """Pregunta temporal con anio + casos → incluye LineChart."""
    from ai_engine.dashboard_spec_generator import DashboardSpecGenerator

    llm = MockBackend()
    llm.add_response(
        prompt_contains="tendencia",
        response=json.dumps(
            {
                "version": "1",
                "title": "Tendencia",
                "layout": "grid",
                "blocks": [
                    {
                        "type": "line",
                        "title": "Casos por año",
                        "x_column": "anio",
                        "y_column": "casos",
                        "agg": "sum",
                    }
                ],
            }
        ),
    )
    gen = DashboardSpecGenerator(llm=llm)
    spec = await gen.generate(
        question="Tendencia de homicidios en Antioquia",
        intent="temporal",
        dataset_name="Homicidios",
        columns=["anio", "cod_mpio", "casos"],
        rows=_rows_temporal(),
    )
    assert spec is not None
    assert any(b.type == "line" for b in spec.blocks)


@pytest.mark.asyncio
async def test_geo_intent_includes_choropleth():
    """Pregunta geo con cod_mpio → incluye ChoroplethMap level=mpio."""
    from ai_engine.dashboard_spec_generator import DashboardSpecGenerator

    llm = MockBackend()
    llm.add_response(
        prompt_contains="distribución",
        response=json.dumps(
            {
                "version": "1",
                "title": "Geo",
                "layout": "grid",
                "blocks": [
                    {
                        "type": "choropleth",
                        "title": "Mapa por municipio",
                        "level": "mpio",
                        "code_column": "cod_mpio",
                        "metric_column": "casos",
                        "legend_format": "number_es_co",
                    }
                ],
            }
        ),
    )
    gen = DashboardSpecGenerator(llm=llm)
    spec = await gen.generate(
        question="Distribución de casos por municipio",
        intent="comparative",
        dataset_name="Homicidios",
        columns=["cod_mpio", "casos"],
        rows=_rows_temporal(),
    )
    assert spec is not None
    choro = [b for b in spec.blocks if b.type == "choropleth"]
    assert choro and choro[0].level == "mpio"


@pytest.mark.asyncio
async def test_ranking_intent_uses_bar_sort_desc():
    """Pregunta ranking → BarChart con sort=desc + limit."""
    from ai_engine.dashboard_spec_generator import DashboardSpecGenerator

    llm = MockBackend()
    llm.add_response(
        prompt_contains="top 5",
        response=json.dumps(
            {
                "version": "1",
                "title": "Top 5 entidades",
                "layout": "stack",
                "blocks": [
                    {
                        "type": "bar",
                        "title": "Contratos por entidad",
                        "x_column": "entidad",
                        "y_column": "contratos",
                        "sort": "desc",
                        "limit": 5,
                    }
                ],
            }
        ),
    )
    gen = DashboardSpecGenerator(llm=llm)
    spec = await gen.generate(
        question="Top 5 entidades por contratos",
        intent="comparative",
        dataset_name="SECOP",
        columns=["entidad", "contratos"],
        rows=_rows_ranking(),
    )
    assert spec is not None
    bars = [b for b in spec.blocks if b.type == "bar"]
    assert bars
    assert bars[0].sort == "desc"
    assert bars[0].limit == 5


# ============================================================
# B. Robustez
# ============================================================


@pytest.mark.asyncio
async def test_block_with_unknown_column_is_dropped():
    """Si el LLM referencia una columna inexistente, ese block se descarta."""
    from ai_engine.dashboard_spec_generator import DashboardSpecGenerator

    llm = MockBackend()
    llm.add_response(
        prompt_contains="columnas",
        response=json.dumps(
            {
                "version": "1",
                "title": "Test",
                "layout": "grid",
                "blocks": [
                    {
                        "type": "line",
                        "title": "OK",
                        "x_column": "anio",
                        "y_column": "casos",
                    },
                    {
                        "type": "bar",
                        "title": "Con columna inválida",
                        "x_column": "columna_inexistente",
                        "y_column": "casos",
                    },
                ],
            }
        ),
    )
    gen = DashboardSpecGenerator(llm=llm)
    spec = await gen.generate(
        question="lista de columnas",
        intent="descriptive",
        dataset_name="x",
        columns=["anio", "casos"],
        rows=_rows_temporal(),
    )
    assert spec is not None
    types = [b.type for b in spec.blocks]
    assert "line" in types  # válido
    assert "bar" not in types  # descartado


@pytest.mark.asyncio
async def test_invalid_json_twice_returns_none():
    """Dos respuestas malformadas seguidas → generador devuelve None."""
    from ai_engine.dashboard_spec_generator import DashboardSpecGenerator

    llm = MockBackend(default_response="esto no es JSON")
    gen = DashboardSpecGenerator(llm=llm)
    spec = await gen.generate(
        question="cualquier cosa",
        intent="search",
        dataset_name="x",
        columns=["a"],
        rows=[{"a": 1}],
    )
    assert spec is None


@pytest.mark.asyncio
async def test_empty_rows_returns_none():
    """Rows vacíos → devuelve None sin llamar al LLM."""
    from ai_engine.dashboard_spec_generator import DashboardSpecGenerator

    llm = MockBackend()
    gen = DashboardSpecGenerator(llm=llm)
    spec = await gen.generate(
        question="x",
        intent="search",
        dataset_name="x",
        columns=["a"],
        rows=[],
    )
    assert spec is None
    assert llm.calls == []  # NO debe llamar al LLM si no hay datos


@pytest.mark.asyncio
async def test_temperature_zero_is_default():
    """El generador llama al LLM con temperature=0 por defecto (determinismo)."""
    from ai_engine.dashboard_spec_generator import DashboardSpecGenerator

    llm = MockBackend()
    llm.add_response(
        prompt_contains="",
        response=json.dumps(
            {
                "version": "1",
                "title": "x",
                "layout": "stack",
                "blocks": [{"type": "table", "title": "t", "columns": ["a"]}],
            }
        ),
    )

    captured: dict = {}
    original_generate = llm.generate

    async def spy(prompt, max_tokens=500, **kwargs):
        captured.update(kwargs)
        return await original_generate(prompt, max_tokens=max_tokens, **kwargs)

    llm.generate = spy  # type: ignore[assignment]
    gen = DashboardSpecGenerator(llm=llm)
    await gen.generate(
        question="x",
        intent="search",
        dataset_name="x",
        columns=["a"],
        rows=[{"a": 1}, {"a": 2}],
    )
    assert captured.get("temperature") == 0


# ============================================================
# C. Validación Pydantic
# ============================================================


def test_dashboard_spec_with_zero_blocks_is_invalid():
    """Pydantic rechaza specs con 0 blocks (min_length=1)."""
    from pydantic import ValidationError

    from api.models.dashboard import DashboardSpec

    with pytest.raises(ValidationError):
        DashboardSpec(version="1", title="X", layout="grid", blocks=[])


def test_dashboard_spec_with_unknown_block_type_is_invalid():
    """Block.type fuera del enum debe fallar."""
    from pydantic import ValidationError

    from api.models.dashboard import DashboardSpec

    with pytest.raises(ValidationError):
        DashboardSpec.model_validate(
            {
                "version": "1",
                "title": "X",
                "layout": "grid",
                "blocks": [{"type": "nonexistent", "title": "Y"}],
            }
        )


def test_dashboard_spec_caps_blocks_at_six():
    """Máximo 6 blocks (PLAN_DASHBOARD §3 y §7.1)."""
    from pydantic import ValidationError

    from api.models.dashboard import DashboardSpec

    base = {
        "version": "1",
        "title": "X",
        "layout": "grid",
        "blocks": [
            {"type": "table", "title": str(i), "columns": ["a"]} for i in range(7)
        ],
    }
    with pytest.raises(ValidationError):
        DashboardSpec.model_validate(base)
