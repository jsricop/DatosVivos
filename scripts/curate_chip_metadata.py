#!/usr/bin/env python3
"""Curación de metadata de jurisdicción geográfica para los datasets del catálogo.

Diseñado para Fase 1 del audit top-down. Llena `jurisdiccion_nivel` y
`jurisdiccion_geo_codes` en la tabla `datasets` para que la UI de chips pueda
filtrar por TERRITORIO sin retrieval ML.

Estrategia (reglas escalonadas, orden de precedencia):

  1. **Distrito Capital**: entity/name menciona Bogotá / D.C. / Distrito Capital.
  2. **Municipal**: entity/name menciona un municipio del catálogo DIVIPOLA
     (`MUNICIPIOS_DIVIPOLA`). Se exigen matches inequívocos: nombre completo
     entre tokens, y se descartan municipios cuyo nombre coincide con
     departamento (ej. "Santander", "Boyacá", "Arauca" son ambos dpto y mpio).
  3. **Departamental**: entity/name menciona un departamento de `DEPARTAMENTOS`
     o uno de sus sinónimos.
  4. **Nacional**: entity/name matchea patrón "Ministerio", "Departamento
     Nacional", "Agencia Nacional", "Instituto Nacional", "Superintendencia",
     "DANE", "DNP", "ICA", "INVÍAS", "IDEAM", etc.
  5. **Desconocido**: ningún patrón calza. `nivel=null`, queda para revisión
     manual o LLM en próxima iteración.

Confidence:
  - **high**: match unívoco (entity contiene el nombre canónico de un dpto/
    mpio/distrito, O matchea acrónimo nacional sin geo en el nombre).
  - **medium**: match por sinónimo o por keyword genérica.
  - **low**: reservado para fallback LLM (no implementado todavía).

Uso:
    # Dry-run local (no escribe DB):
    python scripts/curate_chip_metadata.py --dry-run --limit 50

    # Aplicar en VM:
    docker compose exec -T api python scripts/curate_chip_metadata.py

    # Re-inferir solo los que están sin jurisdicción:
    python scripts/curate_chip_metadata.py --only-missing

Reporte:
    Stdout: tabla por nivel + confidence + top 20 entidades sin clasificar.
    Filesystem: data/curation/jurisdiccion_report_YYYY-MM-DD.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Importes locales — requiere correr desde la raíz del repo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_engine.geo_resolver import DEPARTAMENTOS  # noqa: E402
from ai_engine.geo_resolver_data import MUNICIPIOS_DIVIPOLA  # noqa: E402


# ----------------------------------------------------------------------
# Normalización
# ----------------------------------------------------------------------


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def _norm(text: str | None) -> str:
    if not text:
        return ""
    return _strip_accents(text).lower().strip()


# ----------------------------------------------------------------------
# Reglas pre-compiladas
# ----------------------------------------------------------------------


# Patrones para distrito capital. Los multi-palabra son seguros con `in`;
# los cortos (d.c., d. c., dc) requieren word boundary o pueden caer en
# falsos positivos (ej. una entidad con "D.C." en otro contexto).
_BOGOTA_TOKENS = (
    "bogota d.c.",
    "bogota d c",
    "bogota dc",
    "bogota distrito capital",
    "distrito capital",
    "alcaldia mayor de bogota",
    "secretaria distrital",
    "secretaria de educacion del distrito",
)
_BOGOTA_TOKENS_BOUNDARY = (
    "d.c.",
    "d. c.",
    "dc",
)

# "bogota" solo es señal si NO viene en compuestos que la incluyen sin ser geo
# (ej. "puerto boyaca"). Por ahora aceptamos "bogota" como token aislado.

# Acrónimos / patrones que indican nivel NACIONAL (sin geo).
_NACIONAL_TOKENS = (
    "ministerio",
    "departamento nacional",
    "departamento administrativo",   # DAFP, DPS, DANE
    "agencia nacional",
    "agencia de desarrollo",         # ADR Rural
    "agencia para la",               # ARN, ADRES
    "instituto nacional",
    "instituto colombiano",          # ICBF, ICA (también acrónimos)
    "unidad nacional",
    "unidad administrativa",         # UAESP, USPEC, etc.
    "unidad de proyeccion",          # URF
    "unidad de servicios",
    "unidad de pension",
    "superintendencia",
    "presidencia",
    "vicepresidencia",
    "consejeria",
    "comision nacional",
    "comision de regulacion",        # CRA, CREG
    "consejo nacional",
    "registraduria nacional",
    "procuraduria",
    "contraloria",
    "fiscalia",
    "defensoria del pueblo",
    "auditoria general",
    "rama judicial",
    "congreso de la republica",
    "senado de la republica",
    "camara de representantes",
    "corte constitucional",
    "consejo de estado",
    "corte suprema",
    "archivo general de la nacion",
    "centro de memoria historica",
    "centro nacional",
    "escuela superior",              # ESAP
    "fondo nacional",
    "fondo de garantias",
    "fondo para el financiamiento",
    "fondo para la",
    "sociedad fiduciaria",
    "sociedad de activos",
    "administradora colombiana",     # COLPENSIONES (también)
    "banco agrario",
    "banco de la republica",
    "banco de comercio",
    "positiva compania",             # Positiva Seguros (estatal nacional)
    "confecamaras",
    "hospital militar",
    "club militar",
    "ejercito nacional",
    "armada nacional",
    "policia nacional",
    "fuerza aerea",
    "fuerzas militares",
)
_NACIONAL_ACRONIMOS = (
    "dane",
    "dnp",
    "ica",
    "icbf",
    "invias",
    "ideam",
    "icfes",
    "icetex",
    "mintic",
    "minsalud",
    "mineducacion",
    "mincomercio",
    "minenergia",
    "minambiente",
    "minvivienda",
    "minagricultura",
    "minjusticia",
    "mintransporte",
    "mintrabajo",
    "minhacienda",
    "mindefensa",
    "minrelaciones",
    "mincultura",
    "mininterior",
    "ans",
    "ani",
    "ant",
    "anla",
    "aerocivil",
    "fontur",
    "findeter",
    "supersalud",
    "supertransporte",
    "supersolidaria",
    "supersociedades",
    "superfinanciera",
    "superservicios",
    "siniefa",
    "secop",
    "sgr",
    "sgsss",
    "uaesp",
    "unp",
    "ungrd",
    "upra",
    "upme",
    "urt",
    "uariv",
    # ---- Agregados tras inspección top distrito_capital (Fase 1 prereq) ----
    "agn",          # Archivo General de la Nación
    "arn",          # Agencia Reincorporación y Normalización
    "adr",          # Agencia de Desarrollo Rural
    "dafp",         # Departamento Administrativo Función Pública
    "dps",          # Departamento Administrativo para Prosperidad Social
    "esap",         # Escuela Superior de Administración Pública
    "finagro",
    "coljuegos",
    "urf",          # Unidad de Proyección Normativa
    "uspec",        # Unidad de Servicios Penitenciarios
    "fogafin",
    "fogacoop",
    "fiduagraria",
    "sae",          # Sociedad de Activos Especiales
    "cra",          # Comisión Regulación Agua
    "creg",         # Comisión Regulación Energía y Gas
    "adres",        # Administradora de Recursos del SGSSS
    "colpensiones",
    "porvenir",
    "fonade",
    "enterritorio",
    "fondes",
    "imprenta nacional",
)

# Municipios que ALSO son nombres de departamento (ambiguos): descartarlos
# para evitar falsos positivos. Ej. "Antioquia" es dpto pero también mpio
# en Boyacá (`Santa Fé de Antioquia`).
_AMBIGUOUS_MPIO_NAMES = {_norm(name) for name, _, _ in DEPARTAMENTOS}
# Casos adicionales — nombres de mpio que coinciden con palabras MUY comunes
# o con el nombre del país, generando falsos positivos en entity names que
# claramente no se refieren a ese municipio (ej. "Universidad Nacional de
# Colombia" matchearía 'Colombia' = mpio en Huila).
_AMBIGUOUS_MPIO_NAMES.update({
    "colombia",       # mpio en Huila vs nombre del país
    "armenia",        # mpio en Antioquia vs capital de Quindío (más buscado)
    "florida",        # mpio en Valle del Cauca vs estado USA
    "california",     # mpio en Santander vs estado USA
    "buenos aires",   # mpio en Cauca vs ciudad Argentina
    "argentina",      # mpio en Santander vs país
    "venecia",        # mpio en Antioquia vs Italia
})

# Construir lookup tables eficientes
_DEPT_BY_NORM: dict[str, tuple[str, str]] = {}
for canon, code, synonyms in DEPARTAMENTOS:
    _DEPT_BY_NORM[_norm(canon)] = (canon, code)
    for syn in synonyms:
        _DEPT_BY_NORM[_norm(syn)] = (canon, code)

# Para municipios, indexamos por nombre normalizado pero excluimos los
# que coinciden con nombre de dpto (ambiguos).
_MPIO_BY_NORM: dict[str, tuple[str, str, str]] = {}
for nom, cod_mpio, cod_dpto in MUNICIPIOS_DIVIPOLA:
    norm = _norm(nom)
    if norm in _AMBIGUOUS_MPIO_NAMES:
        continue  # evitar "Antioquia", "Boyacá", "Santander" como mpio
    # Si el mismo nombre aparece en varios dptos (ej. "Argelia"), guardamos
    # solo el primero. Match por nombre solo es señal "medium" en esos casos.
    _MPIO_BY_NORM.setdefault(norm, (nom, cod_mpio, cod_dpto))

# Aliases coloquiales de capitales — nombres oficiales son largos
# ("Santiago de Cali", "Cartagena de Indias") pero el usuario y las entidades
# casi siempre usan el alias corto.
_MPIO_ALIASES: tuple[tuple[str, str, str], ...] = (
    # alias_norm, cod_mpio canonical, cod_dpto
    ("cali", "76001", "76"),         # Santiago de Cali
    ("cartagena", "13001", "13"),    # Cartagena de Indias
    ("popayan", "19001", "19"),
    ("ibague", "73001", "73"),
    ("pereira", "66001", "66"),
    ("manizales", "17001", "17"),
    ("neiva", "41001", "41"),
    ("pasto", "52001", "52"),
    ("villavicencio", "50001", "50"),
    ("santa marta", "47001", "47"),
    ("riohacha", "44001", "44"),
    ("monteria", "23001", "23"),
    ("sincelejo", "70001", "70"),
    ("valledupar", "20001", "20"),
    ("cucuta", "54001", "54"),
    ("bucaramanga", "68001", "68"),
    ("yopal", "85001", "85"),
    ("florencia", "18001", "18"),
    ("mocoa", "86001", "86"),
    ("quibdo", "27001", "27"),
    ("mitu", "97001", "97"),
    ("inirida", "94001", "94"),
    ("leticia", "91001", "91"),
    ("tunja", "15001", "15"),
)
for alias_norm, cod_mpio, cod_dpto in _MPIO_ALIASES:
    # Buscar el canonical en MUNICIPIOS_DIVIPOLA por código
    canonical = next(
        (n for n, c, d in MUNICIPIOS_DIVIPOLA if c == cod_mpio),
        alias_norm.title(),
    )
    _MPIO_BY_NORM.setdefault(alias_norm, (canonical, cod_mpio, cod_dpto))


# ----------------------------------------------------------------------
# Inferencia por dataset
# ----------------------------------------------------------------------


def _word_in(needle: str, haystack: str) -> bool:
    """True si needle aparece como token completo en haystack (ya normalizados).

    Evita matches parciales del estilo "santander" en "norte de santander"
    o "bogota" en "puerto boyaca".
    """
    if not needle or not haystack:
        return False
    pattern = r"(?:^|\s|[\(\)\,\;\:\-\.])" + re.escape(needle) + r"(?:$|\s|[\(\)\,\;\:\-\.])"
    return bool(re.search(pattern, haystack))


def _detect_matches(haystacks: list[str]) -> dict[str, Any]:
    """Detecta TODOS los matches potenciales en entity+name. La decisión de
    precedencia se hace después en `infer_jurisdiccion` con lógica explícita.
    """
    matches: dict[str, Any] = {
        "distrito": None,    # ('bogota d.c.', '11') si match
        "nacional": None,    # ('ministerio', 'token') si match
        "dpto": None,        # ('Antioquia', '05') si match
        "mpio": None,        # ('Medellín', '05001', '05') si match
    }
    for h in haystacks:
        # Distrito. Multi-palabra → `in`. Cortos (d.c., dc) → word boundary
        # para no atrapar entidades con "D.C." en otro contexto.
        if matches["distrito"] is None:
            for tok in _BOGOTA_TOKENS:
                if tok in h:
                    matches["distrito"] = (tok, "11")
                    break
            if matches["distrito"] is None:
                for tok in _BOGOTA_TOKENS_BOUNDARY:
                    if _word_in(tok, h):
                        matches["distrito"] = (tok, "11")
                        break
            if matches["distrito"] is None and _word_in("bogota", h):
                matches["distrito"] = ("bogota", "11")
        # Nacional
        if matches["nacional"] is None:
            for tok in _NACIONAL_TOKENS:
                if tok in h:
                    matches["nacional"] = ("national_keyword", tok)
                    break
            if matches["nacional"] is None:
                for acron in _NACIONAL_ACRONIMOS:
                    if _word_in(acron, h):
                        matches["nacional"] = ("national_acronym", acron)
                        break
            if matches["nacional"] is None and _word_in("nacional", h):
                matches["nacional"] = ("national_keyword", "nacional")
        # Dpto — registramos TODOS los matches. La selección de cuál usar
        # (Bogotá vs otro) la hace `infer_jurisdiccion`. Esto evita que el
        # primer match en orden alfabético se imponga sobre uno semánticamente
        # más fuerte (ej. "Cundinamarca, Bogotá D.C." → preferir Cundinamarca).
        if matches["dpto"] is None:
            found: list[tuple[str, str]] = []
            for dpto_norm, (canon, code) in _DEPT_BY_NORM.items():
                if _word_in(dpto_norm, h):
                    found.append((canon, code))
            if found:
                # Preferir primer dpto NO-Bogotá. Si todos son Bogotá, queda Bogotá.
                non_bogota = next((f for f in found if f[1] != "11"), None)
                matches["dpto"] = non_bogota or found[0]
        # Mpio
        if matches["mpio"] is None:
            for mpio_norm, (canon, cod_mpio, cod_dpto) in _MPIO_BY_NORM.items():
                if _word_in(mpio_norm, h):
                    matches["mpio"] = (canon, cod_mpio, cod_dpto)
                    break
    return matches


def infer_jurisdiccion(
    entity_raw: str | None,
    name: str | None,
    description: str | None,
) -> tuple[str | None, list[str] | None, str, str | None]:
    """Devuelve (nivel, codes, confidence, reason).

    Lógica de precedencia (clave del audit):
      - dpto/mpio específico SIEMPRE gana sobre nacional o distrito, porque
        "Contraloría Departamental del Cauca" es del Cauca, no nacional.
      - distrito + nacional → nacional (entidad nacional con sede en Bogotá:
        Ministerios, INS, DANE — su jurisdicción es nacional, no distrital).
      - solo distrito (sin dpto/nacional) → distrito_capital genuino.
    """
    haystacks = [_norm(entity_raw), _norm(name)]
    m = _detect_matches(haystacks)

    # Helper: ¿el match de dpto es Bogotá (code 11)? Bogotá-como-dpto es
    # evidencia DÉBIL — la mayoría de entidades nacionales tienen sede física
    # en Bogotá y la mencionan en el entity_raw. Otros dptos son evidencia
    # FUERTE (un dataset que menciona "Cauca" raramente es nacional).
    dpto_is_bogota = m["dpto"] is not None and m["dpto"][1] == "11"
    has_other_dpto = m["dpto"] is not None and not dpto_is_bogota

    # 1. Mpio específico siempre gana
    if m["mpio"] is not None:
        canon, cod_mpio, cod_dpto = m["mpio"]
        return (
            "municipal",
            [cod_mpio],
            "high",
            f"mpio_match: '{canon}' (cod {cod_mpio}) en entity/name",
        )

    # 2. Dpto NO-Bogotá gana sobre nacional (Contraloría Departamental del Cauca)
    if has_other_dpto:
        canon, code = m["dpto"]
        return (
            "departamental",
            [code],
            "high",
            f"dpto_match: '{canon}' (cod {code}) en entity/name",
        )

    # 3. Nacional (incluso si hay match de Bogotá-como-dpto-o-distrito,
    #    Bogotá es sede física, no jurisdicción)
    if m["nacional"] is not None:
        kind, tok = m["nacional"]
        conf = "high" if kind == "national_acronym" or tok != "nacional" else "medium"
        sede = " (sede Bogotá D.C.)" if (dpto_is_bogota or m["distrito"]) else ""
        return (
            "nacional",
            [],
            conf,
            f"{kind}: '{tok}' en entity/name{sede}",
        )

    # 4. Bogotá-como-dpto sin nacional → distrito_capital (Alcaldía/Secretaría
    #    distrital). El código 11 es el mismo.
    if dpto_is_bogota or m["distrito"] is not None:
        tok = (m["distrito"][0] if m["distrito"] else m["dpto"][0])
        return (
            "distrito_capital",
            ["11"],
            "high",
            f"distrito_capital_token: '{tok}' en entity/name",
        )

    # 4. Fallback description (solo dpto, evita ruido)
    desc_norm = _norm(description)
    if desc_norm:
        for dpto_norm, (dpto_canon, dpto_code) in _DEPT_BY_NORM.items():
            if _word_in(dpto_norm, desc_norm):
                return (
                    "departamental",
                    [dpto_code],
                    "medium",
                    f"desc_dpto_match: '{dpto_canon}' en description",
                )

    return (None, None, "none", None)


# ----------------------------------------------------------------------
# DB I/O
# ----------------------------------------------------------------------


def _connect(database_url: str):
    """Lazy connect — solo importamos psycopg si vamos a escribir."""
    import psycopg

    return psycopg.connect(database_url)


def fetch_datasets(conn, only_missing: bool, limit: int | None) -> list[dict[str, Any]]:
    where = "WHERE jurisdiccion_nivel IS NULL" if only_missing else ""
    sql = f"""
        SELECT dataset_id, name, entity_raw, description
        FROM datasets
        {where}
        ORDER BY view_count DESC NULLS LAST, dataset_id ASC
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    with conn.cursor() as cur:
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def upsert_jurisdiccion(conn, dataset_id: str, nivel: str | None, codes: list[str] | None,
                       confidence: str, reason: str | None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE datasets
            SET jurisdiccion_nivel = %s,
                jurisdiccion_geo_codes = %s::jsonb,
                jurisdiccion_confidence = %s,
                jurisdiccion_reason = %s,
                jurisdiccion_inferred_at = NOW()
            WHERE dataset_id = %s
            """,
            (
                nivel,
                json.dumps(codes) if codes is not None else None,
                confidence if confidence != "none" else None,
                reason,
                dataset_id,
            ),
        )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def _format_report(stats: dict[str, Any]) -> str:
    nivel_lines = [
        f"  {nivel or '(none)':<20} {count:>5}  ({100*count/stats['total']:.1f}%)"
        for nivel, count in sorted(stats["por_nivel"].items(), key=lambda x: -x[1])
    ]
    conf_lines = [
        f"  {conf or '(none)':<10} {count:>5}  ({100*count/stats['total']:.1f}%)"
        for conf, count in sorted(stats["por_confidence"].items(), key=lambda x: -x[1])
    ]
    sin_clas = "\n".join(
        f"  - {ent}  ({count})" for ent, count in stats["top_sin_clasificar"]
    )
    cobertura_pct = 100.0 * stats["clasificados"] / stats["total"] if stats["total"] else 0.0
    return (
        f"Procesados: {stats['total']}\n"
        f"Clasificados (nivel ≠ none): {stats['clasificados']} ({cobertura_pct:.1f}%)\n\n"
        f"Por nivel:\n" + "\n".join(nivel_lines) + "\n\n"
        f"Por confidence:\n" + "\n".join(conf_lines) + "\n\n"
        f"Top 20 entidades sin clasificar:\n" + (sin_clas or "  (ninguna)") + "\n"
    )


def _main(args: argparse.Namespace) -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url and not args.dry_run:
        print("ERROR: DATABASE_URL no definida. Use --dry-run para inferir sin escribir.",
              file=sys.stderr)
        return 2

    if args.dry_run and database_url is None:
        # Sin DB: leemos un archivo local fixture si existe
        fixture = Path("data/sample_datasets.json")
        if not fixture.exists():
            print(f"ERROR: --dry-run sin DATABASE_URL requiere {fixture}", file=sys.stderr)
            return 2
        rows = json.loads(fixture.read_text())[: args.limit or 100]
        conn = None
    else:
        conn = _connect(database_url)
        rows = fetch_datasets(conn, only_missing=args.only_missing, limit=args.limit)

    print(f"Inferencia sobre {len(rows)} datasets ({'dry-run' if args.dry_run else 'apply'})...",
          file=sys.stderr)

    por_nivel: Counter = Counter()
    por_confidence: Counter = Counter()
    sin_clasificar_entities: Counter = Counter()
    sample_classified: list[dict[str, Any]] = []
    sample_unclassified: list[dict[str, Any]] = []

    for i, row in enumerate(rows):
        nivel, codes, conf, reason = infer_jurisdiccion(
            row.get("entity_raw"), row.get("name"), row.get("description")
        )
        por_nivel[nivel] += 1
        por_confidence[conf] += 1
        if nivel is None:
            sin_clasificar_entities[(row.get("entity_raw") or "(sin entity)")[:80]] += 1
            if len(sample_unclassified) < 10:
                sample_unclassified.append({"id": row["dataset_id"], "name": row.get("name", "")[:80],
                                            "entity": row.get("entity_raw")})
        else:
            if len(sample_classified) < 10:
                sample_classified.append({"id": row["dataset_id"], "nivel": nivel,
                                          "codes": codes, "reason": reason})

        if not args.dry_run and conn is not None:
            upsert_jurisdiccion(conn, row["dataset_id"], nivel, codes, conf, reason)
            if (i + 1) % 500 == 0:
                conn.commit()
                print(f"  {i+1}/{len(rows)} procesados, commit parcial", file=sys.stderr)

    if not args.dry_run and conn is not None:
        conn.commit()
        conn.close()

    stats = {
        "total": len(rows),
        "clasificados": sum(c for nivel, c in por_nivel.items() if nivel is not None),
        "por_nivel": dict(por_nivel),
        "por_confidence": dict(por_confidence),
        "top_sin_clasificar": sin_clasificar_entities.most_common(20),
        "sample_classified": sample_classified,
        "sample_unclassified": sample_unclassified,
    }

    print("\n" + _format_report(stats), file=sys.stderr)

    out_dir = Path("data/curation")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    out_path = out_dir / f"jurisdiccion_report_{stamp}.json"
    out_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False))
    print(f"Reporte: {out_path}", file=sys.stderr)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo infiere e imprime stats, no escribe a DB.")
    parser.add_argument("--only-missing", action="store_true",
                        help="Solo procesa datasets con jurisdiccion_nivel IS NULL.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Procesa máximo N datasets (debug).")
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(_main(_parse_args()))
