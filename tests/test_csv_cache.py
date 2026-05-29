"""Tests para ai_engine/csv_cache (Reto F.4 optimización)."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

# Configura CACHE_DIR ANTES de importar el módulo
_TMP = tempfile.mkdtemp(prefix="csv_cache_test_")
os.environ["CSV_CACHE_DIR"] = _TMP

from ai_engine import csv_cache  # noqa: E402


def test_key_es_deterministico_y_diferencia_urls():
    k1 = csv_cache._key("https://a.com/x.csv")
    k2 = csv_cache._key("https://a.com/x.csv")
    k3 = csv_cache._key("https://b.com/x.csv")
    assert k1 == k2
    assert k1 != k3
    assert len(k1) == 40  # sha1 hex


def test_cache_path_crea_dir():
    csv_cache.CACHE_DIR = Path(_TMP)
    p = csv_cache.cache_path("https://test.example/q.csv")
    assert csv_cache.CACHE_DIR.exists()
    assert str(p).endswith(".csv")
    assert p.parent == csv_cache.CACHE_DIR


def test_is_fresh_false_si_no_existe():
    csv_cache.CACHE_DIR = Path(_TMP)
    p = csv_cache.cache_path("https://nope.example/missing.csv")
    if p.exists():
        p.unlink()
    assert csv_cache._is_fresh(p, ttl=3600) is False


def test_is_fresh_respeta_ttl():
    csv_cache.CACHE_DIR = Path(_TMP)
    p = csv_cache.cache_path("https://ttl.example/a.csv")
    p.write_text("col\n1\n", encoding="utf-8")
    # Recién escrito → fresh para cualquier TTL > 0.
    assert csv_cache._is_fresh(p, ttl=3600) is True
    # TTL 0 → no es fresh.
    assert csv_cache._is_fresh(p, ttl=0) is False
    # Modificar mtime al pasado.
    old = time.time() - 7200
    os.utime(p, (old, old))
    assert csv_cache._is_fresh(p, ttl=3600) is False
    assert csv_cache._is_fresh(p, ttl=86400) is True


def test_invalidate_borra_si_existe():
    csv_cache.CACHE_DIR = Path(_TMP)
    p = csv_cache.cache_path("https://kill.example/y.csv")
    p.write_text("data", encoding="utf-8")
    assert p.exists()
    assert csv_cache.invalidate("https://kill.example/y.csv") is True
    assert not p.exists()
    # Idempotente.
    assert csv_cache.invalidate("https://kill.example/y.csv") is False


def test_url_vacia_levanta_value_error():
    try:
        csv_cache.get_or_download("")
    except ValueError:
        return
    assert False, "Esperaba ValueError para URL vacía"
