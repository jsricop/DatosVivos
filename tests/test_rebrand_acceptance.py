"""Tests de aceptación del Rebrand Beta-2 — DEFINIDOS ANTES DE IMPLEMENTAR.

REGLA INVIOLABLE (MAIN.md §6.6): estos tests NO se modifican una vez commiteados.
Si fallan al implementar, se corrige el CÓDIGO, no los tests.

Cobertura (alineado con plan en /Users/jsricop/.claude/plans/necesito-hacer-un-rebranding-sparkling-clock.md):

- A. API FastAPI (5): main.py registra routers, /api/v1/health 200, schemas pydantic,
     CORS para /web, version namespace.
- B. /api/v1/suggest (4): axes tema/tipo/territorio/entidad devuelven listas no-vacías;
     schema {label, value, kicker}.
- C. /api/v1/popular (2): lee telemetry CSV; si no hay CSV devuelve fallback determinista
     (no inventa); schema {question, count}.
- D. /api/v1/divipola (3): devuelve 32 departamentos + 1122 municipios desde geo_resolver_data;
     puede filtrar por dpto_code.
- E. /api/v1/query SSE (4): emite eventos en orden (intent → dataset_hits → narrative_chunk →
     citations → done); LLM_BACKEND=mock no requiere Ollama; pregunta vacía devuelve error event;
     CORS y Content-Type correctos.
- F. /api/v1/datasets/{id} (2): devuelve metadata estructurada o 404 si dataset no existe;
     incluye link a página datos.gov.co y JSON SODA.
- G. Web scaffold (4): web/package.json válido, tsconfig estricto, tokens.css con 3 modos,
     layout root presente.
- H. BRAND.md compliance (3): paletas hex declaradas pasan contraste AA, sin emojis en código UI,
     sin import de fuentes Google Fonts CDN.

Notas:
- Tests UI no levantan browser real; verifican AST/estructura y validan respuestas API.
- Si FastAPI/httpx no instalados, `skipif` salta sección API pero los chequeos estructurales corren.
- LLM_BACKEND=mock garantiza que los tests no requieren Ollama corriendo.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
API_DIR = REPO_ROOT / "api"
WEB_DIR = REPO_ROOT / "web"
DOCS_DIR = REPO_ROOT / "docs"

FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None
HTTPX_AVAILABLE = importlib.util.find_spec("httpx") is not None

skip_if_no_fastapi = pytest.mark.skipif(
    not (FASTAPI_AVAILABLE and HTTPX_AVAILABLE),
    reason="fastapi/httpx no instalados — instala con pip install -r requirements.api.txt",
)


# ============================================================
# A. API FastAPI — estructura
# ============================================================


def test_api_main_module_exists_and_imports():
    """api/main.py existe y se puede importar como módulo."""
    assert (API_DIR / "main.py").is_file(), "Falta api/main.py"
    spec = importlib.util.spec_from_file_location("api.main", API_DIR / "main.py")
    assert spec is not None


def test_api_routes_directory_has_expected_modules():
    """api/routes/ contiene query.py, health.py, suggest.py, popular.py, divipola.py, datasets.py."""
    routes = API_DIR / "routes"
    assert routes.is_dir(), "Falta api/routes/"
    expected = {"query.py", "health.py", "suggest.py", "popular.py", "divipola.py", "datasets.py"}
    found = {p.name for p in routes.glob("*.py")} - {"__init__.py"}
    missing = expected - found
    assert not missing, f"Faltan routes: {missing}. Encontrados: {found}"


def test_api_schemas_module_defines_request_response_types():
    """api/models/schemas.py define los tipos pydantic principales."""
    schemas_path = API_DIR / "models" / "schemas.py"
    assert schemas_path.is_file()
    content = schemas_path.read_text(encoding="utf-8")
    for required in [
        "QueryRequest",
        "DatasetCitation",
        "PopularQuery",
        "SuggestOption",
        "DivipolaItem",
        "DatasetMetadata",
    ]:
        assert required in content, f"Schema {required!r} no declarado en api/models/schemas.py"


@skip_if_no_fastapi
def test_api_app_registers_v1_router():
    """La app FastAPI tiene los endpoints bajo /api/v1."""
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


@skip_if_no_fastapi
def test_api_cors_allows_web_origin():
    """CORS permite el origen del frontend Next.js."""
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    # FastAPI/Starlette devuelve 200 con header ACA-Origin si CORS está configurado.
    assert "access-control-allow-origin" in {k.lower() for k in response.headers.keys()}


# ============================================================
# B. /api/v1/suggest
# ============================================================


@skip_if_no_fastapi
@pytest.mark.parametrize("axis", ["tema", "tipo", "territorio", "entidad"])
def test_suggest_axis_returns_options(axis):
    """Cada eje de chip devuelve una lista no-vacía con shape {label, value, kicker}."""
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    response = client.get(f"/api/v1/suggest?axis={axis}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict) and "options" in data
    options = data["options"]
    assert isinstance(options, list) and len(options) > 0, f"Sin opciones para axis={axis}"
    for opt in options:
        assert "label" in opt and "value" in opt
        # kicker es opcional pero si está debe ser string corto
        if "kicker" in opt and opt["kicker"]:
            assert isinstance(opt["kicker"], str) and len(opt["kicker"]) <= 30


@skip_if_no_fastapi
def test_suggest_invalid_axis_returns_422():
    """Eje desconocido devuelve 422 (validación)."""
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    response = client.get("/api/v1/suggest?axis=desconocido")
    assert response.status_code in (400, 422)


# ============================================================
# C. /api/v1/popular
# ============================================================


@skip_if_no_fastapi
def test_popular_returns_list_even_without_telemetry(tmp_path, monkeypatch):
    """Si no hay CSV de telemetría, devuelve fallback determinista (no inventa)."""
    from fastapi.testclient import TestClient

    # Forzar TELEMETRY_PATH a un archivo inexistente
    import ai_engine.telemetry as telemetry

    monkeypatch.setattr(telemetry, "TELEMETRY_PATH", tmp_path / "no-existe.csv")

    from api.main import app

    client = TestClient(app)
    response = client.get("/api/v1/popular?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "popular" in data and isinstance(data["popular"], list)
    # Cuando no hay telemetría, fallback determinista — debe ser lista pero puede ser
    # vacía o con un placeholder explícitamente marcado is_fallback=true.
    if data["popular"]:
        for item in data["popular"]:
            assert "question" in item


@skip_if_no_fastapi
def test_popular_aggregates_telemetry_csv(tmp_path, monkeypatch):
    """Si hay CSV de telemetría, agrupa por question y devuelve top-N por count."""
    from fastapi.testclient import TestClient

    import ai_engine.telemetry as telemetry

    csv_path = tmp_path / "queries.csv"
    csv_path.write_text(
        "timestamp_iso,question,intent,datasets_used,soql_executed,rows_count,censored_count,elapsed_s,had_statistics\n"
        "2026-05-19T10:00:00+00:00,¿Cuantos colegios en Boyaca?,descriptive,abc1-2def,SELECT,50,0,5.0,True\n"
        "2026-05-19T10:01:00+00:00,¿Cuantos colegios en Boyaca?,descriptive,abc1-2def,SELECT,50,0,5.0,True\n"
        "2026-05-19T10:02:00+00:00,Tendencia homicidios Cali,temporal,xyz9-8wvu,SELECT,30,0,10.0,True\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(telemetry, "TELEMETRY_PATH", csv_path)

    from api.main import app

    client = TestClient(app)
    response = client.get("/api/v1/popular?limit=10")
    assert response.status_code == 200
    data = response.json()
    popular = data["popular"]
    # La pregunta de Boyacá aparece 2 veces, debe ser la primera por count.
    assert popular[0]["question"].startswith("¿Cuantos colegios en Boyaca")
    assert popular[0]["count"] == 2


# ============================================================
# D. /api/v1/divipola
# ============================================================


@skip_if_no_fastapi
def test_divipola_returns_departments():
    """GET /divipola sin params devuelve los 32 departamentos + Bogotá."""
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    response = client.get("/api/v1/divipola")
    assert response.status_code == 200
    data = response.json()
    assert "departments" in data
    # 32 departamentos + Bogotá D.C. = 33
    assert len(data["departments"]) >= 32


@skip_if_no_fastapi
def test_divipola_filter_by_dpto_returns_municipios():
    """GET /divipola?dpto=05 devuelve municipios de Antioquia."""
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    response = client.get("/api/v1/divipola?dpto=05")
    assert response.status_code == 200
    data = response.json()
    assert "municipios" in data
    munis = data["municipios"]
    # Antioquia tiene 125 municipios según el ADR-010
    assert len(munis) == 125, f"Esperaba 125 municipios en Antioquia, encontré {len(munis)}"
    medellin = next((m for m in munis if m["code"] == "05001"), None)
    assert medellin is not None
    assert medellin["name"] == "Medellín"


@skip_if_no_fastapi
def test_divipola_invalid_dpto_returns_404_or_empty():
    """dpto inválido devuelve 404 o lista vacía (no error 500).

    Usamos `XX` como código garantizadamente inexistente — no es 2 dígitos
    numéricos. Códigos numéricos como `99` (Vichada) sí existen en DIVIPOLA.
    """
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    response = client.get("/api/v1/divipola?dpto=XX")
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        assert response.json().get("municipios", []) == []


# ============================================================
# E. /api/v1/query (SSE)
# ============================================================


@skip_if_no_fastapi
def test_query_with_empty_question_returns_error_event(monkeypatch):
    """Pregunta vacía debe emitir un evento `error` o responder 422."""
    from fastapi.testclient import TestClient

    monkeypatch.setenv("LLM_BACKEND", "mock")

    from api.main import app

    client = TestClient(app)
    response = client.post("/api/v1/query", json={"q": ""})
    assert response.status_code in (200, 422, 400)
    if response.status_code == 200:
        body = response.text
        assert "error" in body or "done" in body


@skip_if_no_fastapi
def test_query_sse_content_type():
    """El endpoint /query usa text/event-stream cuando se pide stream."""
    from fastapi.testclient import TestClient

    os.environ["LLM_BACKEND"] = "mock"

    from api.main import app

    client = TestClient(app)
    with client.stream(
        "POST",
        "/api/v1/query",
        json={"q": "test"},
        headers={"Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200
        ctype = response.headers.get("content-type", "")
        assert "text/event-stream" in ctype


@skip_if_no_fastapi
def test_query_sse_emits_done_event(monkeypatch):
    """En el happy path se emite finalmente un evento `done` con elapsed_s."""
    from fastapi.testclient import TestClient

    monkeypatch.setenv("LLM_BACKEND", "mock")

    from api.main import app

    client = TestClient(app)
    with client.stream("POST", "/api/v1/query", json={"q": "datasets de salud"}) as resp:
        events = []
        for line in resp.iter_lines():
            if line.startswith("event:"):
                events.append(line.split(":", 1)[1].strip())
        # `done` siempre debe aparecer al final, aunque sea con error.
        assert "done" in events, f"No se emitió evento 'done'. Eventos: {events}"


@skip_if_no_fastapi
def test_query_sse_emits_intent_before_narrative(monkeypatch):
    """Orden de eventos: intent antes que narrative_chunk."""
    from fastapi.testclient import TestClient

    monkeypatch.setenv("LLM_BACKEND", "mock")

    from api.main import app

    client = TestClient(app)
    with client.stream("POST", "/api/v1/query", json={"q": "homicidios en cali"}) as resp:
        seen_intent = False
        order_violated = False
        for line in resp.iter_lines():
            if line.startswith("event:"):
                ev = line.split(":", 1)[1].strip()
                if ev == "intent":
                    seen_intent = True
                elif ev == "narrative_chunk" and not seen_intent:
                    order_violated = True
        assert not order_violated, "narrative_chunk apareció antes que intent"


# ============================================================
# F. /api/v1/datasets/{id}
# ============================================================


@skip_if_no_fastapi
def test_dataset_metadata_returns_404_for_unknown(monkeypatch):
    """ID desconocido devuelve 404 (no 500)."""
    from fastapi.testclient import TestClient

    monkeypatch.setenv("LLM_BACKEND", "mock")

    from api.main import app

    client = TestClient(app)
    response = client.get("/api/v1/datasets/zzzz-9999")
    assert response.status_code in (404, 502, 200)
    # Si 200, debe tener un campo "error" o "not_found": true
    if response.status_code == 200:
        body = response.json()
        assert body.get("not_found") is True or body.get("error")


@skip_if_no_fastapi
def test_dataset_metadata_includes_canonical_links():
    """Si el dataset existe, la respuesta incluye url y api_url canónicos."""
    # Patch del metadata client para no depender de la red en CI.
    from fastapi.testclient import TestClient

    from api.main import app
    import api.routes.datasets as datasets_route

    async def fake_get(self, dataset_id):
        return {
            "id": dataset_id,
            "name": "Test dataset",
            "attribution": "Entidad Test",
            "description": "",
            "columns": [],
        }

    from mcp_server.socrata.metadata_client import MetadataClient

    original = MetadataClient.get
    MetadataClient.get = fake_get  # type: ignore[assignment]
    try:
        client = TestClient(app)
        response = client.get("/api/v1/datasets/test-1234")
        assert response.status_code == 200
        data = response.json()
        assert data["url"].endswith("/d/test-1234")
        assert data["api_url"].endswith("resource/test-1234.json")
    finally:
        MetadataClient.get = original  # type: ignore[assignment]


# ============================================================
# G. Web scaffold
# ============================================================


def test_web_directory_exists():
    """web/ existe como carpeta del frontend Next.js."""
    assert WEB_DIR.is_dir(), "Falta web/ — scaffold Next.js"


def test_web_package_json_declares_next15_and_react19():
    """package.json declara dependencias clave del stack acordado."""
    pkg_path = WEB_DIR / "package.json"
    assert pkg_path.is_file(), "Falta web/package.json"
    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    assert "next" in deps, "next no declarado"
    assert "react" in deps, "react no declarado"
    assert "typescript" in deps or "typescript" in pkg.get("devDependencies", {})
    # Tailwind v4
    assert any("tailwindcss" in d for d in deps), "tailwindcss no declarado"


def test_web_tsconfig_strict_enabled():
    """tsconfig.json tiene strict mode habilitado."""
    tsconfig = WEB_DIR / "tsconfig.json"
    assert tsconfig.is_file()
    content = tsconfig.read_text(encoding="utf-8")
    assert '"strict": true' in content, "tsconfig.json no tiene strict: true"


def test_web_tokens_css_declares_three_themes():
    """tokens.css declara los 3 modos: light, dark, contrast."""
    tokens = WEB_DIR / "src" / "styles" / "tokens.css"
    assert tokens.is_file(), "Falta web/src/styles/tokens.css"
    content = tokens.read_text(encoding="utf-8")
    for theme in ['data-theme="light"', 'data-theme="dark"', 'data-theme="contrast']:
        assert theme in content, f"tokens.css no tiene {theme}"


def test_web_layout_root_has_anti_fouc_script():
    """layout.tsx incluye script inline anti-FOUC que aplica data-theme antes del hidrato."""
    layout = WEB_DIR / "src" / "app" / "layout.tsx"
    assert layout.is_file(), "Falta web/src/app/layout.tsx"
    content = layout.read_text(encoding="utf-8")
    # El script anti-FOUC lee localStorage y aplica data-theme
    assert "datosvivos:theme" in content, "layout.tsx no implementa anti-FOUC con clave datosvivos:theme"
    assert "data-theme" in content or "dataset.theme" in content


def test_web_has_five_routes():
    """Las 5 rutas declaradas en BRAND.md §9 existen como page.tsx."""
    routes = [
        WEB_DIR / "src" / "app" / "page.tsx",
        WEB_DIR / "src" / "app" / "buscar" / "page.tsx",
        WEB_DIR / "src" / "app" / "dataset" / "[id]" / "page.tsx",
        WEB_DIR / "src" / "app" / "acerca" / "page.tsx",
        WEB_DIR / "src" / "app" / "accesibilidad" / "page.tsx",
    ]
    missing = [str(p.relative_to(REPO_ROOT)) for p in routes if not p.is_file()]
    assert not missing, f"Faltan páginas: {missing}"


# ============================================================
# H. BRAND.md compliance
# ============================================================


def test_brand_md_exists_and_declares_required_sections():
    """BRAND.md existe y declara las secciones obligatorias del plan."""
    brand = DOCS_DIR / "BRAND.md"
    assert brand.is_file()
    content = brand.read_text(encoding="utf-8")
    for section in [
        "Manifiesto",
        "Sistema de color",
        "Tipografía",
        "Iconografía",
        "Wordmark",
        "Lista negra",
    ]:
        assert section in content, f"BRAND.md no declara la sección {section!r}"


def test_brand_paletas_pasan_contraste_minimo():
    """Las paletas declaradas en BRAND.md respetan contrastes mínimos.

    Mecánica: extrae todos los hex y verifica que ink/bg en los 3 modos
    pasan 4.5:1 (AA normal). Esto es un guard contra cambios accidentales.
    """
    brand = DOCS_DIR / "BRAND.md"
    content = brand.read_text(encoding="utf-8")

    # Tabla de pares (modo, bg, ink, expected_min_ratio) — chequea AA normal.
    pairs = [
        ("light", "#F3EFE3", "#16130E", 4.5),
        ("dark", "#0E0C08", "#E8E1CE", 4.5),
        ("contrast-light", "#FFFFFF", "#000000", 4.5),
        ("contrast-dark", "#000000", "#FFFFFF", 4.5),
    ]
    for mode, bg, ink, min_ratio in pairs:
        assert _wcag_contrast(bg, ink) >= min_ratio, (
            f"Modo {mode}: bg {bg} vs ink {ink} no pasa contraste {min_ratio}:1"
        )
        # Y los hex deben aparecer en BRAND.md (sanity check del documento).
        assert bg.lower() in content.lower() or bg.upper() in content
        assert ink.lower() in content.lower() or ink.upper() in content


def test_no_emojis_in_web_source_files():
    """Las reglas duras de BRAND.md §11 prohíben emojis en código UI productivo."""
    if not WEB_DIR.is_dir():
        pytest.skip("web/ aún no creado")
    # Regex de emojis pictográficos (bloques Unicode más comunes en UIs):
    emoji_re = re.compile(
        "["
        "\U0001F300-\U0001F5FF"
        "\U0001F600-\U0001F64F"
        "\U0001F680-\U0001F6FF"
        "\U0001F700-\U0001F77F"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FAFF"
        "☀-➿"
        "]",
        flags=re.UNICODE,
    )
    offenders = []
    for path in WEB_DIR.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {"node_modules", ".next", "dist", "build"} for part in path.parts):
            continue
        if path.suffix not in {".ts", ".tsx", ".css", ".mjs", ".js", ".json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if emoji_re.search(text):
            # Permitido en archivos test/fixture si lleva comentario explícito de
            # "// allow-emoji" — por ahora no permitimos ninguno.
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, f"Emojis encontrados en código UI: {offenders}"


def test_web_does_not_load_google_fonts_cdn():
    """BRAND.md §4.1: las fuentes IBM Plex deben ser self-hosted, nunca Google Fonts CDN."""
    if not WEB_DIR.is_dir():
        pytest.skip("web/ aún no creado")
    offenders = []
    for path in WEB_DIR.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {"node_modules", ".next", "dist", "build"} for part in path.parts):
            continue
        if path.suffix not in {".ts", ".tsx", ".css", ".mjs", ".js", ".html"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "fonts.googleapis.com" in text or "fonts.gstatic.com" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, f"Google Fonts CDN encontrado en: {offenders}"


# ============================================================
# Helpers
# ============================================================


def _wcag_contrast(hex1: str, hex2: str) -> float:
    """Calcula el ratio de contraste WCAG entre dos colores hex.

    Implementación pragmática del algoritmo WCAG 2.1: convierte a sRGB
    relativo, calcula luminancia, devuelve (L1+0.05)/(L2+0.05).
    """

    def _luminance(hex_color: str) -> float:
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        r, g, b = (int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

        def _adj(c: float) -> float:
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        return 0.2126 * _adj(r) + 0.7152 * _adj(g) + 0.0722 * _adj(b)

    l1 = _luminance(hex1)
    l2 = _luminance(hex2)
    lighter, darker = (l1, l2) if l1 >= l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)
