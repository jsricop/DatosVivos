"""Extrae keywords temáticos por entidad desde el catálogo real de datos.gov.co.

Lee los metadatos del índice vectorial (ChromaDB), agrupa datasets por
entidad canónica (matching contra `acronyms.ENTITIES`), extrae texto de
`name` + `description`, tokeniza, filtra stopwords y términos genéricos,
ranquea por frecuencia y toma los top-N keywords por entidad.

Salida: `mcp_server/socrata/topic_keywords_data.py` con un dict literal
listo para importar — versionable en Git, sin runtime de extracción.

Uso:
    python -m scripts.extract_topic_keywords --top-k 8 --min-len 4
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Asegura import desde la raíz del repo
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb  # noqa: E402
from chromadb.config import Settings as ChromaSettings  # noqa: E402

from mcp_server.socrata.acronyms import ENTITIES  # noqa: E402

# Stopwords español + ruido específico del catálogo
SPANISH_STOPWORDS: frozenset[str] = frozenset(
    {
        "de",
        "la",
        "el",
        "en",
        "y",
        "a",
        "los",
        "las",
        "del",
        "se",
        "por",
        "un",
        "una",
        "para",
        "con",
        "no",
        "su",
        "al",
        "es",
        "lo",
        "como",
        "más",
        "pero",
        "sus",
        "le",
        "ya",
        "o",
        "este",
        "sí",
        "porque",
        "esta",
        "entre",
        "cuando",
        "muy",
        "sin",
        "sobre",
        "también",
        "me",
        "hasta",
        "hay",
        "donde",
        "quien",
        "desde",
        "todo",
        "nos",
        "durante",
        "todos",
        "uno",
        "les",
        "ni",
        "contra",
        "otros",
        "ese",
        "eso",
        "estos",
        "esos",
        "esa",
        "esas",
        "está",
        "estar",
        "han",
        "ha",
        "fue",
        "ser",
        "son",
        "que",
        "qué",
        "cuál",
        "cuales",
        "tal",
        "tan",
        "tales",
        "the",
        "of",
        "and",
        "to",
        "in",
        # Específicos del catálogo: muy genéricos, no son temáticos
        "datos",
        "información",
        "dato",
        "registro",
        "registros",
        "base",
        "fuente",
        "documento",
        "documentos",
        "lista",
        "catálogo",
        "público",
        "pública",
        "públicos",
        "públicas",
        "publicación",
        "publicado",
        "nacional",
        "nacionales",
        "colombia",
        "colombiano",
        "colombiana",
        "general",
        "generales",
        "total",
        "totales",
        "número",
        "cantidad",
        "año",
        "años",
        "fecha",
        "anual",
        "mensual",
        "diario",
        "diaria",
        "departamento",
        "departamental",
        "departamentos",
        "municipio",
        "municipios",
        "municipal",
        "región",
        "regional",
        "regionales",
        "territorio",
        "territorial",
        "nombre",
        "código",
        "tipo",
        "tipos",
        "categoría",
        "categorías",
        "según",
        "segun",
        "actualizado",
        "actualización",
        "diciembre",
        "ministerio",
        "instituto",
        "agencia",
        "unidad",
        "dirección",
        "secretaría",
        "superintendencia",
        "comisión",
        "centro",
        "corporación",
        "fondo",
        "consejo",
        "servicio",
        "sistema",
        "entidad",
        "entidades",
        "publica",
        "estado",
        "estados",
    }
)

# Palabras temáticas mínimas: las que pasaron el filtro genérico
# pero igual son demasiado generales para ser keyword temático útil
ADDITIONAL_FILTER: frozenset[str] = frozenset(
    {
        # Genéricos detectados en la primera corrida
        "ano",
        "fecha",
        "tipo",
        "valor",
        "valores",
        "id",
        "código",
        "codigo",
        "nombre",
        "descripcion",
        "descripción",
        "clasificada",
        "reservada",
        "índice",
        "indice",
        "inventario",
        "puede",
        "deben",
        "través",
        "traves",
        "diferentes",
        "personas",
        "listado",
        "permita",
        "conocer",
        "contiene",
        "esquema",
        "activo",
        "activos",
        "actividad",
        "vigencia",
        "elementos",
        "responsable",
        "responsables",
        "perfiles",
        "ingresado",
        "ingresados",
        "proceso",
        "procesos",
        "columnas",
        "junio",
        "julio",
        "marzo",
        "enero",
        "fechaactualizacion",
        "fechacorte",
        "estados",
        "rango",
        "clasificación",
        "clasificacion",
        "clasificados",
        "registrar",
        "obtenida",
        "adquirida",
        "controlada",
        "generada",
        "calificada",
        "anteriormente",
        "actualmente",
        "presenta",
        "presentan",
        "muestra",
        "muestran",
        "incluye",
        "incluyen",
        "corresponde",
        "corresponden",
        "asimismo",
        "además",
        "ademas",
        "decir",
        "siendo",
        "encuentra",
        "asistencias",
        "realizadas",
        "permite",
        "permiten",
        "publicado",
        "publicada",
        "publicadas",
        "comprende",
        "comprenden",
        "censo",
        "manera",
        "considerando",
        "donde",
        "cual",
        "cuales",
        "primer",
        "primera",
        "primeros",
        "primeras",
        "segundo",
        "segunda",
        "deberá",
        "debera",
        "podrá",
        "podra",
    }
)


# Heurísticas para matchear entidad → datasets en el índice
def _build_canonical_to_attribution_patterns() -> dict[str, list[re.Pattern]]:
    """Para cada entidad canónica, construye patrones que matchean su `attribution`.

    Cuando el attribution viene como `"Nombre Canónico - SIGLA, Ciudad"`,
    el canónico (parte antes del " - ") debe coincidir con ENTITIES[i]["canonical"].
    Las siglas en aliases también sirven como señal secundaria.
    """
    out: dict[str, list[re.Pattern]] = {}
    for entry in ENTITIES:
        canonical = entry["canonical"]
        patterns = []
        # Match exacto del canónico al inicio del attribution
        patterns.append(re.compile(rf"^{re.escape(canonical)}\b", re.IGNORECASE))
        # Match por sigla principal (primer alias UPPERCASE)
        for alias in entry["aliases"]:
            if alias.isupper() and len(alias) >= 3:
                patterns.append(re.compile(rf"-\s+{re.escape(alias)}\b", re.IGNORECASE))
                break
        out[canonical] = patterns
    return out


def _tokenize(text: str) -> list[str]:
    """Tokeniza texto a palabras alfabéticas en minúscula. Sin números, sin puntuación."""
    return re.findall(r"[a-záéíóúüñ]+", text.lower())


def _filter_token(token: str, min_len: int = 4) -> bool:
    """True si el token pasa filtros (longitud, no es stopword)."""
    if len(token) < min_len:
        return False
    if token in SPANISH_STOPWORDS:
        return False
    if token in ADDITIONAL_FILTER:
        return False
    return True


def extract_keywords_per_entity(
    chroma_path: Path,
    top_k: int = 8,
    min_len: int = 4,
    min_freq: int = 2,
) -> dict[str, list[str]]:
    """Devuelve dict canonical → list[keyword] usando el catálogo real.

    Args:
        chroma_path: ruta al índice ChromaDB.
        top_k: cuántos keywords devolver por entidad (top por frecuencia).
        min_len: longitud mínima de un token para considerarlo.
        min_freq: frecuencia mínima de un token para ser keyword.
    """
    client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    col = client.get_or_create_collection("datos_gov_co")
    all_data = col.get(include=["metadatas"])
    metadatas = all_data.get("metadatas") or []

    patterns_by_canonical = _build_canonical_to_attribution_patterns()

    # Set global de aliases en lowercase: si un token de la descripción coincide
    # con cualquier alias conocido, no es keyword temático (tier 1 ya lo cubre).
    all_aliases_lower: set[str] = {a.lower() for e in ENTITIES for a in e["aliases"]}

    # Acumula tokens por entidad canónica
    tokens_per_entity: dict[str, Counter] = defaultdict(Counter)
    unmatched = 0
    matched = 0

    for m in metadatas:
        entity_text = (m.get("entity") or "").strip()
        if not entity_text:
            continue

        # Encontrar a qué canonical pertenece este dataset
        matched_canonical = None
        for canonical, patterns in patterns_by_canonical.items():
            if any(p.search(entity_text) for p in patterns):
                matched_canonical = canonical
                break

        if not matched_canonical:
            unmatched += 1
            continue
        matched += 1

        # Combinar name + description (excluimos `tags` por ahora: el índice
        # almacena `columns_field_name` normalizados ahí, no tags semánticos —
        # bug histórico en build_index.py — produce ruido como
        # "conservaci_n_y_o" en vez de "conservación").
        name = m.get("name") or ""
        description = m.get("description") or ""
        text = f"{name} {description}"

        for tok in _tokenize(text):
            if not _filter_token(tok, min_len=min_len):
                continue
            # Excluir tokens que ya son aliases conocidos (tier 1 los cubre)
            if tok in all_aliases_lower:
                continue
            tokens_per_entity[matched_canonical][tok] += 1

    # Suplementos manuales para entidades donde la extracción data-driven omite
    # términos temáticos principales (porque los datasets publicados son sobre
    # casos específicos, no sobre el tema general). Ej: IDEAM publica datos de
    # "inundaciones" y "centros poblados" pero NO usa la palabra "clima" en sus
    # descriptions. Sin embargo, el usuario sí va a buscar "clima" → IDEAM.
    manual_supplements: dict[str, list[str]] = {
        "Corporación Agencia Nacional de Gobierno Digital": [
            "digital",
            "gobierno",
            "tecnología",
            "transformación",
            "innovación",
        ],
        "Instituto de Hidrología, Meteorología y Estudios Ambientales": [
            "clima",
            "meteorología",
            "hidrología",
            "lluvias",
            "temperatura",
            "precipitaciones",
        ],
        "Ministerio de Salud y Protección Social": [
            "salud",
            "enfermedades",
            "vacunas",
            "vacunación",
            "hospitales",
        ],
        "Ministerio de Educación Nacional": [
            "educación",
            "escuelas",
            "colegios",
            "matrícula",
            "estudiantes",
        ],
        "Ministerio de Tecnologías de la Información y las Comunicaciones": [
            "tecnología",
            "internet",
            "telecomunicaciones",
            "conectividad",
            "comunicaciones",
        ],
        "Ministerio de Ambiente y Desarrollo Sostenible": [
            "ambiente",
            "biodiversidad",
            "especies",
            "contaminación",
            "ecosistemas",
        ],
        "Ministerio de Agricultura y Desarrollo Rural": [
            "agricultura",
            "cultivos",
            "ganadería",
            "agropecuario",
            "campo",
        ],
        "Ministerio de Transporte": [
            "transporte",
            "movilidad",
            "vehículos",
            "tránsito",
        ],
        "Ministerio de Minas y Energía": [
            "minería",
            "petróleo",
            "gas",
            "electricidad",
            "energía",
        ],
        "Ministerio de Hacienda y Crédito Público": [
            "presupuesto",
            "tributario",
            "fiscal",
            "crédito",
            "finanzas",
        ],
        "Departamento Administrativo Nacional de Estadísticas": [
            "estadísticas",
            "censo",
            "demografía",
            "indicadores",
        ],
        "Departamento Nacional de Planeación": [
            "planeación",
            "planificación",
            "desarrollo",
            "presupuesto",
            "inversión",
        ],
        "Dirección de Impuestos y Aduanas Nacionales": [
            "impuestos",
            "tributario",
            "aduanas",
            "recaudo",
            "contribuyentes",
        ],
        "Instituto Colombiano para la Evaluación de la Educación": [
            "evaluación",
            "exámenes",
            "saber",
            "pruebas",
        ],
        "Instituto Nacional de Salud": [
            "salud",
            "vigilancia",
            "epidemiología",
            "enfermedades",
        ],
        "Instituto Nacional Penitenciario y Carcelario": [
            "cárceles",
            "presos",
            "penitenciario",
            "reclusos",
        ],
        "Instituto Geográfico Agustín Codazzi": [
            "catastro",
            "cartografía",
            "mapas",
            "predios",
        ],
        "Instituto Colombiano Agropecuario": [
            "agropecuario",
            "sanidad",
            "ganadería",
            "cultivos",
        ],
        "Instituto Colombiano de Bienestar Familiar": [
            "niñez",
            "infancia",
            "familia",
            "adolescentes",
        ],
        "Instituto Nacional de Vigilancia de Medicamentos y Alimentos": [
            "medicamentos",
            "alimentos",
            "sanitario",
        ],
        "Agencia Nacional de Seguridad Vial": [
            "vial",
            "tránsito",
            "accidentes",
            "seguridad",
        ],
        "Agencia Nacional de Tierras": [
            "tierras",
            "predios",
            "titulación",
            "reforma",
        ],
        "Agencia Nacional de Hidrocarburos": [
            "petróleo",
            "crudo",
            "gas",
            "hidrocarburos",
        ],
        "Agencia Nacional de Minería": [
            "minería",
            "minas",
            "mineros",
            "extracción",
        ],
        "Unidad de Planificación de Tierras Rurales, Adecuación de Tierras y Usos Agropecuarios": [
            "tierras",
            "rurales",
            "agropecuario",
            "planificación",
        ],
        "Unidad Nacional para la Gestión del Riesgo de desastres": [
            "riesgo",
            "desastres",
            "emergencias",
            "atención",
        ],
        "Unidad Administrativa Especial para la Atención y Reparación Integral a las Víctimas": [
            "víctimas",
            "reparación",
            "conflicto",
            "atención",
        ],
        "Unidad Administrativa Especial de Aeronáutica Civil": [
            "aviación",
            "aeronáutica",
            "aeropuertos",
            "vuelos",
        ],
        "Agencia para la Reincorporación y la Normalización": [
            "reincorporación",
            "desmovilización",
            "paz",
            "excombatientes",
        ],
        "Administradora Colombiana de Pensiones": [
            "pensiones",
            "jubilación",
            "afiliados",
            "aportes",
        ],
        "Servicio Nacional de Aprendizaje": [
            "aprendizaje",
            "formación",
            "capacitación",
            "laboral",
        ],
        "Jurisdicción Especial para la Paz": [
            "paz",
            "transicional",
            "justicia",
            "conflicto",
        ],
        "Ministerio de Igualdad y Equidad": [
            "igualdad",
            "equidad",
            "género",
            "diversidad",
            "inclusión",
        ],
        "Fondo de Garantías de Entidades Cooperativas": [
            "cooperativas",
            "garantías",
            "ahorradores",
            "depósitos",
        ],
    }

    # Palabras de "rol" en canonicals que NO son temáticas (igual filtradas)
    role_words: frozenset[str] = frozenset(
        {
            "ministerio",
            "departamento",
            "administrativo",
            "agencia",
            "instituto",
            "unidad",
            "superintendencia",
            "corporación",
            "corporacion",
            "fondo",
            "consejo",
            "servicio",
            "sistema",
            "comisión",
            "comision",
            "dirección",
            "direccion",
            "centro",
            "general",
            "nacional",
            "colombiano",
            "colombiana",
            "colombia",
            "público",
            "publico",
            "pública",
            "publica",
            "república",
            "republica",
            "sociedad",
            "especial",
            "autoridad",
            "escuela",
            "superior",
            "del",
            "para",
            "los",
            "las",
            "el",
            "la",
            "de",
            "en",
            "y",
            "por",
            "con",
            "sin",
            "su",
            "se",
        }
    )

    def _canonical_topic_words(canonical: str) -> list[str]:
        """Extrae palabras temáticas del nombre canónico (excluyendo role words)."""
        tokens = re.findall(r"[a-záéíóúüñ]+", canonical.lower())
        return [t for t in tokens if t not in role_words and _filter_token(t, min_len=4)]

    # Tomar top-K por entidad respetando min_freq, enriqueciendo con canonical
    result: dict[str, list[str]] = {}
    for entry in ENTITIES:
        canonical = entry["canonical"]
        counter = tokens_per_entity.get(canonical) or Counter()
        # Excluir tokens que solo aparecen una vez (ruido)
        filtered = [(t, c) for t, c in counter.items() if c >= min_freq]
        filtered.sort(key=lambda x: -x[1])
        extracted = [t for t, _ in filtered[:top_k]]

        # Pipeline de enriquecimiento limpio (orden de prioridad):
        #   1. Manual supplements (anteponen) — temas que la extracción omite.
        #   2. Canonical topic words — palabras del nombre canónico, filtrando role.
        #   3. Alias topic words — palabras de aliases multi-word (no la sigla).
        # Tras cada paso aplicamos el filtro inviolable: nada que sea un alias
        # conocido en `acronyms.py` puede aparecer (tier 1 lo cubre).

        def _accept(word: str) -> bool:
            return (
                word
                and word not in role_words
                and word not in all_aliases_lower
                and _filter_token(word, min_len=4)
            )

        merged: list[str] = []
        seen: set[str] = set()

        # Step 1: manual supplements (anteponen, son los más importantes)
        for word in manual_supplements.get(canonical, []):
            if _accept(word) and word not in seen:
                merged.append(word)
                seen.add(word)

        # Step 2: extracción data-driven
        for word in extracted:
            if _accept(word) and word not in seen:
                merged.append(word)
                seen.add(word)

        # Step 3: canonical topic words (si todavía nos faltan)
        if len(merged) < 3:
            for word in _canonical_topic_words(canonical):
                if _accept(word) and word not in seen:
                    merged.append(word)
                    seen.add(word)
                if len(merged) >= top_k:
                    break

        # Step 4: alias topic words (tokens internos de aliases multi-word)
        if len(merged) < 3:
            for alias in entry["aliases"]:
                for word in re.findall(r"[a-záéíóúüñ]+", alias.lower()):
                    if _accept(word) and word not in seen:
                        merged.append(word)
                        seen.add(word)
                    if len(merged) >= top_k:
                        break
                if len(merged) >= top_k:
                    break

        if merged:
            result[canonical] = merged[:top_k]

    return result


def write_data_module(
    keywords: dict[str, list[str]],
    output_path: Path,
) -> None:
    """Escribe `topic_keywords_data.py` como módulo Python con dict literal."""
    header = '''"""Generated by `scripts/extract_topic_keywords.py` — NO EDITAR A MANO.

