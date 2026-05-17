"""Tests de aceptación Sprint 4 — DEFINIDOS ANTES DE IMPLEMENTAR.

REGLA INVIOLABLE (MAIN.md §6.6): estos tests NO se modifican una vez commiteados.
Si fallan al implementar, se corrige el CÓDIGO, no los tests.

Sprint 4 deliverable (MAIN.md §10.5): "Streamlit + accesibilidad (sin Power BI)"
Deadline: 2026-06-29.

Scope (16 tests):
- A. Estructura de la app (4): `app/main.py`, páginas chat/explorer/about,
     `agent_client.py`, componentes en `app/components/` (+ `accessibility/`).
- B. AgentClient (3): instancia Analyzer, expone `ask`, no bloquea el event loop.
- C. Componentes (4): chart_renderer detecta tipo, chart_narrator genera alt-text,
     map_renderer hace join DIVIPOLA, speech_input usa Web Speech API.
- D. Accesibilidad (3): contraste tema dark configurado, página chat con toggle a11y
     en sidebar, fallback a input de texto cuando STT no soportado.
- E. Docker (2): `Dockerfile.streamlit` presente y servicio en `docker-compose.yml`.

Notas:
- Los tests UI no levantan un browser real (sería frágil y lento). En su lugar:
  - Verifican que los módulos importan sin error (smoke test).
  - Inspeccionan el AST/estructura del código (que las funciones esperadas existen).
  - Usan `streamlit.testing.v1.AppTest` cuando aplica (corre la app headless).
- Si Streamlit no está instalado todavía (FASE 2 lo agrega), los tests aplican
  `@pytest.mark.skipif` para no romper la suite del MCP server.
- No hay tests de Plotly/Folium "que se vea bonito" — solo que la función produce
  la figura correcta dado un DataFrame de entrada.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = REPO_ROOT / "app"

STREAMLIT_AVAILABLE = importlib.util.find_spec("streamlit") is not None
skip_if_no_streamlit = pytest.mark.skipif(
    not STREAMLIT_AVAILABLE,
    reason="Streamlit no instalado todavía (FASE 2 del Sprint 4 lo agrega)",
)

# ============================================================
# A. Estructura de la app
# ============================================================


def test_app_main_module_exists():
    """`app/main.py` existe como entrypoint Streamlit."""
    assert (APP_DIR / "main.py").is_file(), (
        "Falta app/main.py — entrypoint Streamlit del Sprint 4"
    )


def test_app_pages_exist():
    """Las 3 páginas (chat, explorer, about) existen en `app/pages/`."""
    pages = APP_DIR / "pages"
    assert pages.is_dir(), "Falta app/pages/"
    expected = ["chat.py", "explorer.py", "about.py"]
    found = {p.name for p in pages.glob("*.py")}
    missing = [p for p in expected if p not in found]
    assert not missing, f"Faltan páginas: {missing}. Encontradas: {found}"


def test_agent_client_module_exists():
    """`app/agent_client.py` envuelve `ai_engine.Analyzer`."""
    assert (APP_DIR / "agent_client.py").is_file()


def test_components_directory_has_chart_map_and_accessibility():
    """`app/components/` contiene los renderers y el subfolder `accessibility/`."""
    components = APP_DIR / "components"
    assert components.is_dir(), "Falta app/components/"

    files = {p.name for p in components.glob("*.py")}
    for expected in ["chart_renderer.py", "map_renderer.py"]:
        assert expected in files, f"Falta app/components/{expected}. Encontrados: {files}"

    a11y = components / "accessibility"
    assert a11y.is_dir(), "Falta app/components/accessibility/"
    a11y_files = {p.name for p in a11y.glob("*.py")}
    for expected in [
        "speech_input.py",
        "speech_output.py",
        "chart_narrator.py",
        "a11y_toggle.py",
    ]:
        assert expected in a11y_files, (
            f"Falta app/components/accessibility/{expected}. Encontrados: {a11y_files}"
        )


# ============================================================
# B. AgentClient
# ============================================================


@skip_if_no_streamlit
def test_agent_client_exposes_ask():
    """`AgentClient.ask(question)` es la API pública para preguntar."""
    from app.agent_client import AgentClient

    client = AgentClient()
    assert hasattr(client, "ask")
    assert callable(client.ask)


@skip_if_no_streamlit
def test_agent_client_wraps_analyzer():
    """`AgentClient` mantiene una instancia de `ai_engine.Analyzer` internamente."""
    from ai_engine.analyzer import Analyzer
    from app.agent_client import AgentClient

    client = AgentClient()
    inner = getattr(client, "analyzer", None) or getattr(client, "_analyzer", None)
    assert isinstance(inner, Analyzer), (
        "AgentClient debe envolver ai_engine.Analyzer, no reinventar"
    )


@skip_if_no_streamlit
def test_agent_client_ask_is_awaitable_or_sync_wrapper():
    """`ask()` puede ser async o sync wrapper, pero NUNCA bloquea silenciosamente."""
    import inspect

    from app.agent_client import AgentClient

    client = AgentClient()
    method = client.ask
    if inspect.iscoroutinefunction(method):
        return  # OK
    doc = (method.__doc__ or "").lower()
    assert "asyncio" in doc or "sync" in doc or "wrapper" in doc, (
        "Si `ask` es sync, debe documentar cómo maneja el async del Analyzer"
    )


# ============================================================
# C. Componentes
# ============================================================


@skip_if_no_streamlit
def test_chart_renderer_builds_figure_for_timeseries():
    """`chart_renderer.render` produce una figura Plotly cuando hay columna datetime."""
    import pandas as pd

    from app.components.chart_renderer import render_chart

    df = pd.DataFrame(
        {
            "fecha": pd.to_datetime(["2026-01-01", "2026-02-01", "2026-03-01"]),
            "valor": [10, 15, 12],
        }
    )
    fig = render_chart(df)
    assert fig is not None
    assert hasattr(fig, "data") and len(fig.data) >= 1


@skip_if_no_streamlit
def test_chart_narrator_generates_alt_text():
    """`chart_narrator.narrate` produce alt-text descriptivo para lectores de pantalla."""
    import pandas as pd

    from app.components.accessibility.chart_narrator import narrate_chart

    df = pd.DataFrame(
        {
            "categoria": ["A", "B", "C"],
            "valor": [10, 20, 30],
        }
    )
    alt = narrate_chart(df)
    assert isinstance(alt, str)
    assert len(alt) >= 20, (
        f"Alt-text demasiado corto ({len(alt)} chars): {alt!r}. "
        "Debe describir el gráfico para lectores de pantalla."
    )


@skip_if_no_streamlit
def test_map_renderer_handles_cod_dpto_column():
    """`map_renderer.render` acepta DataFrames con `cod_dpto` y produce un Folium Map."""
    import pandas as pd

    from app.components.map_renderer import render_map

    df = pd.DataFrame(
        {
            "cod_dpto": ["05", "11", "76"],
            "valor": [100, 200, 150],
        }
    )
    m = render_map(df)
    assert m is not None
    assert hasattr(m, "_repr_html_"), "Esperaba un Folium Map (tiene _repr_html_)"


@skip_if_no_streamlit
def test_speech_input_uses_web_speech_api():
    """`speech_input` embebe Web Speech API (SpeechRecognition)."""
    from app.components.accessibility.speech_input import render_speech_input

    html = render_speech_input()
    assert isinstance(html, str)
    assert "webkitSpeechRecognition" in html or "SpeechRecognition" in html, (
        "speech_input debe usar Web Speech API"
    )


# ============================================================
# D. Accesibilidad y configuración
# ============================================================


def test_streamlit_config_uses_dark_theme():
    """`.streamlit/config.toml` configura tema dark (alto contraste accesible)."""
    config_path = REPO_ROOT / ".streamlit" / "config.toml"
    assert config_path.is_file(), "Falta .streamlit/config.toml"
    content = config_path.read_text(encoding="utf-8")
    assert "[theme]" in content
    assert 'base = "dark"' in content or 'base="dark"' in content


def test_chat_page_uses_a11y_toggle_in_sidebar():
    """La página de chat incorpora el toggle de accesibilidad del sidebar."""
    chat_page = APP_DIR / "pages" / "chat.py"
    src = chat_page.read_text(encoding="utf-8")
    # Smoke check: importa el toggle global a11y
    assert "a11y_toggle" in src, (
        "La página de chat debe importar/usar app.components.accessibility.a11y_toggle"
    )


def test_speech_input_has_text_fallback():
    """`speech_input` documenta o implementa fallback a input de texto."""
    voice_module = APP_DIR / "components" / "accessibility" / "speech_input.py"
    src = voice_module.read_text(encoding="utf-8")
    assert any(token in src.lower() for token in ["fallback", "st.chat_input", "text_input"]), (
        "speech_input debe ofrecer fallback de texto cuando STT no es soportado por el navegador"
    )


# ============================================================
# E. Docker
# ============================================================


def test_dockerfile_streamlit_exists():
    """`Dockerfile.streamlit` existe para construir la imagen de la UI."""
    assert (REPO_ROOT / "Dockerfile.streamlit").is_file(), (
        "Falta Dockerfile.streamlit (Sprint 4 FASE 6)"
    )


def test_docker_compose_has_streamlit_service():
    """`docker-compose.yml` declara el servicio `streamlit` desde `Dockerfile.streamlit`."""
    compose = REPO_ROOT / "docker-compose.yml"
    assert compose.is_file()
    content = compose.read_text(encoding="utf-8")
    assert "streamlit:" in content, "Falta servicio `streamlit` en docker-compose.yml"
    assert "Dockerfile.streamlit" in content, (
        "El servicio streamlit debe construirse desde Dockerfile.streamlit"
    )
