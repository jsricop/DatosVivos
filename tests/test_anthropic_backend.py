"""Tests congelados para AnthropicBackend (LLM_BACKEND=anthropic).

NO contactan la API real — usan mocks. Validan:
- model_for_task respeta backend=anthropic.
- generate() y generate_stream() arman payload correcto.
- Errores claros si SDK no instalado o API key falta.
"""

from __future__ import annotations

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_model_for_task_anthropic_default():
    """Sin env vars, retorna default Haiku."""
    from ai_engine.llm_backend import model_for_task

    with patch.dict(os.environ, {"LLM_BACKEND": "anthropic"}, clear=False):
        # Limpiar overrides
        for k in ("ANTHROPIC_MODEL_FAST", "ANTHROPIC_MODEL_NARRATIVE", "ANTHROPIC_MODEL"):
            os.environ.pop(k, None)
        assert "haiku" in model_for_task("narrative").lower()
        assert "haiku" in model_for_task("soql").lower()


def test_model_for_task_anthropic_env_override():
    """Con env vars custom, las usa."""
    from ai_engine.llm_backend import model_for_task

    env = {
        "LLM_BACKEND": "anthropic",
        "ANTHROPIC_MODEL_FAST": "claude-sonnet-4-6",
        "ANTHROPIC_MODEL_NARRATIVE": "claude-opus-4-7",
    }
    with patch.dict(os.environ, env, clear=False):
        assert model_for_task("rerank") == "claude-sonnet-4-6"
        assert model_for_task("soql") == "claude-sonnet-4-6"
        assert model_for_task("dashboard") == "claude-sonnet-4-6"
        assert model_for_task("narrative") == "claude-opus-4-7"


def test_model_for_task_ollama_unaffected():
    """Con backend=ollama, el routing Anthropic NO se aplica."""
    from ai_engine.llm_backend import model_for_task

    env = {
        "LLM_BACKEND": "ollama",
        "OLLAMA_MODEL_FAST": "qwen2.5-coder:3b",
        "OLLAMA_MODEL_NARRATIVE": "qwen2.5:7b",
    }
    with patch.dict(os.environ, env, clear=False):
        assert model_for_task("rerank") == "qwen2.5-coder:3b"
        assert model_for_task("narrative") == "qwen2.5:7b"


def test_anthropic_backend_requires_api_key():
    """Sin ANTHROPIC_API_KEY, llamar generate debe levantar error claro."""
    from ai_engine.llm_backend import AnthropicBackend

    backend = AnthropicBackend(api_key=None)
    backend.api_key = None  # explícito
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        backend._get_client()


@pytest.mark.asyncio
async def test_anthropic_backend_generate_payload():
    """`generate()` construye payload Messages API correcto."""
    from ai_engine.llm_backend import AnthropicBackend

    fake_client = MagicMock()
    fake_content_block = MagicMock(type="text", text="Antioquia tiene 125 municipios.")
    fake_response = MagicMock(content=[fake_content_block])
    fake_client.messages.create = AsyncMock(return_value=fake_response)

    backend = AnthropicBackend(api_key="sk-test")
    backend._client = fake_client

    result = await backend.generate(
        "Pregunta de prueba", max_tokens=100, model="claude-haiku-4-5", temperature=0.3
    )
    assert result == "Antioquia tiene 125 municipios."
    fake_client.messages.create.assert_awaited_once()
    kwargs = fake_client.messages.create.await_args.kwargs
    assert kwargs["model"] == "claude-haiku-4-5"
    assert kwargs["max_tokens"] == 100
    assert kwargs["temperature"] == 0.3
    assert kwargs["messages"] == [{"role": "user", "content": "Pregunta de prueba"}]


@pytest.mark.asyncio
async def test_anthropic_backend_generate_stream_yields_tokens():
    """`generate_stream()` emite tokens conforme llegan del text_stream."""
    from ai_engine.llm_backend import AnthropicBackend

    # Mock del context manager `async with messages.stream(...) as stream`.
    fake_tokens = ["Ant", "io", "quia", " tiene ", "125", " municipios."]

    class FakeStream:
        text_stream = None  # configurado abajo

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    async def _gen():
        for t in fake_tokens:
            yield t

    fake_stream = FakeStream()
    fake_stream.text_stream = _gen()
    fake_client = MagicMock()
    fake_client.messages.stream = MagicMock(return_value=fake_stream)

    backend = AnthropicBackend(api_key="sk-test")
    backend._client = fake_client

    collected = []
    async for tok in backend.generate_stream("test", max_tokens=50):
        collected.append(tok)
    assert collected == fake_tokens


def test_factory_get_backend_anthropic():
    """`LLM_BACKEND=anthropic` retorna AnthropicBackend."""
    from ai_engine.llm_backend import AnthropicBackend, get_backend

    with patch.dict(os.environ, {"LLM_BACKEND": "anthropic"}, clear=False):
        backend = get_backend()
        assert isinstance(backend, AnthropicBackend)
