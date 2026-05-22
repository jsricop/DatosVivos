"""Abstracción de backend LLM intercambiable: Ollama, OpenAI, Anthropic, Mock.

La selección del backend se hace vía `LLM_BACKEND` env var (MAIN.md ADR-001).
La selección del MODELO por task se hace vía `get_backend_for(task)` (ADR-015) —
tiered: modelo rápido (3B) para rerank/SoQL/dashboard, modelo medio (7B) para
narrative.

Todos exponen `async generate(prompt, **kwargs) -> str` para que el resto del
motor de IA sea agnóstico del proveedor.

MockBackend permite tests deterministas sin red ni LLM real. Útil tanto para
CI (sin Ollama corriendo) como para validar la orquestación del analyzer sin
las latencias/no-determinismo del LLM.
"""

from __future__ import annotations

import json
import logging
import os
from typing import AsyncIterator, Literal, Protocol

import httpx

log = logging.getLogger(__name__)

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:3b"

# Task labels para tiered routing (ADR-015).
Task = Literal["rerank", "soql", "narrative", "dashboard", "reformulate"]


class LLMBackend(Protocol):
    """Contrato común a todos los backends LLM."""

    async def generate(
        self, prompt: str, max_tokens: int = 500, *, model: str | None = None, **kwargs
    ) -> str: ...


class MockBackend:
    """Backend determinista. Devuelve respuestas pre-grabadas o un default.

    Uso:
        mock = MockBackend(default_response="N/A")
        mock.add_response(prompt_contains="Antioquia", response="125")
        await mock.generate("¿municipios de Antioquia?")  # → "125"
    """

    _DASHBOARD_DEMO_SPEC: str = (
        '{"version":"1","title":"Vista de los datos","subtitle":"Resumen automático",'
        '"layout":"grid","blocks":['
        '{"type":"table","title":"Primeras filas","columns":["__placeholder__"],"max_rows":15}'
        "]}"
    )

    def __init__(self, default_response: str = "MOCK_RESPONSE") -> None:
        self.default_response = default_response
        self._responses: list[tuple[str, str]] = []
        self.calls: list[str] = []

    def add_response(self, *, prompt_contains: str, response: str) -> None:
        self._responses.append((prompt_contains, response))

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        *,
        model: str | None = None,
        **kwargs,
    ) -> str:
        self.calls.append(prompt)
        for key, value in self._responses:
            if key.lower() in prompt.lower():
                return value
        if (
            os.getenv("DASHBOARD_DEMO_FALLBACK") == "1"
            and "diseñador de dashboards" in prompt.lower()
        ):
            return self._build_demo_spec(prompt)
        return self.default_response

    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 500,
        *,
        model: str | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Para tests: emite la respuesta completa en un único chunk."""
        text = await self.generate(prompt, max_tokens, model=model, **kwargs)
        yield text

    @classmethod
    def _build_demo_spec(cls, prompt: str) -> str:
        cols: list[str] = []
        for line in prompt.splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") and len(cols) < 8:
                name = stripped[2:].split("(")[0].split(",")[0].strip()
                if name and name not in cols:
                    cols.append(name)
        if not cols:
            return cls._DASHBOARD_DEMO_SPEC
        return (
            '{"version":"1","title":"Vista automática",'
            '"subtitle":"Spec demo (LLM no disponible)",'
            '"layout":"grid","blocks":['
            f'{{"type":"table","title":"Primeras filas","columns":{cols!r},"max_rows":15}}'
            "]}"
        ).replace("'", '"')


class OllamaBackend:
    """Cliente HTTP al daemon local de Ollama (`/api/generate`).

    Soporta override de modelo por llamada vía `model=` kwarg — útil para
    tiered routing (ADR-015): rerank/SoQL/dashboard al modelo rápido (3B),
    narrative al modelo medio (7B).

    `generate()` espera la respuesta completa (`stream=False`).
    `generate_stream()` emite tokens conforme llegan de Ollama (`stream=True`).
    """

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.host = (host or os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        self.timeout = timeout

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.host}/api/tags")
                return r.status_code == 200
        except httpx.RequestError:
            return False

    def _build_payload(
        self,
        prompt: str,
        max_tokens: int,
        model: str | None,
        stream: bool,
        kwargs: dict,
    ) -> dict:
        payload: dict = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {"num_predict": max_tokens},
        }
        if "temperature" in kwargs:
            payload["options"]["temperature"] = float(kwargs["temperature"])
        return payload

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        *,
        model: str | None = None,
        **kwargs,
    ) -> str:
        payload = self._build_payload(prompt, max_tokens, model, stream=False, kwargs=kwargs)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(f"{self.host}/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
            return data.get("response", "").strip()

    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 500,
        *,
        model: str | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream tokens de Ollama conforme se generan.

        Ollama emite NDJSON con `{"response": "<token>", "done": false}` por línea.
        Yieldeamos `response` de cada chunk. Cuando llega `done=true` cerramos.

        Si el LLM falla mid-stream, el caller decide qué hacer con lo recibido.
        """
        payload = self._build_payload(prompt, max_tokens, model, stream=True, kwargs=kwargs)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST", f"{self.host}/api/generate", json=payload
            ) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    text = chunk.get("response", "")
                    if text:
                        yield text
                    if chunk.get("done"):
                        break


