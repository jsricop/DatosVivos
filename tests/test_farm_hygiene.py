"""Higiene del lake en el farmeo (huérfanos del 2026-07-13).

Tres garantías:
1. `_mark_undownloaded` borra el parquet previo y limpia sus campos en el
   manifest cuando un intento termina en failed/too_big (antes el parquet
   viejo quedaba en disco con `parquet_path` apuntándole).
2. `_csv_to_parquet` escribe vía `.part` + rename: un fallo no deja parquet
   parcial con nombre definitivo.
3. `_sweep_orphans` barre archivos sin dueño (>1 h) y respeta los vivos.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from scripts import farm_datasets as farm


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeConn:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.upserts = []

    def cursor(self):
        return _FakeCursor(self.rows)

    def commit(self):
        pass


def test_mark_undownloaded_borra_parquet_y_limpia_manifest(tmp_path, monkeypatch):
    parquet = tmp_path / "abcd-1234.parquet"
    parquet.write_bytes(b"parquet viejo")
    registrado = {}

    def fake_upsert(conn, dataset_id, **fields):
        registrado["dataset_id"] = dataset_id
        registrado.update(fields)

    monkeypatch.setattr(farm, "_upsert", fake_upsert)
    cand = {"dataset_id": "abcd-1234", "score": 3.5}
    farm._mark_undownloaded(None, cand, parquet, "too_big", "x" * 999)

    assert not parquet.exists()
    assert registrado["dataset_id"] == "abcd-1234"
    assert registrado["status"] == "too_big"
    assert registrado["bytes"] is None
    assert registrado["rows"] is None
    assert registrado["parquet_path"] is None
    assert len(registrado["error"]) == 400  # truncado


def test_csv_to_parquet_atomico_ok(tmp_path):
    csv = tmp_path / "d.csv"
    csv.write_text("a,b\n1,2\n3,4\n")
    parquet = tmp_path / "d.parquet"

    rows = farm._csv_to_parquet(csv, parquet)

    assert rows == 2
    assert parquet.exists()
    assert not (tmp_path / "d.parquet.part").exists()


def test_csv_to_parquet_fallo_no_deja_parcial(tmp_path):
    csv = tmp_path / "no-existe.csv"  # falla en los 3 encodings
    parquet = tmp_path / "d.parquet"

    with pytest.raises(Exception):
        farm._csv_to_parquet(csv, parquet)

    assert not parquet.exists()
    assert not (tmp_path / "d.parquet.part").exists()


def test_sweep_orphans_borra_viejos_y_respeta_vivos(tmp_path, monkeypatch):
    monkeypatch.setattr(farm, "LAKE_DIR", tmp_path)
    vivo = tmp_path / "vivo-0001.parquet"
    vivo.write_bytes(b"ok")
    huerfano = tmp_path / "huer-0001.parquet"
    huerfano.write_bytes(b"muerto")
    tmp_kill = tmp_path / "algo.tmp"
    tmp_kill.write_bytes(b"kill")
    reciente = tmp_path / "reciente.parquet.part"
    reciente.write_bytes(b"en curso")
    hace_2h = time.time() - 7200
    import os
    for f in (vivo, huerfano, tmp_kill):
        os.utime(f, (hace_2h, hace_2h))

    conn = _FakeConn(rows=[{"parquet_path": f"/app/data/lake/{vivo.name}"}])
    farm._sweep_orphans(conn, dry=False)

    assert vivo.exists()  # referenciado por el manifest
    assert reciente.exists()  # < 1 h: puede estar escribiéndose
    assert not huerfano.exists()
    assert not tmp_kill.exists()


def test_sweep_orphans_dry_no_borra(tmp_path, monkeypatch):
    monkeypatch.setattr(farm, "LAKE_DIR", tmp_path)
    huerfano = tmp_path / "huer-0002.parquet"
    huerfano.write_bytes(b"muerto")
    import os
    hace_2h = time.time() - 7200
    os.utime(huerfano, (hace_2h, hace_2h))

    farm._sweep_orphans(_FakeConn(rows=[]), dry=True)

    assert huerfano.exists()
