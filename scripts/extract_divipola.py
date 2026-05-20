"""Extrae el catálogo DIVIPOLA completo desde datos.gov.co y genera
`ai_engine/geo_resolver_data.py` con la lista canónica de municipios.

Mismo patrón que `scripts/extract_topic_keywords.py`: el script es
reproducible, lo corre quien necesite refrescar el snapshot, y commitea
el archivo generado para que el resolver no dependa de red en runtime.

Dataset fuente: `gdxc-w37w` (DANE — DIVIPOLA municipios de Colombia).
1.122 municipios al 2026-05-20.

Uso:
    python -m scripts.extract_divipola
"""

from __future__ import annotations

import json
import sys
import time
import unicodedata
from pathlib import Path

import httpx

DATASET_ID = "gdxc-w37w"
DOMAIN = "www.datos.gov.co"
ENDPOINT = f"https://{DOMAIN}/resource/{DATASET_ID}.json"
PAGE_SIZE = 1000
OUTPUT = Path(__file__).resolve().parent.parent / "ai_engine" / "geo_resolver_data.py"


def _strip_tildes(text: str) -> str:
    """lowercase + sin tildes — para normalización canónica."""
    text = text.lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def _title_case_es(name: str) -> str:
    """Title case respetando preposiciones/artículos en español.

    Ejemplos:
      'SAN ANDRES DE TUMACO' → 'San Andrés de Tumaco'
      'EL DONCELLO'          → 'El Doncello'
      'LA TEBAIDA'           → 'La Tebaida'
    """
    lower_words = {"de", "del", "la", "las", "los", "y", "en"}
    parts = name.split()
    out = []
    for i, w in enumerate(parts):
        w_lower = w.lower()
        if i > 0 and w_lower in lower_words:
            out.append(w_lower)
        else:
            out.append(w.title())
    return " ".join(out)


def fetch_all() -> list[dict]:
    """Descarga todas las filas paginando."""
    headers = {"User-Agent": "DatosVivos/0.1 extract_divipola"}
    all_rows: list[dict] = []
    offset = 0
    while True:
        params = {"$limit": PAGE_SIZE, "$offset": offset}
        resp = httpx.get(ENDPOINT, params=params, headers=headers, timeout=60.0)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break
        all_rows.extend(rows)
        print(f"  fetched {len(rows)} rows (offset={offset}), total={len(all_rows)}")
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(0.2)  # cortesía con Socrata
    return all_rows


def build_municipios(rows: list[dict]) -> list[tuple[str, str, str]]:
    """Devuelve lista de tuplas (nom_mpio_canonical, cod_mpio, cod_dpto).

    Dedupe por cod_mpio (el dataset puede tener duplicados con tipo distinto).
    Excluye filas sin cod_mpio o sin nom_mpio.
    """
    seen_codes: dict[str, tuple[str, str, str]] = {}
    for r in rows:
        mcode = (r.get("cod_mpio") or "").strip()
        name = (r.get("nom_mpio") or "").strip()
        dcode = (r.get("cod_dpto") or "").strip()
        if not mcode or not name or not dcode:
            continue
        if mcode in seen_codes:
            continue
        seen_codes[mcode] = (_title_case_es(name), mcode, dcode)
    # ordenar por código para diff estable
    return sorted(seen_codes.values(), key=lambda x: x[1])


def render_module(municipios: list[tuple[str, str, str]]) -> str:
    """Genera el contenido del módulo Python."""
    lines = [
        '"""Catálogo DIVIPOLA de municipios colombianos.',
        "",
        "Generado por `scripts/extract_divipola.py` desde el dataset oficial",
        f"`{DATASET_ID}` (DANE) de datos.gov.co.",
        "",
        f"Total: {len(municipios)} municipios.",
        "",
        "NO EDITAR A MANO — regenerar con:",
        "    python -m scripts.extract_divipola",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "# (nom_mpio canonical, cod_mpio 5 dígitos, cod_dpto 2 dígitos)",
        "MUNICIPIOS_DIVIPOLA: tuple[tuple[str, str, str], ...] = (",
    ]
    for name, mcode, dcode in municipios:
        # comilla simple si nombre no tiene comilla simple, else doble
        if "'" in name:
            lines.append(f'    ("{name}", "{mcode}", "{dcode}"),')
        else:
            lines.append(f"    ('{name}', '{mcode}', '{dcode}'),")
    lines.append(")")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    print(f"==> Descargando DIVIPOLA desde {ENDPOINT}")
    rows = fetch_all()
    print(f"==> Total filas recibidas: {len(rows)}")
    municipios = build_municipios(rows)
    print(f"==> Tras dedupe: {len(municipios)} municipios")
    content = render_module(municipios)
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"==> Escrito {OUTPUT} ({OUTPUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