Datos extraídos del catálogo real de datos.gov.co indexado en ChromaDB.
Para regenerar: `python -m scripts.extract_topic_keywords --top-k N`.

Cada entrada es un dict de `canonical_name -> [keywords]`, donde keywords
son palabras temáticas (no nombres de entidades) extraídas de los campos
`name` + `description` + `tags` de los datasets publicados por cada entidad.
"""

from __future__ import annotations

from typing import Final

KEYWORDS_BY_CANONICAL: Final[dict[str, list[str]]] = '''
    lines = [header]
    # Pretty-print dict con orden estable
    lines.append("{\n")
    for canonical in sorted(keywords.keys()):
        kws = keywords[canonical]
        kws_repr = ", ".join(repr(k) for k in kws)
        # Wrap si la línea es muy larga
        if len(kws_repr) > 80:
            kws_repr_multi = "\n        " + ",\n        ".join(repr(k) for k in kws) + ",\n    "
            lines.append(f"    {canonical!r}: [{kws_repr_multi}],\n")
        else:
            lines.append(f"    {canonical!r}: [{kws_repr}],\n")
    lines.append("}\n")

    output_path.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--min-len", type=int, default=4)
    parser.add_argument("--min-freq", type=int, default=2)
    parser.add_argument(
        "--chroma-path",
        type=Path,
        default=Path("./data/vector_index"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./mcp_server/socrata/topic_keywords_data.py"),
    )
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args()

    print(f"Leyendo índice: {args.chroma_path}")
    keywords = extract_keywords_per_entity(
        chroma_path=args.chroma_path,
        top_k=args.top_k,
        min_len=args.min_len,
        min_freq=args.min_freq,
    )

    print(f"Entidades con keywords extraídos: {len(keywords)}")
    if args.print_summary:
        # Imprimir las primeras 15
        for i, (canonical, kws) in enumerate(sorted(keywords.items())):
            if i >= 15:
                break
            print(f"  {canonical[:50]:50} → {kws}")
        print(f"  ... ({len(keywords) - 15} más)")

    write_data_module(keywords, args.output)
    print(f"Escrito: {args.output}")
    print(f"Total entradas: {len(keywords)}")


if __name__ == "__main__":
    main()
