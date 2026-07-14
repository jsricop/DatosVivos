"""Tests de aceptación — extensión multi-dataset de cross_datasets.

REGLA INVIOLABLE (MAIN.md §6.6): estos tests NO se modifican una vez commiteados.
Si fallan al refactorizar, se corrige el CÓDIGO, no los tests.

Motivación: el `cross_datasets` original solo cruzaba 2 datasets. Esta extensión
permite N=1..5 con verificación explícita de que la join_key existe en cada
paso de la cadena (anti-falsos-positivos). Sprint 3 contrato pairwise queda
absorbido por la nueva firma.

Cobertura (8 tests):
- A. Cardinalidades: N=0 error, N=1 sin merge, N=6 rechazo por seguridad
- B. Pairwise canónico (regression Sprint 3 con nueva API)
- C. N=3 con key común
- D. N=3 con lista de N-1 keys (per-pair)
- E. Key inválida en medio de la cadena (error útil)
- F. Short-circuit: si A⨝B vacío, no descargar C
"""

from __future__ import annotations

import json

import pytest
from mcp.server.fastmcp.exceptions import ToolError

# ============================================================
# Datasets reales que comparten `cod_dpto`:
# - gdxc-w37w: DIVIPOLA municipios          (1.122 filas)
# - emp6-672w: Comunas y Barrios Valledupar (310 filas)
# - t7kp-7a7c: DIVIPOLA departamentos geo.  (~32 filas)
# - vcjz-niiq: DIVIPOLA departamentos (usa `codigo_departamento`, distinta convención)
#
# OJO: estos tests son @live y el origen puede BORRAR datasets — pasó con
# vafm-j2df (DIVIPOLA municipios geoloc.), eliminado por el DANE y
# reemplazado aquí por emp6-672w el 2026-07-12.
# ============================================================

DS_MUNI = "gdxc-w37w"
DS_MUNI_GEO = "emp6-672w"
DS_DEPT_GEO = "t7kp-7a7c"
DS_DEPT_DIFF_NAME = "vcjz-niiq"  # usa `codigo_departamento`, NO `cod_dpto`
JOIN = "cod_dpto"


def _unwrap(result):
    """Aplana el retorno heterogéneo de `mcp.call_tool` in-process."""
    if isinstance(result, tuple):
        _, payload = result
        if isinstance(payload, dict) and "result" in payload:
            return payload["result"]
        return payload
    if hasattr(result, "content"):
        return [json.loads(b.text) for b in result.content if getattr(b, "text", None)]
    return result


# ============================================================
# A. Cardinalidades
# ============================================================


async def test_cross_multi_zero_datasets_raises_useful_error():
    """N=0: error explícito, no caída silenciosa."""
    from mcp_server.server import mcp

    with pytest.raises(ToolError) as exc_info:
        await mcp.call_tool(
            "cross_datasets",
            {"dataset_ids": [], "join_keys": JOIN},
        )
    assert "vac" in str(exc_info.value).lower() or "0" in str(exc_info.value)


@pytest.mark.live
async def test_cross_multi_single_dataset_returns_rows_without_merge():
    """N=1: devuelve las filas del dataset, sin merge. `join_keys` puede ser None."""
    from mcp_server.server import mcp

    result = await mcp.call_tool(
        "cross_datasets",
        {"dataset_ids": [DS_MUNI], "per_dataset_limit": 10},
    )
    rows = _unwrap(result)
    assert isinstance(rows, list) and rows, "N=1 debería devolver filas"
    assert "cod_dpto" in rows[0], "esperaba columnas originales del dataset"
    assert len(rows) <= 10, "per_dataset_limit debería capear"


async def test_cross_multi_rejects_more_than_five_datasets():
    """N>5: error explícito por seguridad (cap definido en Sprint extension)."""
    from mcp_server.server import mcp

    with pytest.raises(ToolError) as exc_info:
        await mcp.call_tool(
            "cross_datasets",
            {
                "dataset_ids": [DS_MUNI] * 6,
                "join_keys": JOIN,
            },
        )
    msg = str(exc_info.value).lower()
    assert "5" in msg or "máximo" in msg or "exced" in msg


# ============================================================
# B. Pairwise canónico (regression con nueva API)
# ============================================================


