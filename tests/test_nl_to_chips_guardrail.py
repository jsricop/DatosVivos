"""Tests del guardrail post-LLM en ai_engine/nl_to_chips.

No testeamos el LLM (necesita mock). Sí testeamos el post-procesamiento:
validación contra `available`, rechazo de territorio/entidad cuyo label
no aparece en el query.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

from ai_engine import nl_to_chips


class FakeBackend:
    """Backend de prueba: devuelve un JSON predefinido."""

    def __init__(self, response_obj):
        self._response = json.dumps(response_obj) if isinstance(response_obj, dict) else response_obj

    async def generate(self, prompt, max_tokens=200, model=None, **kwargs):
        return self._response


def _patch_backend(monkeypatch_obj):
    """Patcha get_backend y model_for_task del módulo."""
    nl_to_chips.get_backend = lambda: monkeypatch_obj
    nl_to_chips.model_for_task = lambda task: "test-model"


AVAILABLE = {
    "tema": ["Educación", "Salud y Protección Social", "Vivienda, Ciudad y Territorio"],
    "territorio": [
        {"value": "nacional", "label": "Nacional"},
        {"value": "11", "label": "Bogotá D.C."},
        {"value": "08", "label": "Atlántico"},
        {"value": "76", "label": "Valle del Cauca"},
    ],
    "entidad": [
        {"value": "100", "label": "DANE"},
        {"value": "200", "label": "Ministerio de Salud"},
    ],
}


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_query_vacia_devuelve_todos_null():
    _patch_backend(FakeBackend({"tema": "Educación", "tipo": "Cuántos"}))
    result = _run(nl_to_chips.map_nl_to_chips("", AVAILABLE))
    assert all(v is None for v in result.values())


def test_acepta_chips_validos_cuando_estan_en_query():
    _patch_backend(FakeBackend({
        "tema": "Educación", "tipo": "Cuántos",
        "territorio": "11", "entidad": None, "refinador": "colegios"
    }))
    result = _run(nl_to_chips.map_nl_to_chips(
        "Cuántos colegios públicos hay en Bogotá", AVAILABLE
    ))
    assert result["tema"] == "Educación"
    assert result["tipo"] == "Cuántos"
    assert result["territorio"] == "11"  # "Bogotá" está en el query
    assert result["refinador"] == "colegios"


def test_rechaza_territorio_que_no_aparece_en_query():
    """El bug original: LLM eligió 08 (Atlántico) para 'Mapa por departamento'.
    El guardrail debe filtrarlo porque 'Atlántico' no está en el query.
    """
    _patch_backend(FakeBackend({
        "tema": None, "tipo": "Mapa", "territorio": "08",
        "entidad": None, "refinador": None,
    }))
    result = _run(nl_to_chips.map_nl_to_chips(
        "Mapa de homicidios por departamento", AVAILABLE
    ))
    assert result["tipo"] == "Mapa"
    assert result["territorio"] is None  # filtrado


def test_rechaza_tema_no_en_available():
    _patch_backend(FakeBackend({
        "tema": "Inventado", "tipo": "Cuántos",
        "territorio": None, "entidad": None, "refinador": None,
    }))
    result = _run(nl_to_chips.map_nl_to_chips("Cuántos x", AVAILABLE))
    assert result["tema"] is None


def test_rechaza_tipo_invalido():
    _patch_backend(FakeBackend({
        "tema": None, "tipo": "Inventado",
        "territorio": None, "entidad": None, "refinador": None,
    }))
    result = _run(nl_to_chips.map_nl_to_chips("test", AVAILABLE))
    assert result["tipo"] is None


def test_acepta_entidad_si_label_aparece():
    _patch_backend(FakeBackend({
        "tema": None, "tipo": "Cuántos",
        "territorio": None, "entidad": "100", "refinador": None,
    }))
    result = _run(nl_to_chips.map_nl_to_chips("Datos del DANE", AVAILABLE))
    assert result["entidad"] == "100"


def test_rechaza_entidad_que_no_aparece_en_query():
    _patch_backend(FakeBackend({
        "tema": None, "tipo": "Cuántos",
        "territorio": None, "entidad": "200", "refinador": None,
    }))
    result = _run(nl_to_chips.map_nl_to_chips("Pregunta genérica", AVAILABLE))
    assert result["entidad"] is None  # "Ministerio de Salud" no aparece


def test_acepta_nacional_si_query_dice_nacional():
    _patch_backend(FakeBackend({
        "tema": None, "tipo": "Tendencia",
        "territorio": "nacional", "entidad": None, "refinador": None,
    }))
    result = _run(nl_to_chips.map_nl_to_chips(
        "Tendencia nacional del PIB", AVAILABLE
    ))
    assert result["territorio"] == "nacional"


def test_json_invalido_devuelve_todos_null():
    _patch_backend(FakeBackend("no es json"))
    result = _run(nl_to_chips.map_nl_to_chips("test", AVAILABLE))
    assert all(v is None for v in result.values())
