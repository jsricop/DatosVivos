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

import asyncio
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
        Yieldeamos `response` de cada chunk.

        **Triple safety net** (ADR-016 bug fix 2026-05-22):
        Ollama puede no emitir `{"done": true}` correctamente Y dejar el TCP
        abierto sin enviar más bytes — el loop queda colgado para siempre
        si solo confiamos en `done:true`. Tres mecanismos de cierre:

        1. `chunk.get("done")` → cierre natural (cuando Ollama lo emite bien).
        2. Contador `chunks_yielded >= safety_limit` (max_tokens × 1.2)
           → cierre cuando emitió suficientes tokens.
        3. `asyncio.wait_for` por cada línea con `idle_timeout` → cierre
           cuando Ollama deja de enviar bytes (último token sin EOS).

        Si el LLM falla mid-stream, el caller decide qué hacer con lo recibido.
        """
        payload = self._build_payload(prompt, max_tokens, model, stream=True, kwargs=kwargs)
        safety_limit = max(int(max_tokens * 1.2), max_tokens + 10)
        # Tiempo máximo entre dos tokens consecutivos antes de considerar
        # que Ollama terminó (sin haber emitido done:true). 8s es generoso
        # para CPU-only — un token típicamente llega en <500ms.
        idle_timeout = 8.0
        chunks_yielded = 0
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST", f"{self.host}/api/generate", json=payload
            ) as r:
                r.raise_for_status()
                line_iter = r.aiter_lines()
                while True:
                    try:
                        line = await asyncio.wait_for(
                            line_iter.__anext__(), timeout=idle_timeout
                        )
                    except StopAsyncIteration:
                        # Stream terminó naturalmente.
                        break
                    except asyncio.TimeoutError:
                        # Ollama lleva idle_timeout sin enviar línea nueva
                        # — asumimos que terminó (caso num_predict sin EOS).
                        log.info(
                            "Ollama stream idle por %.1fs sin chunk nuevo; "
                            "cerrando (chunks=%d).",
                            idle_timeout,
                            chunks_yielded,
                        )
                        break
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    text = chunk.get("response", "")
                    if text:
                        yield text
                        chunks_yielded += 1
                    if chunk.get("done"):
                        break
                    if chunks_yielded >= safety_limit:
                        log.warning(
                            "Ollama stream alcanzó %d chunks sin done:true "
                            "(safety limit=%d). Cerrando conexión.",
                            chunks_yielded,
                            safety_limit,
                        )
                        break


class AnthropicBackend:
    """Cliente Anthropic Messages API — opt-in con `LLM_BACKEND=anthropic`.

    Diseño:
    - Misma interfaz que `OllamaBackend` (`generate`, `generate_stream`).
    - `model` por llamada override default — compatible con `model_for_task()`.
    - System prompt + user prompt: el `prompt` que llega del Analyzer se
      pasa como user message; el system prompt es vacío por simplicidad
      (la instrucción de cifras/whitelist va en el user message).
    - Streaming: usa `AsyncAnthropic.messages.stream(...)` que emite tokens
      conforme llegan. Bajo latencia (TTFB ~300ms con Haiku).

    Requisitos:
    - `pip install anthropic` (en requirements.api.txt).
    - Env var `ANTHROPIC_API_KEY` seteada.

    Activación (post-validación de Ollama):
        # En .env de la VM:
        LLM_BACKEND=anthropic
        ANTHROPIC_API_KEY=sk-ant-xxxx
        ANTHROPIC_MODEL_FAST=claude-haiku-4-5-20251001
        ANTHROPIC_MODEL_NARRATIVE=claude-haiku-4-5-20251001
        # docker compose restart api
    """

    DEFAULT_MODEL = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.model = model or os.getenv("ANTHROPIC_MODEL", self.DEFAULT_MODEL)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.timeout = timeout
        # Cliente lazy — no romper si SDK no instalado al import.
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError as exc:
                raise RuntimeError(
                    "AnthropicBackend requiere `pip install anthropic`. "
                    "Ya está en requirements.api.txt."
                ) from exc
            if not self.api_key:
                raise RuntimeError(
                    "AnthropicBackend requiere ANTHROPIC_API_KEY env var."
                )
            self._client = AsyncAnthropic(api_key=self.api_key, timeout=self.timeout)
        return self._client

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        *,
        model: str | None = None,
        **kwargs,
    ) -> str:
        """Llamada no-streaming. Equivalente a Ollama `stream=False`."""
        client = self._get_client()
        used_model = model or self.model
        message_kwargs = {
            "model": used_model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if "temperature" in kwargs:
            message_kwargs["temperature"] = float(kwargs["temperature"])
        resp = await client.messages.create(**message_kwargs)
        # `resp.content` es lista de bloques; concatenamos los de tipo text.
        chunks: list[str] = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                chunks.append(getattr(block, "text", ""))
        return "".join(chunks).strip()

    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 500,
        *,
        model: str | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream tokens via `AsyncAnthropic.messages.stream`.

        Yieldea `text` por cada `MessageStreamEvent` de tipo `content_block_delta`
        con `delta.type == "text_delta"`. El context manager `async with`
        cierra la conexión correctamente al terminar.
        """
        client = self._get_client()
        used_model = model or self.model
        stream_kwargs = {
            "model": used_model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if "temperature" in kwargs:
            stream_kwargs["temperature"] = float(kwargs["temperature"])
        async with client.messages.stream(**stream_kwargs) as stream:
            async for text in stream.text_stream:
                if text:
                    yield text


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


_ANTHROPIC_TASK_TO_ENV_VAR: dict[Task, str] = {
    "rerank": "ANTHROPIC_MODEL_FAST",
    "soql": "ANTHROPIC_MODEL_FAST",
    "dashboard": "ANTHROPIC_MODEL_FAST",
    "reformulate": "ANTHROPIC_MODEL_FAST",
    "narrative": "ANTHROPIC_MODEL_NARRATIVE",
}
_DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"


def model_for_task(task: Task) -> str:
    """Resuelve el modelo a usar para un task específico.

    Cuando `LLM_BACKEND=anthropic`:
      Lee `ANTHROPIC_MODEL_FAST` o `ANTHROPIC_MODEL_NARRATIVE`. Si no, default Haiku.

    Cuando `LLM_BACKEND=ollama` (default):
      Lee `OLLAMA_MODEL_FAST` o `OLLAMA_MODEL_NARRATIVE`. Si no, cae a `OLLAMA_MODEL`
      legacy. Si tampoco, defaults Qwen.
    """
    backend = os.getenv("LLM_BACKEND", "ollama").lower()
    if backend == "anthropic":
        env_var = _ANTHROPIC_TASK_TO_ENV_VAR.get(task, "ANTHROPIC_MODEL_FAST")
        value = os.getenv(env_var) or os.getenv("ANTHROPIC_MODEL")
        return value or _DEFAULT_ANTHROPIC_MODEL

    # Default: ollama.
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
