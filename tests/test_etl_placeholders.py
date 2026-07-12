"""Guardas anti-plantilla del ETL (metadata Mustache sin diligenciar).

Regla (2026-07-12): un título {{name}} descarta la fila completa; cualquier
otro campo con plantilla ({{source}}, {{description}}, ...) se trata como
ausente sin perder el dataset.
"""

from __future__ import annotations

import pytest

pytest.importorskip("psycopg")

from scripts.etl_refresh_catalog import _is_placeholder, _scrub_placeholder  # noqa: E402


def test_is_placeholder():
    assert _is_placeholder("{{name}}")
    assert _is_placeholder("  {{source}} ")
    assert not _is_placeholder("Víctimas Masacres (MA)")
    assert not _is_placeholder("")


def test_scrub_placeholder_limpia_solo_plantillas():
    assert _scrub_placeholder("{{source}}") is None
    assert _scrub_placeholder("{{description}}") is None
    assert _scrub_placeholder("Centro Nacional de Memoria Histórica") == \
        "Centro Nacional de Memoria Histórica"
    assert _scrub_placeholder(None) is None
    assert _scrub_placeholder("") == ""
