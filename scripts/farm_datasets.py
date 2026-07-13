#!/usr/bin/env python3
"""Farmeo: bodega local de datasets en Parquet con regla diaria de cola.

Descarga los datasets más valiosos del catálogo (prioridad determinista
"valor por GB" — sin API de LLM) a `/app/data/lake/{dataset_id}.parquet`,
dentro de un presupuesto de disco. El manifest (`dataset_snapshots`, migración
027) es el checkpoint: el script es REANUDABLE — si muere (VPN, reinicio),
re-lanzar continúa donde iba.

Modos:
  --bootstrap   carga inicial hasta llenar el presupuesto (esta noche, en tmux)
  --daily       regla de cola (la corre el ETL nocturno vía run_daily()):
                (1) re-descarga los descargados cuya fuente cambió,
                (2) re-puntúa, (3) entra-uno-sale-uno con histéresis 20 %.
  --dry-run     lista qué haría sin tocar disco ni manifest.

Prioridad (SQL, determinista):
  valor = 3·LN(1+consultas_90d) + LN(1+view_count) + LN(1+download_count)
        + 0.5·frescura(decay 2 años)
  score = valor / GREATEST(bytes_estimados, 1 MB)

Guardas: cap 1.5 GB de CSV por dataset · presupuesto global (bytes reales del
manifest) · timeout 120 s por descarga · un fallo marca `failed` y sigue ·
advisory lock de Postgres (una sola instancia farmea a la vez).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_engine.duckdb_executor import resolve_data_url  # noqa: E402

log = logging.getLogger("farm_datasets")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

LAKE_DIR = Path(os.environ.get("LAKE_DIR", "/app/data/lake"))
SOCRATA_CSV = "https://www.datos.gov.co/api/views/{id}/rows.csv?accessType=DOWNLOAD"
PER_DATASET_CAP = int(float(os.environ.get("FARM_DATASET_CAP_GB", "1.5")) * 1024**3)
# Tope de PARED por dataset: los gigantes con row_count desactualizado
# (p. ej. SECOP II) estiran el stream por media hora antes de tocar el cap
# de bytes. A ~0.8 MB/s medidos, 10 min ≈ 500 MB — suficiente para todo lo
# que cabe razonablemente en el presupuesto.
WALL_SECONDS = int(os.environ.get("FARM_WALL_SECONDS", "600"))
DOWNLOAD_TIMEOUT = 120
CHUNK = 1024 * 256
ADVISORY_LOCK_KEY = 0x5FA127  # una sola instancia de farmeo a la vez

# valor = uso real (señal reina) + engagement + frescura; score = valor/GB estimado.
_CANDIDATES_SQL = """
    SELECT d.dataset_id,
           d.name,
           d.source_type,
           d.data_url,
           d.rows_updated_at,
           (
             3.0 * LN(1 + COALESCE(u.consultas_90d, 0))
             + LN(1 + COALESCE(d.view_count, 0))
             + LN(1 + COALESCE(d.download_count, 0))
             + 0.5 * GREATEST(0, 1 - LEAST(1,
                 EXTRACT(EPOCH FROM (NOW() - d.rows_updated_at)) / (730.0 * 86400)))
           ) AS valor,
           COALESCE(c.n_cols, 12) AS n_cols,
           CASE WHEN d.source_type = 'socrata'
                THEN GREATEST(d.row_count, 1) * COALESCE(c.n_cols, 12) * 15
                ELSE 5 * 1024 * 1024
           END AS bytes_est
    FROM datasets d
    LEFT JOIN LATERAL (
        SELECT count(*) AS consultas_90d FROM dataset_usage du
        WHERE du.dataset_id = d.dataset_id
          AND du.created_at > NOW() - INTERVAL '90 days'
    ) u ON TRUE
    LEFT JOIN LATERAL (
        SELECT count(*) AS n_cols FROM dataset_columns_curated cc
        WHERE cc.dataset_id = d.dataset_id
    ) c ON TRUE
    WHERE (d.quality_flag IS NULL OR d.quality_flag = 'ok')
      AND (
            (d.source_type = 'socrata' AND d.row_count > 0)
         OR (d.source_type = 'federated' AND d.federated_status = 'ok'
             AND d.data_url IS NOT NULL AND d.data_url != ''
             -- Solo TABULARES: el catálogo ya sabe el formato. 76 candidatos
             -- con data_url PDF/XLSX/etc. gastaban resolución y descarga para
             -- fallar (2026-07-12). Los no-tabulares y solo-metadatos no
             -- tienen filas que farmear.
             AND lower(COALESCE(d.data_format, '')) = 'csv')
      )
