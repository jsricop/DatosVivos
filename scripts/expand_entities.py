#!/usr/bin/env python3
"""Expande `entities` desde el catálogo real (D.2).

Hoy `entities` tiene 11 semillas (MinTIC, ANI, MinSalud, etc.). El catálogo
tiene 1.354 `entity_raw` distintas. Este script:

1. SELECT DISTINCT entity_raw FROM datasets.
2. Normaliza cada uno: extrae name canónico (sin sufijo geo), abbrev (si
   está entre guiones o paréntesis), infiere kind.
3. UPSERT en `entities`. Las 11 semillas se mantienen, las nuevas se agregan.
4. UPDATE datasets.entity_id apuntando al entity_id correcto.

Idempotente: re-corrigible. Las 11 semillas tienen UNIQUE(domain_email);
nuevas se insertan con domain_email NULL (no son entidades de auth).

Uso:
    DATABASE_URL=... python scripts/expand_entities.py [--dry-run] [--limit N]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import unicodedata
from collections import Counter

import psycopg
from psycopg.rows import dict_row


# Sufijos geo a stripear del entity_raw (lista NO exhaustiva — las más
# frecuentes que detectamos en el catálogo: 32 dptos + "Bogotá D.C." +
# variantes). Strip por re.sub al final del string.
_GEO_SUFFIX_PATTERN = re.compile(
    r",\s*(?:"
    r"Bogot[áa]\s+D\.?C\.?"
    r"|Amazonas|Antioquia|Arauca|Atl[áa]ntico|Bol[íi]var|Boyac[áa]|Caldas"
    r"|Caquet[áa]|Casanare|Cauca|Cesar|Choc[óo]|C[óo]rdoba|Cundinamarca"
    r"|Guain[íi]a|Guaviare|Huila|La\s+Guajira|Magdalena|Meta|Nari[ñn]o"
    r"|Norte\s+de\s+Santander|Putumayo|Quind[íi]o|Risaralda|San\s+Andr[ée]s"
    r"|Santander|Sucre|Tolima|Valle\s+del\s+Cauca|Vaup[ée]s|Vichada"
    r")\s*$",
    re.IGNORECASE,
)

# Acrónimo entre guiones: "Foo Bar - FOOB, ..." → "FOOB"
# O entre paréntesis: "Foo Bar (FOOB)" → "FOOB"
# Acepta tanto mayúsculas puras (DANE, INS, ANI) como camelCase típico de
# ministerios colombianos (MinSalud, MinTIC, SuperFinanciera, SuperSalud).
_ABBREV_TOKEN = r"(?:Min[A-Z][a-zA-Z]+|Super[A-Z][a-zA-Z]+|[A-ZÁÉÍÓÚÑ]{2,18})"
_ABBREV_DASH = re.compile(rf"\s-\s+({_ABBREV_TOKEN})(?:[,\s]|$)")
_ABBREV_PAREN = re.compile(rf"\(({_ABBREV_TOKEN})\)")

# Patrones para inferir kind
_KIND_TERRITORIAL = re.compile(
    r"^(alcald[íi]a|gobernaci[óo]n|asamblea|concejo|personer[íi]a)\b",
    re.IGNORECASE,
)
_KIND_NACIONAL_TOKENS = (
    "ministerio",
    "departamento administrativo",
    "departamento nacional",
    "agencia nacional",
    "agencia de",
    "instituto nacional",
    "instituto colombiano",
    "unidad nacional",
    "unidad administrativa",
    "comisi[óo]n nacional",
    "comisi[óo]n de regulaci[óo]n",
    "consejo nacional",
    "presidencia",
    "vicepresidencia",
    "registradur[íi]a",
    "procuradur[íi]a",
    "contralor[íi]a general",
    "fiscal[íi]a",
    "defensor[íi]a",
    "rama judicial",
    "congreso",
    "senado",
    "c[áa]mara de representantes",
    "corte ",
    "superintendencia",
    "escuela superior",
    "centro de memoria",
    "fondo nacional",
    "fondo de garant[íi]as",
    "banco agrario",
    "banco de la rep[úu]blica",
    "polic[íi]a nacional",
)
_KIND_NACIONAL_RE = re.compile(
    r"\b(?:" + "|".join(_KIND_NACIONAL_TOKENS) + r")\b",
    re.IGNORECASE,
)


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def normalize_entity_raw(raw: str) -> dict:
    """Convierte entity_raw a {name, abbrev, kind}.

    Reglas:
    - Strip sufijo geográfico al final (", Bogotá D.C." o ", <Dpto>").
    - Extrae abbrev de patrones "- ABBR" o "(ABBR)" si están.
    - Infiere kind por keywords del name normalizado.
    """
    raw = (raw or "").strip()
    # 1) Strip sufijo geo
    cleaned = _GEO_SUFFIX_PATTERN.sub("", raw).strip()
    # 2) Extraer abbrev (preferimos guion sobre paréntesis)
    abbrev = None
    m = _ABBREV_DASH.search(cleaned)
    if m:
        abbrev = m.group(1).strip()
        # Sacar el "- ABBR" del name canónico
        cleaned = _ABBREV_DASH.sub("", cleaned, count=1).strip().rstrip(",").rstrip("-").strip()
    else:
        m = _ABBREV_PAREN.search(cleaned)
        if m:
            abbrev = m.group(1).strip()
            cleaned = _ABBREV_PAREN.sub("", cleaned).strip().rstrip("(").rstrip(",").strip()
    # 3) Inferir kind
    if _KIND_TERRITORIAL.search(cleaned):
        kind = "territorial"
    elif _KIND_NACIONAL_RE.search(cleaned):
        kind = "nacional"
    else:
        kind = "descentralizada"
    return {"name": cleaned, "abbrev": abbrev, "kind": kind, "raw": raw}


# ----------------------------------------------------------------------
# Pipeline
# ----------------------------------------------------------------------


def fetch_distinct_entities(conn) -> list[dict]:
    """Devuelve todas las entity_raw únicas con su count de datasets."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT entity_raw, COUNT(*) AS n FROM datasets "
            "WHERE entity_raw IS NOT NULL AND entity_raw != '' "
            "GROUP BY entity_raw ORDER BY n DESC"
        )
        return cur.fetchall()