class AnthropicBackend:
    """Placeholder para Anthropic API. No implementado en Beta-2."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        self.model = model
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        *,
        model: str | None = None,
        **kwargs,
    ) -> str:
        raise NotImplementedError(
            "AnthropicBackend pendiente. Para Beta-2 usar LLM_BACKEND=ollama o mock."
        )


# ---------------------------------------------------------------
# Tiered model routing (ADR-015)
# ---------------------------------------------------------------

# Default fallback si las env vars no están seteadas. Compatible con deploys
# previos a ADR-015 que solo definían `OLLAMA_MODEL`.
_DEFAULT_FAST_MODEL = "qwen2.5-coder:3b"
_DEFAULT_NARRATIVE_MODEL = "qwen2.5:7b"

_TASK_TO_ENV_VAR: dict[Task, str] = {
    "rerank": "OLLAMA_MODEL_FAST",
    "soql": "OLLAMA_MODEL_FAST",
    "dashboard": "OLLAMA_MODEL_FAST",
    "reformulate": "OLLAMA_MODEL_FAST",
    "narrative": "OLLAMA_MODEL_NARRATIVE",
}


def model_for_task(task: Task) -> str:
    """Resuelve el modelo Ollama a usar para un task específico.

    Lee de env var asociada (OLLAMA_MODEL_FAST u OLLAMA_MODEL_NARRATIVE). Si
    no está seteada, usa el default. Si `OLLAMA_MODEL` (legacy, single-model)
    está seteado y la específica no, usa el legacy para preservar comportamiento.
    """
    env_var = _TASK_TO_ENV_VAR.get(task, "OLLAMA_MODEL_FAST")
    value = os.getenv(env_var)
    if value:
        return value
    legacy = os.getenv("OLLAMA_MODEL")
    if legacy:
        return legacy
    return (
        _DEFAULT_NARRATIVE_MODEL if task == "narrative" else _DEFAULT_FAST_MODEL
    )


def get_backend() -> LLMBackend:
    """Factory: lee `LLM_BACKEND` env var y devuelve la instancia correspondiente."""
    name = os.getenv("LLM_BACKEND", "ollama").lower()
    if name == "ollama":
        return OllamaBackend()
    if name == "mock":
        return MockBackend()
    if name == "anthropic":
        return AnthropicBackend()
    raise ValueError(
        f"LLM_BACKEND inválido: {name!r}. Valores soportados: 'ollama', 'mock', 'anthropic'."
    )