"""


def _connect():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL no configurada")
    return psycopg.connect(url, row_factory=dict_row)


def _score_candidates(conn) -> list[dict]:
    """Todos los candidatos con score = valor/GB, ordenados desc."""
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT *,
                   valor / GREATEST(bytes_est, 1024 * 1024) * 1e9 AS score
            FROM ({_CANDIDATES_SQL}) t
            ORDER BY score DESC
        """)
        return cur.fetchall()


def _manifest(conn) -> dict[str, dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM dataset_snapshots")
        return {r["dataset_id"]: r for r in cur.fetchall()}


def _upsert(conn, dataset_id: str, **fields) -> None:
    cols = ["dataset_id"] + list(fields)
    sets = ", ".join(f"{k} = EXCLUDED.{k}" for k in fields)
    with conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO dataset_snapshots ({', '.join(cols)}) "
            f"VALUES ({', '.join(['%s'] * len(cols))}) "
            f"ON CONFLICT (dataset_id) DO UPDATE SET {sets}",
            [dataset_id] + list(fields.values()),
        )
    conn.commit()


def _used_bytes(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COALESCE(SUM(bytes), 0) AS b FROM dataset_snapshots "
            "WHERE status = 'downloaded'"
        )
        return int(cur.fetchone()["b"])


def _stream_download(url: str, dest: Path) -> int:
    """Descarga con cap y move atómico (patrón csv_cache). → bytes."""
    req = urllib.request.Request(url, headers={"User-Agent": "DatosVivos-farm/1.0"})
    tmp = dest.with_suffix(".tmp")
    total = 0
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp, \
                open(tmp, "wb") as fh:
            while True:
                chunk = resp.read(CHUNK)
                if not chunk:
                    break
                total += len(chunk)
                if total > PER_DATASET_CAP:
                    raise ValueError(f"supera el cap por dataset ({PER_DATASET_CAP} B)")
                if time.monotonic() - t0 > WALL_SECONDS:
                    raise ValueError(
                        f"supera el tope de tiempo por dataset ({WALL_SECONDS}s)"
                    )
                fh.write(chunk)
        tmp.rename(dest)
        return total
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _csv_to_parquet(csv_path: Path, parquet_path: Path) -> int:
    """CSV → Parquet ZSTD con DuckDB (fallback de encodings). → filas."""
    last_err: Exception | None = None
    for enc in (None, "latin-1", "utf-16"):
        try:
            con = duckdb.connect(":memory:")
            read = (
                f"read_csv_auto('{csv_path}')" if enc is None
                else f"read_csv('{csv_path}', auto_detect=true, encoding='{enc}')"
            )
            con.execute(
                f"COPY (SELECT * FROM {read}) TO '{parquet_path}' "
                f"(FORMAT PARQUET, COMPRESSION ZSTD)"
            )
            rows = con.execute(
                f"SELECT count(*) FROM read_parquet('{parquet_path}')"
            ).fetchone()[0]
            con.close()
            return int(rows)
        except Exception as e:  # noqa: BLE001 — probar siguiente encoding
            last_err = e
            Path(parquet_path).unlink(missing_ok=True)
    raise last_err  # type: ignore[misc]


def _api_headers() -> dict:
    h = {"User-Agent": "DatosVivos-farm/1.0"}
    token = os.environ.get("SOCRATA_APP_TOKEN")
    if token:
        h["X-App-Token"] = token
    return h


def _json_get(url: str, timeout: int = 10, attempts: int = 2):
    """GET JSON con reintento: Socrata devuelve 429 intermitentes cuando el
    farmeo encadena count(1) sin App Token — un backoff corto los absorbe
    (fue la causa de que 17 gigantes socrata pasaran el pre-chequeo el
    2026-07-11: el None silencioso los dejaba seguir a descarga)."""
    import json
    last: Exception | None = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers=_api_headers())
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except Exception as e:  # noqa: BLE001
            last = e
            if i + 1 < attempts:
                time.sleep(2.0 * (i + 1))
    raise last  # type: ignore[misc]


def _live_size_estimate(dataset_id: str, n_cols_catalog: int) -> int | None:
    """Estimación de bytes con datos VIVOS de Socrata. None si no se puede.

    1 llamada (count). Si el dataset es grande (>500k filas) y el ancho del
    catálogo puede estar corto (SECOP no está curado → default 12 cols cuando
    tiene ~70), una 2ª llamada trae las columnas reales de la metadata.
    """
    try:
        rows = _json_get(
            f"https://www.datos.gov.co/resource/{dataset_id}.json"
            f"?%24select=count(1)"
        )
        n = int(list(rows[0].values())[0]) if rows else None
        if n is None:
            return None
        cols = n_cols_catalog
        if n > 500_000:
            try:
                meta = _json_get(
                    f"https://www.datos.gov.co/api/views/{dataset_id}.json"
                )
                cols = max(cols, len(meta.get("columns") or []))
            except Exception:  # noqa: BLE001 — sin metadata, ancho del catálogo
                pass
        return n * max(cols, 1) * 15
    except Exception:  # noqa: BLE001 — sin conteo, la descarga acotada decide
        return None