def existing_entities(conn) -> dict[tuple[str, str | None], int]:
    """Mapa (name_normalized, abbrev) → entity_id para las que ya existen."""
    out: dict[tuple[str, str | None], int] = {}
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT entity_id, name, abbrev FROM entities")
        for r in cur.fetchall():
            key = (_strip_accents(r["name"]).lower(), r["abbrev"])
            out[key] = r["entity_id"]
    return out


def upsert_entity(conn, normalized: dict, existing_map: dict) -> int:
    """Inserta si no existe, devuelve entity_id."""
    key = (_strip_accents(normalized["name"]).lower(), normalized["abbrev"])
    if key in existing_map:
        return existing_map[key]
    # Si existe por name sin importar abbrev (semillas tienen abbrev pero
    # nuestro normalizado puede haber inferido None), reuse.
    name_key = _strip_accents(normalized["name"]).lower()
    for (n, _abbr), eid in existing_map.items():
        if n == name_key:
            existing_map[key] = eid
            return eid
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO entities (name, abbrev, kind, domain_email) "
            "VALUES (%s, %s, %s, NULL) RETURNING entity_id",
            (normalized["name"], normalized["abbrev"], normalized["kind"]),
        )
        row = cur.fetchone()
        new_id = row[0]
    existing_map[key] = new_id
    return new_id


def link_datasets(conn, mapping: dict[str, int]) -> int:
    """UPDATE datasets.entity_id = mapping[entity_raw] usando un VALUES batch.

    Devuelve el número de filas afectadas.
    """
    if not mapping:
        return 0
    # Construimos un VALUES inline con (raw, eid). UPDATE FROM (VALUES) es
    # más rápido que un UPDATE por entity_raw.
    rows = [(raw, eid) for raw, eid in mapping.items()]
    placeholders = ",".join(["(%s, %s)"] * len(rows))
    flat: list = []
    for raw, eid in rows:
        flat.append(raw)
        flat.append(eid)
    sql = f"""
        UPDATE datasets AS d
        SET entity_id = m.eid
        FROM (VALUES {placeholders}) AS m(raw, eid)
        WHERE d.entity_raw = m.raw
          AND (d.entity_id IS NULL OR d.entity_id != m.eid)
    """
    with conn.cursor() as cur:
        cur.execute(sql, flat)
        return cur.rowcount


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo imprime el plan, no escribe.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Procesar solo las top-N entity_raw.")
    args = parser.parse_args()

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL no definida", file=sys.stderr)
        return 2

    with psycopg.connect(url) as conn:
        raws = fetch_distinct_entities(conn)
        if args.limit:
            raws = raws[: args.limit]
        print(f"Encontradas {len(raws):,} entity_raw únicas.")

        existing = existing_entities(conn)
        print(f"Entities existentes: {len(existing)}")

        # 1) Normalizar todas → mapping entity_raw → entity_id
        mapping: dict[str, int] = {}
        kind_counter: Counter = Counter()
        new_entities = 0

        for r in raws:
            normalized = normalize_entity_raw(r["entity_raw"])
            kind_counter[normalized["kind"]] += 1
            if args.dry_run:
                # Solo simulamos: si no existe en existing, contar como nueva
                key = (_strip_accents(normalized["name"]).lower(), normalized["abbrev"])
                if key not in existing and \
                   _strip_accents(normalized["name"]).lower() not in {n for (n, _a) in existing}:
                    new_entities += 1
                continue
            eid = upsert_entity(conn, normalized, existing)
            mapping[r["entity_raw"]] = eid

        if args.dry_run:
            print(f"DRY-RUN: insertaría {new_entities} entities nuevas.")
            print(f"Distribución kind:")
            for k, n in kind_counter.most_common():
                print(f"  {k:<20} {n}")
            return 0

        conn.commit()
        new_total = len(set(mapping.values())) - len(existing) + len([k for k in existing.keys() if k[0] not in {_strip_accents(r["entity_raw"]).lower() for r in raws}])
        print(f"Entities post-upsert: total ~{len(set(mapping.values()))}, distribución kind:")
        for k, n in kind_counter.most_common():
            print(f"  {k:<20} {n}")

        # 2) Link datasets
        n_updated = link_datasets(conn, mapping)
        conn.commit()
        print(f"datasets.entity_id actualizado: {n_updated:,} filas")

    return 0


if __name__ == "__main__":
    sys.exit(main())
