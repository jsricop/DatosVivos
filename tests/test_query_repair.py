"""Unit tests para QueryGenerator.repair y el reescritor LIMIT 0 (ADR-022 Fase 3)."""

from __future__ import annotations

import asyncio

from ai_engine.query_generator import QueryGenerator
from ai_engine.soql_verifier import _with_limit_zero, verify_execution


class _FakeBackend:
    def __init__(self, response: str):
        self._response = response
        self.last_prompt = None

    async def generate(self, prompt, max_tokens=300, model=None, **kwargs):
        self.last_prompt = prompt
        return self._response


SCHEMA = {"columns": [{"fieldName": "cod_dpto", "dataTypeName": "text"},
                      {"fieldName": "anio", "dataTypeName": "number"}],
          "sample_rows": []}


def test_repair_devuelve_soql_postprocesado():
    be = _FakeBackend("```sql\nSELECT count(*) AS n WHERE cod_dpto = '15'\n```")
    qg = QueryGenerator(backend=be)
    out = asyncio.run(qg.repair("¿cuántos en Boyacá?", SCHEMA,
                                "SELECT total_x", "La columna total_x no existe; usa count(*)."))
    assert out == "SELECT count(*) AS n WHERE cod_dpto = '15'"
    # El prompt de reparación incluye el SoQL anterior y el error dirigido.
    assert "total_x" in be.last_prompt
    assert "ERROR DEL VERIFICADOR" in be.last_prompt


def test_with_limit_zero_agrega():
    assert _with_limit_zero("SELECT count(*) AS n") == "SELECT count(*) AS n LIMIT 0"


def test_with_limit_zero_reemplaza():
    assert _with_limit_zero("SELECT * LIMIT 100").endswith("LIMIT 0")


def test_verify_execution_ok():
    class _Soda:
        async def query(self, dataset_id, soql_query):
            assert "LIMIT 0" in soql_query  # no trae datos
            return []
    r = asyncio.run(verify_execution("SELECT count(*) AS n", soda_client=_Soda(), dataset_id="x"))
    assert r.ok


def test_verify_execution_captura_error():
    class _Soda:
        async def query(self, dataset_id, soql_query):
            raise RuntimeError("400 Could not parse SoQL: no such column foo")
    r = asyncio.run(verify_execution("SELECT foo", soda_client=_Soda(), dataset_id="x"))
    assert not r.ok and r.layer_failed == "execution"
    assert "no such column" in r.error_message