def _farm_one(conn, cand: dict) -> bool:
    """Descarga un candidato. → True si quedó downloaded."""
    ds = cand["dataset_id"]
    LAKE_DIR.mkdir(parents=True, exist_ok=True)
    csv_tmp = LAKE_DIR / f"{ds}.csv"
    parquet = LAKE_DIR / f"{ds}.parquet"
    try:
        if cand["source_type"] == "socrata":
            # Pre-chequeo: el row_count del catálogo puede estar viejo (caso
            # SECOP II: parecía diminuto y era gigante). El tamaño VIVO cuesta
            # 1-2 llamadas (~2-4 s) y evita gastar 10 min de stream en algo
            # que no cabe.
            est = _live_size_estimate(ds, int(cand.get("n_cols") or 12))
            if est is not None and est > PER_DATASET_CAP:
                _upsert(conn, ds, status="too_big",
                        error=f"tamaño vivo ≈ {est/1024**3:.1f} GB > cap; "
                              f"saltado sin descargar",
                        priority_score=cand["score"],
                        last_scored_at=datetime.now(timezone.utc))
                return False
            url = SOCRATA_CSV.format(id=ds)
        else:
            url = resolve_data_url(cand["data_url"])
            # Pre-chequeo federado: HEAD Content-Length (muchos servidores lo
            # dan). 3 federados llegaron al cap por streaming el 2026-07-11.
            try:
                head = urllib.request.Request(url, method="HEAD",
                                              headers=_api_headers())
                with urllib.request.urlopen(head, timeout=10) as resp:
                    clen = int(resp.headers.get("Content-Length") or 0)
                if clen > PER_DATASET_CAP:
                    _upsert(conn, ds, status="too_big",
                            error=f"Content-Length {clen/1024**3:.1f} GB > cap; "
                                  f"saltado sin descargar",
                            priority_score=cand["score"],
                            last_scored_at=datetime.now(timezone.utc))
                    return False
            except Exception:  # noqa: BLE001 — sin HEAD, el stream acotado decide
                pass
        _stream_download(url, csv_tmp)
        rows = _csv_to_parquet(csv_tmp, parquet)
        bytes_real = parquet.stat().st_size
        _upsert(
            conn, ds,
            status="downloaded", bytes=bytes_real, rows=rows,
            parquet_path=str(parquet), source_kind=cand["source_type"],
            source_updated_at=cand["rows_updated_at"],
            downloaded_at=datetime.now(timezone.utc),
            priority_score=cand["score"], error=None,
        )
        return True
    except ValueError as e:
        # cap por dataset (incluye UnicodeDecodeError, subclase de ValueError:
        # encodings imposibles quedan como too_big = skip permanente, correcto
        # porque reintentar es fútil)
        _upsert(conn, ds, status="too_big", error=str(e)[:400],
                priority_score=cand["score"],
                last_scored_at=datetime.now(timezone.utc))
        return False
    except Exception as e:  # noqa: BLE001 — un fallo nunca tumba la corrida
        _upsert(conn, ds, status="failed", error=str(e)[:400],
                priority_score=cand["score"],
                last_scored_at=datetime.now(timezone.utc))
        return False
    finally:
        csv_tmp.unlink(missing_ok=True)


def _evict(conn, snap: dict) -> None:
    if snap.get("parquet_path"):
        Path(snap["parquet_path"]).unlink(missing_ok=True)
    _upsert(conn, snap["dataset_id"], status="evicted", bytes=None,
            parquet_path=None)


