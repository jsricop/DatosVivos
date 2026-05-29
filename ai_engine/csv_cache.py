"""Cache disk-backed de CSVs federados (Reto F.4 optimización).

Cada query federado hoy descarga el CSV remoto vía DuckDB httpfs — primera
vez 3-13s, siguientes lo mismo. Con cache en disco:
  - Primera query: descarga + escribe a `/app/data/csv_cache/<sha1>.csv`.
  - Siguientes: lee del disco, query <1s.

Invalidación:
  - TTL por archivo (default 24h, alineado con el cron diario del ETL).
  - Bajo demanda: borrar `csv_cache/<sha1>.csv` invalida solo ese archivo.

Tamaño máximo por archivo: 200 MB. Si el CSV es más grande, no se cachea
(la descarga vuelve cada vez, pero al menos no llenamos el disco).
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

# Directorio configurable; default coincide con el volumen `/app/data`
# del contenedor api (montado contra `~/DatosVivos/data` en el host).
CACHE_DIR = Path(os.environ.get("CSV_CACHE_DIR", "/app/data/csv_cache"))
DEFAULT_TTL_SECONDS = 86_400  # 24h
MAX_FILE_BYTES = 200 * 1024 * 1024  # 200 MB

_USER_AGENT = "DatosVivos/F.4-cache (+https://github.com/jsricop/DatosVivos)"


def _key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def cache_path(url: str) -> Path:
    """Path donde vive (o viviría) el archivo en cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{_key(url)}.csv"


def _is_fresh(path: Path, ttl: int) -> bool:
    if not path.exists():
        return False
    age = time.time() - path.stat().st_mtime
    return age < ttl


def get_or_download(url: str, ttl: int = DEFAULT_TTL_SECONDS) -> str:
    """Devuelve un path local al CSV. Si no existe en cache o expiró, lo
    descarga (con cap por tamaño). Si la descarga falla, propaga la
    excepción para que el caller la maneje.

    Para archivos > MAX_FILE_BYTES: no cachea — devuelve la URL original
    para que DuckDB la lea via httpfs (más lento pero no explota disco).
    """
    if not url:
        raise ValueError("URL vacía")
    path = cache_path(url)
    if _is_fresh(path, ttl):
        return str(path)

    req = urllib.request.Request(
        url, headers={"User-Agent": _USER_AGENT, "Accept": "*/*"}
    )
    tmp = path.with_suffix(".tmp")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            length = resp.headers.get("Content-Length")
            if length and int(length) > MAX_FILE_BYTES:
                log.info(
                    "csv_cache: %s excede %d bytes, sirvo via URL directa",
                    url, MAX_FILE_BYTES,
                )
                return url
            # Streaming download con cap por tamaño efectivo.
            written = 0
            with open(tmp, "wb") as out:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > MAX_FILE_BYTES:
                        out.close()
                        tmp.unlink(missing_ok=True)
                        log.info(
                            "csv_cache: %s pasó %d bytes durante descarga, "
                            "sirvo via URL directa",
                            url, MAX_FILE_BYTES,
                        )
                        return url
                    out.write(chunk)
        # Move atómica.
        tmp.replace(path)
    except Exception:
        # En cualquier error, limpia temp y propaga.
        tmp.unlink(missing_ok=True)
        raise
    return str(path)


def invalidate(url: str) -> bool:
    """Borra el archivo en cache si existe. True si lo había."""
    path = cache_path(url)
    if path.exists():
        path.unlink()
        return True
    return False
