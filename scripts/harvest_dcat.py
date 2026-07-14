"""Harvester DCAT JSON-LD (Project Open Data v1.1).

Para portales que NO usan CKAN sino DCAT (Drupal + DKAN + módulo Open Data).
Hoy soporta:
    medellin → www.medata.gov.co/data.json (id prefix: med-)

Uso (dentro del contenedor api):
    DATABASE_URL=... python -m scripts.harvest_dcat --portal medellin
    DATABASE_URL=... python -m scripts.harvest_dcat --portal medellin --dry-run

Idempotente: UPSERT por dataset_id. Reusa el helper _normalize_license_id
de harvest_ckan para mantener vocabulario de license_id consistente.

Cumple los mismos criterios curatorios que harvest_ckan (Hito R):
    license_id, update_frequency, sector, domain_metadata, cobertura_geografica
    (default por portal), jurisdiccion_nivel (default), jurisdiccion_geo_codes.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.request
from datetime import datetime
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from scripts.harvest_ckan import _normalize_license_id

USER_AGENT = "DatosVivos/F.5-dcat-harvester (+https://github.com/jsricop/DatosVivos)"

PORTALS: dict[str, dict[str, Any]] = {
    "medellin": {
        "url": "https://www.medata.gov.co/data.json",
        "host": "www.medata.gov.co",
        "prefix": "med-",
        # Defaults curatorios para Medellín (Hito R criteria)
        "cobertura_geografica": "Municipal",
        "jurisdiccion_nivel": "municipal",
        "jurisdiccion_geo_codes": ["05001"],  # DIVIPOLA Medellín
    },
}

log = logging.getLogger("harvest_dcat")
DATABASE_URL = os.environ.get("DATABASE_URL")


def _build_dataset_id(identifier: str, prefix: str) -> str:
    """`<prefix><suffix>` capado a 20 chars. MEDATA usa `1-020-13-000030`,
    cabe sin truncar."""
    clean = (identifier or "").strip().replace(" ", "")
    candidate = f"{prefix}{clean}"
    return candidate[:20]


def _http_get_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def _iter_datasets(catalog_url: str, limit: int | None) -> Iterator[dict[str, Any]]:
    """DCAT data.json es un catálogo único, no paginado. Carga todo y yield."""
    log.info("GET %s", catalog_url)
    cat = _http_get_json(catalog_url)
    datasets = cat.get("dataset") or []
    log.info("Catálogo DCAT: %d datasets", len(datasets))
    for i, ds in enumerate(datasets):
        yield ds
        if limit and (i + 1) >= limit:
            return


def _parse_date_es(s: str | None):
    """MEDATA usa DD-MM-YYYY (no ISO). También acepta ISO por si acaso."""
    if not s:
        return None
    s = s.strip()
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s[:10] if "T" not in s else s[:19], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _pick_csv_distribution(dists: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """Devuelve la primera distribution con format/mediaType CSV con URL."""
    if not dists:
        return None
    for d in dists:
        fmt = (d.get("format") or "").lower().strip()
        mt = (d.get("mediaType") or "").lower().strip()
        if fmt == "csv" or mt in ("text/csv", "application/csv"):
            url = (d.get("downloadURL") or d.get("accessURL") or "").strip()
            if url:
                return d
    return None


def _normalize_license_url(license_url: str | None) -> str | None:
    """MEDATA expone license como URL Creative Commons. Normaliza al vocab nativo."""
    if not license_url:
        return None
    u = license_url.lower()
    if "by-sa" in u and "/4.0" in u: return "CC_40_BY_SA"
    if "by-nd" in u and "/4.0" in u: return "CC_40_BY_ND"
    if "by/4.0" in u or "/by/4.0" in u: return "CC_40_BY"
    if "zero" in u or "cc0" in u or "publicdomain" in u: return "CC0_10"
    return None


def _normalize_dcat_frequency(periodicity: str | None) -> str | None:
    """DCAT accrualPeriodicity puede ser ISO 8601 (R/P1Y) o texto. Devuelve
    el string crudo; parse_frequency_days SQL ya entiende ambos (mig 011)."""
    if not periodicity:
        return None
    return periodicity.strip()


def _build_row_medellin(
    ds: dict[str, Any], portal_cfg: dict[str, Any]
) -> dict[str, Any] | None:
    """Mapea un dataset DCAT MEDATA a una fila de `datasets`."""
    identifier = ds.get("identifier") or ""
    if not identifier:
        return None
    dataset_id = _build_dataset_id(identifier, portal_cfg["prefix"])

    title = ds.get("title") or ""
    description = ((ds.get("description") or "")[:2000]) or None

    publisher = ds.get("publisher") or {}
    entity_raw = publisher.get("name") or "Alcaldía de Medellín"

    themes = ds.get("theme") or []
    category = themes[0] if themes else None
    # sector = mismo theme — DCAT no separa concepto
    sector = themes[0] if themes else None

    keywords = ds.get("keyword") or []

    modified = _parse_date_es(ds.get("modified"))
    issued = _parse_date_es(ds.get("issued"))

    dist = _pick_csv_distribution(ds.get("distribution"))
    if not dist:
        return None
    data_url = dist.get("downloadURL") or dist.get("accessURL")
    if not data_url:
        return None

    license_raw = ds.get("license") or None
    license_id = _normalize_license_url(license_raw)

    update_frequency = _normalize_dcat_frequency(ds.get("accrualPeriodicity"))

    # domain_metadata: trazabilidad de todo lo no-mapeado
    dm: dict[str, Any] = {}
    contact = ds.get("contactPoint") or {}
    if contact.get("fn"):
        dm["contact_fn"] = contact["fn"]  # ej. "Secretaría de Educación"
    if contact.get("hasEmail"):
        dm["contact_email"] = contact["hasEmail"]
    if ds.get("temporal"):
        dm["temporal"] = ds["temporal"]
    if ds.get("conformsTo"):
        dm["conformsTo"] = ds["conformsTo"]
    if ds.get("accessLevel"):
        dm["accessLevel"] = ds["accessLevel"]
    if keywords:
        dm["keywords"] = keywords
    if themes:
        dm["themes"] = themes

    return {
        "dataset_id": dataset_id,
        "name": title,
        "entity_raw": entity_raw,
        "category": category,
        "description": description,
        "rows_updated_at": modified,
        "data_updated_at": modified,
        "metadata_updated_at": modified,
        "publication_date": issued,
        "created_at_socrata": issued,
        "provenance": "official",
        "license": license_raw,
        "license_id": license_id,
        "update_frequency": update_frequency,
        "sector": sector,
        "domain_metadata": dm if dm else None,
        "source_type": "federated",
        "source_portal": portal_cfg["host"],
        "data_url": data_url,
        "data_format": "csv",
        "federated_status": "ok",
        "socrata_url": f"https://{portal_cfg['host']}/dataset/{identifier}",
        "api_url": None,
        # Curación deducible por portal (mismos criterios mig 020)
        "cobertura_geografica": portal_cfg.get("cobertura_geografica"),
        "jurisdiccion_nivel": portal_cfg.get("jurisdiccion_nivel"),
        "jurisdiccion_geo_codes": Jsonb(portal_cfg["jurisdiccion_geo_codes"])
            if portal_cfg.get("jurisdiccion_geo_codes") else None,
    }


def _resolve_entity_id(cur: psycopg.Cursor, entity_raw: str | None) -> int | None:
    if not entity_raw:
        return None
    cur.execute(
        """
        SELECT entity_id FROM entities
        WHERE lower(trim(name)) = lower(trim(%s))
        ORDER BY length(name) DESC LIMIT 1
        """,
        (entity_raw,),
    )
    row = cur.fetchone()
    return row["entity_id"] if row else None


_UPSERT_SQL = """
INSERT INTO datasets (
    dataset_id, name, entity_id, entity_raw, category, description,
    rows_updated_at, data_updated_at, metadata_updated_at, publication_date,
    created_at_socrata, provenance, license, license_id, update_frequency,
    sector, domain_metadata, source_type, source_portal,
    data_url, data_format, federated_status, socrata_url, api_url,
    cobertura_geografica, jurisdiccion_nivel, jurisdiccion_geo_codes,
    jurisdiccion_confidence, jurisdiccion_inferred_at, jurisdiccion_reason,
    last_refreshed_at
) VALUES (
    %(dataset_id)s, %(name)s, %(entity_id)s, %(entity_raw)s, %(category)s,
    %(description)s, %(rows_updated_at)s, %(data_updated_at)s,
    %(metadata_updated_at)s, %(publication_date)s, %(created_at_socrata)s,
    %(provenance)s, %(license)s, %(license_id)s, %(update_frequency)s,
    %(sector)s, %(domain_metadata)s, %(source_type)s, %(source_portal)s,
    %(data_url)s, %(data_format)s, %(federated_status)s, %(socrata_url)s,
    %(api_url)s, %(cobertura_geografica)s, %(jurisdiccion_nivel)s,
    %(jurisdiccion_geo_codes)s, 'high', NOW(),
    'DCAT portal default por source_portal', NOW()
)
ON CONFLICT (dataset_id) DO UPDATE SET
    name = EXCLUDED.name,
    entity_id = EXCLUDED.entity_id,
    entity_raw = EXCLUDED.entity_raw,
    category = COALESCE(EXCLUDED.category, datasets.category),
    description = EXCLUDED.description,
    rows_updated_at = EXCLUDED.rows_updated_at,
    data_updated_at = EXCLUDED.data_updated_at,
    metadata_updated_at = EXCLUDED.metadata_updated_at,
    license = EXCLUDED.license,
    license_id = COALESCE(EXCLUDED.license_id, datasets.license_id),
    update_frequency = COALESCE(EXCLUDED.update_frequency, datasets.update_frequency),
    sector = COALESCE(EXCLUDED.sector, datasets.sector),
    domain_metadata = COALESCE(EXCLUDED.domain_metadata, datasets.domain_metadata),
    cobertura_geografica = COALESCE(datasets.cobertura_geografica, EXCLUDED.cobertura_geografica),
    jurisdiccion_nivel = COALESCE(datasets.jurisdiccion_nivel, EXCLUDED.jurisdiccion_nivel),
    jurisdiccion_geo_codes = COALESCE(datasets.jurisdiccion_geo_codes, EXCLUDED.jurisdiccion_geo_codes),
    data_url = EXCLUDED.data_url,
    last_refreshed_at = NOW()