def bootstrap(conn, budget: int, dry: bool) -> None:
    cands = _score_candidates(conn)
    man = _manifest(conn)
    used = _used_bytes(conn)
    log.info("bootstrap: %d candidatos, presupuesto %.1f GB, usado %.2f GB",
             len(cands), budget / 1024**3, used / 1024**3)

    def _fallo_permanente(prev: dict, cand: dict) -> bool:
        """403/404/encoding del origen NO se curan reintentando: cada
        relanzamiento del bootstrap quemaba ~1 h re-fallando 883 entradas
        ("0 ok · N fail", 2026-07-13). Los transitorios (timeout, 5xx, 429)
        sí se reintentan; y si la FUENTE cambió desde el fallo, se
        reintenta también (el publicador pudo arreglar el dataset)."""
        err = (prev.get("error") or "").lower()
        permanente = ("403" in err or "404" in err
                      or "encoded" in err or "unicode" in err
                      or "decode" in err)
        fuente_cambio = prev.get("source_updated_at") is not None and \
            prev["source_updated_at"] != cand["rows_updated_at"]
        return permanente and not fuente_cambio
    ok = skip = fail = 0
    for cand in cands:
        if used >= budget:
            log.info("presupuesto lleno (%.2f GB) — fin", used / 1024**3)
            break
        prev = man.get(cand["dataset_id"])
        if prev and prev["status"] == "downloaded" and \
                prev["source_updated_at"] == cand["rows_updated_at"]:
            skip += 1
            continue
        if prev and prev["status"] in ("too_big",):
            skip += 1
            continue
        if prev and prev["status"] == "failed" and _fallo_permanente(prev, cand):
            skip += 1
            continue
        if dry:
            log.info("[dry] bajaría %s (score %.2f, est %.1f MB) %s",
                     cand["dataset_id"], cand["score"],
                     cand["bytes_est"] / 1024**2, cand["name"][:50])
            ok += 1
            if ok >= 30:
                break
            continue
        if _farm_one(conn, cand):
            ok += 1
            used = _used_bytes(conn)
        else:
            fail += 1
        if (ok + fail) % 25 == 0:
            log.info("progreso: %d ok · %d fail · %d skip · %.2f/%.0f GB",
                     ok, fail, skip, used / 1024**3, budget / 1024**3)
    log.info("bootstrap fin: %d ok · %d fail · %d skip · %.2f GB usados",
             ok, fail, skip, used / 1024**3)


def daily(conn, budget: int, max_swaps: int, max_minutes: int, dry: bool) -> None:
    t0 = time.monotonic()
    cands = {c["dataset_id"]: c for c in _score_candidates(conn)}
    man = _manifest(conn)

    # 1) refrescar descargados cuya fuente cambió
    stale = [
        cands[ds] for ds, s in man.items()
        if s["status"] == "downloaded" and ds in cands
        and s["source_updated_at"] != cands[ds]["rows_updated_at"]
    ]
    log.info("daily: %d descargados con fuente actualizada", len(stale))
    for cand in stale:
        if time.monotonic() - t0 > max_minutes * 60:
            log.info("tope de tiempo — fin de refresco")
            break
        if dry:
            log.info("[dry] refrescaría %s", cand["dataset_id"])
        else:
            _farm_one(conn, cand)

    # 2+3) cola entra-uno-sale-uno con histéresis 20 %
    swaps = 0
    while swaps < max_swaps and time.monotonic() - t0 < max_minutes * 60:
        man = _manifest(conn)
        down = [m for m in man.values() if m["status"] == "downloaded"
                and m["dataset_id"] in cands]
        if not down:
            break
        worst = min(down, key=lambda m: cands[m["dataset_id"]]["score"])
        worst_score = cands[worst["dataset_id"]]["score"]
        pool = [c for ds, c in cands.items()
                if man.get(ds) is None or man[ds]["status"] == "evicted"]
        if not pool:
            break
        best = max(pool, key=lambda c: c["score"])
        if best["score"] <= worst_score * 1.2:
            log.info("cola estable: mejor fuera (%.2f) ≤ 1.2× peor dentro (%.2f)",
                     best["score"], worst_score)
            break
        if dry:
            log.info("[dry] swap: sale %s (%.2f) ← entra %s (%.2f)",
                     worst["dataset_id"], worst_score,
                     best["dataset_id"], best["score"])
            swaps += 1
            continue
        used = _used_bytes(conn)
        if used >= budget:
            _evict(conn, worst)
        if _farm_one(conn, best):
            swaps += 1
        else:
            # no entró: no evictar más por este candidato
            break
    log.info("daily fin: %d swaps", swaps)


def run_daily(budget_gb: float = 12.0, max_swaps: int = 15,
              max_minutes: int = 40) -> None:
    """Punto de entrada para el gancho del ETL. Nunca lanza excepción."""
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_try_advisory_lock(%s) AS ok",
                            [ADVISORY_LOCK_KEY])
                if not cur.fetchone()["ok"]:
                    log.info("otra instancia farmea — salto")
                    return
            daily(conn, int(budget_gb * 1024**3), max_swaps, max_minutes, dry=False)
    except Exception:  # noqa: BLE001
        log.exception("farmeo diario falló (el ETL continúa)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--bootstrap", action="store_true")
    mode.add_argument("--daily", action="store_true")
    ap.add_argument("--budget-gb", type=float, default=12.0)
    ap.add_argument("--max-swaps", type=int, default=15)
    ap.add_argument("--max-minutes", type=int, default=40)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s) AS ok", [ADVISORY_LOCK_KEY])
            if not cur.fetchone()["ok"]:
                log.error("otra instancia de farmeo está corriendo — abortando")
                return 1
        budget = int(args.budget_gb * 1024**3)
        if args.bootstrap:
            bootstrap(conn, budget, args.dry_run)
        else:
            daily(conn, budget, args.max_swaps, args.max_minutes, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
