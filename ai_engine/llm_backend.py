"""Abstracción de backend LLM intercambiable: Ollama, OpenAI, Anthropic, Mock.

La selección del backend se hace vía `LLM_BACKEND` env var (MAIN.md ADR-001).
Todos exponen `async generate(prompt, **kwargs) -> str` para que el resto del
motor de IA sea agnóstico del proveedor.

MockBackend permite tests deterministas sin red ni LLM real. Útil tanto para
CI (sin Ollama corriendo) como para validar la orquestación del analyzer sin
las latencias/no-determinismo del LLM.
"""

from __future__ import annotations

import logging
import os
from typing import Protocol

import httpx

log = logging.getLogger(__name__)

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:3b"


class LLMBackend(Protocol):
    """Contrato común a todos los backends LLM."""

    async def generate(self, prompt: str, max_tokens: int = 500, **kwargs) -> str: ...


class MockBackend:
    """Backend determinista. Devuelve respuestas pre-grabadas o un default.

    Uso:
        mock = MockBackend(default_response="N/A")
        mock.add_response(prompt_contains="Antioquia", response="125")
        await mock.generate("¿municipios de Antioquia?")  # → "125"
    """

    # Spec demo: se devuelve cuando el prompt es el del DashboardSpecGenerator.
    # Útil para verificar end-to-end el journey SSE sin Ollama corriendo.
    # No interfiere con tests unitarios que llaman `add_response` antes.
    _DASHBOARD_DEMO_SPEC: str = (
        '{"version":"1","title":"Vista de los datos","subtitle":"Resumen automático",'
        '"layout":"grid","blocks":['
        '{"type":"table","title":"Primeras filas","columns":["__placeholder__"],"max_rows":15}'
        "]}"
    )

    def __init__(self, default_response: str = "MOCK_RESPONSE") -> None:
        self.default_response = default_response
        self._responses: list[tuple[str, str]] = []
        self.calls: list[str] = []  # historial de prompts para introspección en tests

    def add_response(self, *, prompt_contains: str, response: str) -> None:
        """Registra una respuesta que se dispara si `prompt_contains in prompt`."""
        self._responses.append((prompt_contains, response))

    async def generate(self, prompt: str, max_tokens: int = 500, **kwargs) -> str:
        self.calls.append(prompt)
        for key, value in self._responses:
            if key.lower() in prompt.lower():
                return value
        # Heurística de comodidad opt-in (env `DASHBOARD_DEMO_FALLBACK=1`):
        # si el prompt es el del DashboardSpecGenerator y no hubo match
        # pre-grabado, devolver un spec demo con las primeras columnas del
        # prompt. Permite verificar el journey SSE → DashboardRenderer sin
        # Ollama. NUNCA activo durante pytest (los tests son congelados).
        if (
            os.getenv("DASHBOARD_DEMO_FALLBACK") == "1"
            and "diseñador de dashboards" in prompt.lower()
        ):
            return self._build_demo_spec(prompt)
        return self.default_response

    @classmethod
    def _build_demo_spec(cls, prompt: str) -> str:
        """Detecta las primeras columnas del prompt y construye un spec demo."""
        # Las columnas en el prompt aparecen como `  - <name>` (PLAN_DASHBOARD prompt).
        cols: list[str] = []
        for line in prompt.splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") and len(cols) < 8:
                # Tomar solo el nombre antes de cualquier paréntesis o coma.
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

    No requiere Ollama corriendo para instanciar (`__init__` es liviano).
    Sólo el `generate()` o `health_check()` hace la llamada real.
    """

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,  # 60s era ajustado bajo carga concurrente (CPU/Metal contention)
    ) -> None:
        self.host = (host or os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        self.timeout = timeout

    async def health_check(self) -> bool:
        """True si el daemon responde en `/api/tags`."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.host}/api/tags")
                return r.status_code == 200
        except httpx.RequestError:
            return False

    async def generate(self, prompt: str, max_tokens: int = 500, **kwargs) -> str:
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        # Permitir override de opciones desde el caller (temperature, top_p, etc.)
        if "temperature" in kwargs:
            payload["options"]["temperature"] = float(kwargs["temperature"])

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(f"{self.host}/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
            return data.get("response", "").strip()


class AnthropicBackend:
    """Placeholder para Anthropic API (LLM_BACKEND=anthropic).

    Implementación completa pendiente — para Sprint 3 sólo cubrimos
    Ollama (local) y Mock (tests). Documentado en MAIN.md ADR-001 que
    el backend es intercambiable; este placeholder mantiene la
    consistencia de la factory.
    """

    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        self.model = model
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

    async def generate(self, prompt: str, max_tokens: int = 500, **kwargs) -> str:
        raise NotImplementedError(
            "AnthropicBackend pendiente. Para Sprint 3 usar LLM_BACKEND=ollama o mock."
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