"""


def main(portal_key: str, limit: int | None, dry_run: bool) -> None:
    if not DATABASE_URL:
        log.error("DATABASE_URL no definida")
        sys.exit(1)
    portal_cfg = PORTALS.get(portal_key)
    if not portal_cfg:
        log.error("Portal desconocido %r. Opciones: %s", portal_key, list(PORTALS))
        sys.exit(2)

    n_total = n_csv = n_inserted = 0
    rows_to_insert: list[dict[str, Any]] = []

    for ds in _iter_datasets(portal_cfg["url"], limit):
        n_total += 1
        # Dispatch por portal (hoy solo medellin, fácil agregar otros)
        if portal_key == "medellin":
            row = _build_row_medellin(ds, portal_cfg)
        else:
            row = None
        if not row:
            continue
        n_csv += 1
        rows_to_insert.append(row)

    log.info(
        "Discovery [%s]: %d datasets · %d con CSV usable · %d skip",
        portal_key, n_total, n_csv, n_total - n_csv,
    )

    if dry_run:
        log.info("DRY-RUN: no inserto. Ejemplo:")
        if rows_to_insert:
            s = rows_to_insert[0]
            log.info("  %s | %s | %s", s["dataset_id"], s["name"][:60], s["data_url"][:60])
            log.info("  license_id=%s update_frequency=%s sector=%s",
                     s.get("license_id"), s.get("update_frequency"), s.get("sector"))
        return

    with psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=False) as conn:
        with conn.cursor() as cur:
            for row in rows_to_insert:
                row["entity_id"] = _resolve_entity_id(cur, row["entity_raw"])
                if isinstance(row.get("domain_metadata"), dict):
                    row["domain_metadata"] = Jsonb(row["domain_metadata"])
                try:
                    cur.execute(_UPSERT_SQL, row)
                    n_inserted += 1
                except Exception as exc:  # noqa: BLE001
                    log.warning("UPSERT falló para %s: %s", row["dataset_id"], exc)
            conn.commit()

            # Higiene: el harvest puede reintroducir variantes de grafía de
            # category ("Función Pública") que parten el filtro TEMA hasta
            # el ETL siguiente (ciclo 4, 2026-07-13). Se re-unifica aquí.
            from scripts.classify_quality_flag import normalize_categories
            n_norm = normalize_categories(conn)
            if n_norm:
                log.info("Categorías re-normalizadas tras harvest: %d", n_norm)

    log.info("Insertados/actualizados: %d datasets (de %d candidatos)", n_inserted, n_csv)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--portal", default="medellin", choices=list(PORTALS),
                   help="Portal DCAT a cosechar")
    p.add_argument("--limit", type=int, default=None, help="Máx datasets a procesar")
    p.add_argument("--dry-run", action="store_true", help="No inserta, solo cuenta")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main(args.portal, args.limit, args.dry_run)