@pytest.mark.live
async def test_cross_multi_pairwise_with_shared_key():
    """N=2: comportamiento equivalente al Sprint 3 con la nueva firma."""
    from mcp_server.server import mcp

    result = await mcp.call_tool(
        "cross_datasets",
        {
            "dataset_ids": [DS_MUNI, DS_DEPT_GEO],
            "join_keys": JOIN,
        },
    )
    rows = _unwrap(result)
    assert rows, "merge pairwise debería producir filas"
    assert JOIN in rows[0], f"join_key {JOIN} debe estar en cada fila merged"


# ============================================================
# C. N=3 con key común
# ============================================================


@pytest.mark.live
async def test_cross_multi_three_datasets_with_common_key():
    """N=3 todas comparten `cod_dpto`. join_keys puede ser string único."""
    from mcp_server.server import mcp

    result = await mcp.call_tool(
        "cross_datasets",
        {
            "dataset_ids": [DS_MUNI, DS_MUNI_GEO, DS_DEPT_GEO],
            "join_keys": JOIN,  # string → se aplica a todos los pares
        },
    )
    rows = _unwrap(result)
    assert rows, "merge encadenado debería producir filas"
    assert JOIN in rows[0]
    # Cada fila debe traer datos de los 3 datasets (al menos algunas columnas)
    keys = set(rows[0].keys())
    assert len(keys) >= 4, f"esperaba múltiples columnas tras 3-way merge, vi: {keys}"


# ============================================================
# D. join_keys como lista (per-pair)
# ============================================================


@pytest.mark.live
async def test_cross_multi_accepts_list_of_join_keys():
    """N=3 con `join_keys` como lista de N-1 elementos (per-pair)."""
    from mcp_server.server import mcp

    result = await mcp.call_tool(
        "cross_datasets",
        {
            "dataset_ids": [DS_MUNI, DS_MUNI_GEO, DS_DEPT_GEO],
            "join_keys": [JOIN, JOIN],  # 2 keys para 3 datasets (N-1)
        },
    )
    rows = _unwrap(result)
    assert rows
    assert JOIN in rows[0]


# ============================================================
# E. Key inválida en medio de la cadena
# ============================================================


@pytest.mark.live
async def test_cross_multi_invalid_key_in_middle_of_chain_errors():
    """N=3 donde el dataset del medio NO tiene la key. Error útil que identifica
    cuál dataset rompió la cadena."""
    from mcp_server.server import mcp

    # vcjz-niiq usa `codigo_departamento`, NO `cod_dpto`. Romperá la cadena.
    with pytest.raises(ToolError) as exc_info:
        await mcp.call_tool(
            "cross_datasets",
            {
                "dataset_ids": [DS_MUNI, DS_DEPT_DIFF_NAME, DS_DEPT_GEO],
                "join_keys": JOIN,
            },
        )
    msg = str(exc_info.value)
    # El error debe mencionar qué dataset rompió + cuál columna falta
    assert DS_DEPT_DIFF_NAME in msg or "vcjz" in msg, f"no menciona el dataset roto: {msg}"
    assert "cod_dpto" in msg, f"no menciona la columna esperada: {msg}"


# ============================================================
# F. Short-circuit en merge vacío
# ============================================================


@pytest.mark.live
async def test_cross_multi_short_circuits_on_empty_intermediate_merge(monkeypatch):
    """Si A⨝B = [], NO se debe descargar C. Verifica con spy sobre SodaClient."""
    from mcp_server.server import mcp
    from mcp_server.socrata.soda_client import SodaClient

    call_log: list[str] = []

    async def spy_query(self, dataset_id, **kwargs):
        call_log.append(dataset_id)
        # Para forzar A⨝B vacío, devolvemos filas con `cod_dpto` distinto en cada dataset
        if dataset_id == DS_MUNI:
            return [{"cod_dpto": "99", "nom_mpio": "FAKE"}]
        if dataset_id == DS_DEPT_GEO:
            return [{"cod_dpto": "01", "nom_dpto": "OTHER"}]
        # Tercer dataset NO debería llamarse
        return [{"cod_dpto": "99", "extra": "should-not-fetch"}]

    monkeypatch.setattr(SodaClient, "query", spy_query)

    result = await mcp.call_tool(
        "cross_datasets",
        {
            "dataset_ids": [DS_MUNI, DS_DEPT_GEO, DS_MUNI_GEO],
            "join_keys": JOIN,
        },
    )
    rows = _unwrap(result)
    assert rows == [], "esperaba [] cuando el primer merge queda vacío"
    assert DS_MUNI_GEO not in call_log, (
        f"short-circuit falló: se descargó {DS_MUNI_GEO} aunque A⨝B = []. " f"Llamadas: {call_log}"
    )
