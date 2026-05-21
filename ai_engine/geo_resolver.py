"""Resolver geográfico: detecta menciones a departamentos/municipios colombianos
y devuelve el contexto canónico DIVIPOLA.

Diseño (acuerdo con usuario, 2026-05-18):

- **No interfiere con preguntas generales**: si no hay señal geográfica
  explícita, devuelve `None` y el pipeline funciona exactamente como hoy.
- **Opt-in por contenido**: activa filtros/boost solo cuando detecta
  departamentos, municipios, "Colombia/nacional", o "por departamento/municipio".
- **Cobertura inicial**: 32 departamentos + Bogotá D.C. + capitales departamentales.
  Cobertura completa de municipios queda para una fase posterior alimentada con
  telemetría real.

Reglas de matching:
1. Normalización: lowercase + sin tildes + sin puntuación.
2. Match exacto sobre tokens.
3. Si no hay match exacto, fuzzy con `difflib.get_close_matches` (cutoff 0.85).
4. Cuando matchea un municipio, también se popula el departamento padre.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass, field

from ai_engine.geo_resolver_data import MUNICIPIOS_DIVIPOLA

# ----------------------------------------------------------------------
# Diccionario DIVIPOLA
# ----------------------------------------------------------------------

# 32 departamentos + Bogotá D.C. (cod_dpto '11').
# (canonical_name, code, [sinónimos])
DEPARTAMENTOS: list[tuple[str, str, list[str]]] = [
    ("Amazonas", "91", []),
    ("Antioquia", "05", []),
    ("Arauca", "81", []),
    ("Atlántico", "08", ["atlantico"]),
    ("Bogotá D.C.", "11", ["bogota", "bogota dc", "bogota d.c.", "distrito capital", "santa fe de bogota"]),
    ("Bolívar", "13", ["bolivar"]),
    ("Boyacá", "15", ["boyaca"]),
    ("Caldas", "17", []),
    ("Caquetá", "18", ["caqueta"]),
    ("Casanare", "85", []),
    ("Cauca", "19", []),
    ("Cesar", "20", []),
    ("Chocó", "27", ["choco"]),
    ("Córdoba", "23", ["cordoba"]),
    ("Cundinamarca", "25", []),
    ("Guainía", "94", ["guainia"]),
    ("Guaviare", "95", []),
    ("Huila", "41", []),
    ("La Guajira", "44", ["guajira"]),
    ("Magdalena", "47", []),
    ("Meta", "50", []),
    ("Nariño", "52", ["narino"]),
    ("Norte de Santander", "54", []),
    ("Putumayo", "86", []),
    ("Quindío", "63", ["quindio"]),
    ("Risaralda", "66", []),
    ("San Andrés", "88", ["san andres", "san andres y providencia", "providencia"]),
    ("Santander", "68", []),
    ("Sucre", "70", []),
    ("Tolima", "73", []),
    ("Valle del Cauca", "76", ["valle"]),
    ("Vaupés", "97", ["vaupes"]),
    ("Vichada", "99", []),
]

# Capitales departamentales hardcoded (lista corta, mantenida explícitamente
# para que la regla "anti-capital" sepa exactamente qué mpios saltarse cuando
# la pregunta usa plural genérico). El catálogo completo de ~1100 mpios vive
# en `geo_resolver_data.MUNICIPIOS_DIVIPOLA`.
# (mpio_name, mpio_code, dpto_code)
CAPITALES: list[tuple[str, str, str]] = [
    ("Leticia", "91001", "91"),
    ("Medellín", "05001", "05"),
    ("Arauca", "81001", "81"),  # también es nombre de dpto
    ("Barranquilla", "08001", "08"),
    ("Cartagena", "13001", "13"),
    ("Tunja", "15001", "15"),
    ("Manizales", "17001", "17"),
    ("Florencia", "18001", "18"),
    ("Yopal", "85001", "85"),
    ("Popayán", "19001", "19"),
    ("Valledupar", "20001", "20"),
    ("Quibdó", "27001", "27"),
    ("Montería", "23001", "23"),
    ("Inírida", "94001", "94"),
    ("San José del Guaviare", "95001", "95"),
    ("Neiva", "41001", "41"),
    ("Riohacha", "44001", "44"),
    ("Santa Marta", "47001", "47"),
    ("Villavicencio", "50001", "50"),
    ("Pasto", "52001", "52"),
    ("Cúcuta", "54001", "54"),
    ("Mocoa", "86001", "86"),
    ("Armenia", "63001", "63"),
    ("Pereira", "66001", "66"),
    ("San Andrés", "88001", "88"),
    ("Bucaramanga", "68001", "68"),
    ("Sincelejo", "70001", "70"),
    ("Ibagué", "73001", "73"),
    ("Cali", "76001", "76"),
    ("Mitú", "97001", "97"),
    ("Puerto Carreño", "99001", "99"),
    # Mpios grandes no-capitales más frecuentes
    ("Soledad", "08758", "08"),
    ("Bello", "05088", "05"),
    ("Soacha", "25754", "25"),
    ("Itagüí", "05360", "05"),
    ("Envigado", "05266", "05"),
    ("Cartago", "76147", "76"),
    ("Buenaventura", "76109", "76"),
]


# Países extranjeros que comparten nombre o se parecen — protección contra falsos positivos.
PAISES_EXTRANJEROS = {"ecuador", "peru", "venezuela", "brasil", "panama", "mexico", "chile", "argentina"}

# Nombres de mpio que NUNCA se matchean directamente porque se confunden con
# entidades de mayor jerarquía (país, depto). Quienes quieran el mpio específico
# pueden agregar nombre+depto ("Colombia, Huila") y se resolverá vía dpto.
_MPIO_BLACKLIST: set[str] = {
    "colombia",  # mpio en Huila — choca con país Colombia
}

# Stopwords funcionales del español que NUNCA deben hacer fuzzy match contra
# nombres de mpio/dpto. Razón: palabras como "cual" → "Cumbal" (ratio 0.80),
# "como" → "Cómbita", "para" → "Parménides", causan falsos positivos.
_FUZZY_STOPWORDS: set[str] = {
    # Pronombres interrogativos y relativos
    "cual", "cuales", "como", "donde", "cuando", "porque", "para",
    "quien", "quienes",
    # Preposiciones y conjunciones largas (≥4 chars que entran al fuzzy)
    "entre", "sobre", "desde", "hacia", "hasta", "contra", "segun",
    "ante", "bajo", "tras", "durante", "mediante",
    # Cuantificadores y comparativos
    "mucho", "muchos", "mucha", "muchas", "menos", "mayor", "menor",
    "mayores", "menores", "alta", "alto", "altas", "altos",
    "baja", "bajo", "bajas", "bajos", "mejor", "mejores", "peor",
    "peores", "maxima", "maximo", "minima", "minimo",
    # Verbos comunes en preguntas
    "tiene", "tienen", "registra", "registran", "presenta", "presentan",
    "hace", "hacen", "posee", "poseen", "reporta", "reportan",
    "muestra", "muestran", "exhibe", "exhiben", "puede", "pueden",
    # Sustantivos genéricos
    "datos", "dato", "informacion", "estadistica", "estadisticas",
    "cifra", "cifras", "tasa", "tasas", "indice", "indices",
    "numero", "numeros", "cantidad", "cantidades", "total", "totales",
    "departamento", "departamentos", "municipio", "municipios",
    "ciudad", "ciudades", "region", "regiones", "territorio",
    "territorios", "pais", "paises", "zona", "zonas",
    # Conectores temporales
    "antes", "despues", "luego", "ahora", "siempre", "nunca",
    # Otros frecuentes
    "tambien", "ademas", "esta", "estos", "estas", "esto",
    "afectada", "afectado", "afectados", "afectadas",
}


@dataclass(frozen=True)
class GeoTarget:
    """Una entidad geográfica resuelta (dpto, mpio, o scope nacional)."""

    name: str
    code: str | None  # None solo para level="national"
    level: str  # "national" | "dpto" | "mpio"


@dataclass(frozen=True)
class GeoContext:
    """Contexto geográfico extraído de una pregunta.

    `targets` es la lista canónica de territorios mencionados (puede tener
    1-N entradas). Para retrocompat, las propiedades `dpto_code`, `dpto_name`,
    `mpio_code`, `mpio_name` devuelven el PRIMER target del tipo correspondiente.

    `comparison_mode`:
    - "vs": múltiples targets a comparar (A vs B vs C).
    - "ranking": top-N sobre `groupby`.
    - "vs_national": local target vs agregado nacional.
    - None: no es comparativa, comportamiento singular.

    `scope`:
    - "national": el usuario dijo "Colombia"/"nacional" y no nombra subnacional.
    - "subnational": al menos un target dpto o mpio.
    """

    targets: list[GeoTarget] = field(default_factory=list)
    comparison_mode: str | None = None
    groupby: str | None = None
    scope: str = "subnational"
    confidence: float = 1.0
    notes: list[str] = field(default_factory=list)
    # Top-N (solo cuando comparison_mode='ranking'). Default 5.
    top_n: int = 5

    # ------------------------------------------------------------
    # Accessors retrocompatibles
    # ------------------------------------------------------------

    @property
    def dpto_name(self) -> str | None:
        for t in self.targets:
            if t.level == "dpto":
                return t.name
        # Inferir el dpto padre desde el primer mpio.
        for t in self.targets:
            if t.level == "mpio" and t.code and len(t.code) == 5:
                return _DPTO_BY_CODE.get(t.code[:2])
        return None

    @property
    def dpto_code(self) -> str | None:
        for t in self.targets:
            if t.level == "dpto":
                return t.code
        for t in self.targets:
            if t.level == "mpio" and t.code and len(t.code) == 5:
                return t.code[:2]
        return None

    @property
    def mpio_name(self) -> str | None:
        for t in self.targets:
            if t.level == "mpio":
                return t.name
        return None

    @property
    def mpio_code(self) -> str | None:
        for t in self.targets:
            if t.level == "mpio":
                return t.code
        return None


# ----------------------------------------------------------------------
# Helpers de normalización
# ----------------------------------------------------------------------


def _normalize(text: str) -> str:
    """lowercase + sin tildes + sin puntuación; preserva espacios."""
    text = text.lower()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    # Quitar puntuación común
    text = re.sub(r"[.,;:!¡¿?\"'`]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Diccionarios pre-normalizados para matching exacto rápido.
def _build_lookups() -> tuple[dict[str, tuple[str, str]], dict[str, tuple[str, str, str]]]:
    """Devuelve dos dicts:
    - dpto_lookup[norm_name] = (canonical_name, code)
    - mpio_lookup[norm_name] = (canonical_name, mpio_code, dpto_code)
    """
    dpto: dict[str, tuple[str, str]] = {}
    for canonical, code, synonyms in DEPARTAMENTOS:
        dpto[_normalize(canonical)] = (canonical, code)
        for syn in synonyms:
            dpto[_normalize(syn)] = (canonical, code)

    mpio: dict[str, tuple[str, str, str]] = {}
    # Primero el catálogo completo DIVIPOLA (~1122 mpios extraídos de gdxc-w37w).
    for name, mcode, dcode in MUNICIPIOS_DIVIPOLA:
        key = _normalize(name)
        if key in _MPIO_BLACKLIST:
            continue
        mpio[key] = (name, mcode, dcode)
    # Alias coloquial: para nombres con patrón "X de Y" (ej. "San Andrés
    # de Tumaco" → "Tumaco") agregar el sufijo después de " de " como alias.
    # Refleja el uso cotidiano del ciudadano. Reglas:
    # - Solo si el alias no existe ya como mpio (no sobreescribimos un mpio real).
    # - Solo si el alias NO es nombre de un dpto (evita "Santa Fé de Antioquia"
    #   → "antioquia" choque con el dpto Antioquia).
    # - Mínimo 4 caracteres (evita aliases ultra-genéricos).
    for name, mcode, dcode in MUNICIPIOS_DIVIPOLA:
        key = _normalize(name)
        if key in _MPIO_BLACKLIST:
            continue
        if " de " not in key:
            continue
        _, _, after_de = key.partition(" de ")
        after_de = after_de.strip()
        if (
            after_de
            and len(after_de) >= 4
            and after_de not in mpio
            and after_de not in dpto       # ← clave: no chocar con dptos
            and after_de not in _MPIO_BLACKLIST
        ):
            mpio[after_de] = (name, mcode, dcode)
    # CAPITALES sobreescribe si hay diferencias de nombre canónico.
    for name, mcode, dcode in CAPITALES:
        mpio[_normalize(name)] = (name, mcode, dcode)
    return dpto, mpio


_DPTO_LOOKUP, _MPIO_LOOKUP = _build_lookups()


# Mapeo dpto_code → canonical_name para poblar nombre al matchear solo mpio.
_DPTO_BY_CODE: dict[str, str] = {code: name for name, code, _ in DEPARTAMENTOS}


# ----------------------------------------------------------------------
# Detección de breakdown
# ----------------------------------------------------------------------

_BREAKDOWN_PATTERNS = (
    (re.compile(r"\bpor\s+municipios?\b", re.IGNORECASE), "cod_mpio"),
    (re.compile(r"\bpor\s+departamentos?\b", re.IGNORECASE), "cod_dpto"),
    (re.compile(r"\bpor\s+territorios?\b", re.IGNORECASE), "cod_dpto"),
    (re.compile(r"\bcada\s+departamento\b", re.IGNORECASE), "cod_dpto"),
    (re.compile(r"\bcada\s+municipio\b", re.IGNORECASE), "cod_mpio"),
)


def _detect_breakdown(question: str) -> str | None:
    for pattern, col in _BREAKDOWN_PATTERNS:
        if pattern.search(question):
            return col
    return None


# ----------------------------------------------------------------------
# Detección de plurales genéricos (regla anti-capital)
# ----------------------------------------------------------------------

_PLURAL_GENERIC_RE = re.compile(
    r"\b(municipios|departamentos|territorios|regiones)\b", re.IGNORECASE
)


def _has_plural_generic(question: str) -> bool:
    """¿La pregunta menciona 'municipios'/'departamentos' en plural genérico?"""
    return bool(_PLURAL_GENERIC_RE.search(question))


# ----------------------------------------------------------------------
# Detección de scope nacional
# ----------------------------------------------------------------------

_NATIONAL_PATTERNS = (
    re.compile(r"\b(colombia|colombiana?o?s?|nacional|nacionales|del pais|en el pais)\b", re.IGNORECASE),
)


def _is_national(question: str) -> bool:
    return any(p.search(question) for p in _NATIONAL_PATTERNS)


# ----------------------------------------------------------------------
# Detección de comparison_mode
# ----------------------------------------------------------------------

_VS_PATTERN = re.compile(
    r"\b(vs|versus|comparad?[oa]?s?|compara|frente a|contra)\b", re.IGNORECASE
)
_AND_BETWEEN_TARGETS = re.compile(r"\b(\w[\w\s]+?)\s+y\s+(\w[\w\s]+?)\b", re.IGNORECASE)
_RANKING_PATTERN = re.compile(
    r"\b(top\s+\d+|los?\s+\d+\s+(mejores|peores|m[áa]s|menos)|ranking)\b", re.IGNORECASE
)
_RANKING_N_RE = re.compile(r"\btop\s+(\d+)\b|\blos?\s+(\d+)\s+", re.IGNORECASE)

# Ranking IMPLÍCITO (PROD_IMPROV #4): patrones del lenguaje cotidiano del
# ciudadano que piden ordenamiento sin decir "top N" o "ranking".
# Captura "(qué|cuál) ... X ... (más|mayor|máxima|alta|...)" con cualquier
# contenido entre el interrogativo y el cuantificador (max 60 chars para
# evitar matches absurdos a través de oraciones).
# Ejemplos cubiertos:
#   "qué departamento tiene más universidades"
#   "cuál es la ciudad más afectada por homicidios"
#   "cuál municipio tiene la tasa más alta de dengue"
#   "qué región presenta mayor inversión social"
_IMPLICIT_RANKING_PATTERN = re.compile(
    r"\b(qu[eé]|cu[aá]l(?:es)?)\b"
    r"[^.?!]{0,60}?"  # no greedy hasta encontrar cuantificador
    r"\b(m[áa]s|menos|mayor(?:es)?|menor(?:es)?|"
    r"m[áa]xim[oa]s?|m[íi]nim[oa]s?|"
    r"alta|alto|altas|altos|baja|bajo|bajas|bajos|"
    r"mejor(?:es)?|peor(?:es)?)\b",
    re.IGNORECASE,
)
_VS_NATIONAL_PATTERN = re.compile(
    r"\b(respecto al? (promedio )?(nacional|colombia)|comparad[oa]\s+con\s+(colombia|el pais)|"
    r"versus (el)? nacional|frente al nacional)\b",
    re.IGNORECASE,
)

# Count-in: pregunta de conteo simple SOBRE un territorio específico.
# Ejemplos: "cuántos municipios tiene Antioquia", "cuántos hospitales hay en
# Medellín", "qué cantidad de casos registra Cundinamarca".
# Activa plantilla SoQL determinista `SELECT count(*) WHERE cod_dpto/mpio = X`.
_COUNT_IN_PATTERN = re.compile(
    r"\b(cu[áa]nt[oa]s?|qu[eé]\s+cantidad\s+de|n[uú]mero\s+de|"
    r"total\s+de|cantidad\s+de)\b",
    re.IGNORECASE,
)


def _detect_ranking_n(question: str, default: int = 5) -> int:
    m = _RANKING_N_RE.search(question)
    if m:
        for grp in m.groups():
            if grp and grp.isdigit():
                return max(1, min(50, int(grp)))
    return default


# ----------------------------------------------------------------------
# Detección de territorio (dpto / mpio)
# ----------------------------------------------------------------------


def _dedup_overlapping(spans: list[tuple[int, int, tuple]]) -> list[tuple]:
    """Dado [(start, end, payload), ...], descarta los rangos contenidos en otros más largos.

    Ej.: "valle del cauca" (start=0, end=15) y "cauca" (start=10, end=15) →
    se conserva el más largo. Devuelve solo los payloads en orden de start.
    """
    spans_sorted = sorted(spans, key=lambda s: (s[0], -(s[1] - s[0])))
    kept: list[tuple[int, int, tuple]] = []
    for start, end, payload in spans_sorted:
        # Si este rango está completamente dentro de un kept previo, descartar.
        if any(k_start <= start and end <= k_end for k_start, k_end, _ in kept):
            continue
        kept.append((start, end, payload))
    kept.sort(key=lambda s: s[0])
    return [p for _, _, p in kept]


def _find_dpto(norm_text: str) -> list[tuple[str, str, float]]:
    """Devuelve lista (canonical_name, dpto_code, confidence) ordenada por posición."""
    spans: list[tuple[int, int, tuple]] = []
    for key, (canonical, code) in _DPTO_LOOKUP.items():
        for m in re.finditer(rf"\b{re.escape(key)}\b", norm_text):
            spans.append((m.start(), m.end(), (canonical, code, 1.0)))
    return _dedup_overlapping(spans)


def _find_mpio(norm_text: str) -> list[tuple[str, str, str, float]]:
    """Devuelve lista (canonical_name, mpio_code, dpto_code, confidence)."""
    spans: list[tuple[int, int, tuple]] = []
    for key, (canonical, mcode, dcode) in _MPIO_LOOKUP.items():
        for m in re.finditer(rf"\b{re.escape(key)}\b", norm_text):
            spans.append((m.start(), m.end(), (canonical, mcode, dcode, 1.0)))
    return _dedup_overlapping(spans)


def _fuzzy_match_token(token: str, candidates: list[str], cutoff: float = 0.78) -> str | None:
    """Fuzzy match con difflib. Devuelve el mejor candidato si supera cutoff.

    Cutoff 0.78 calibrado para tolerar typos simples (ej. 'medeyin' → 'medellin'
    con ratio 0.8) sin introducir falsos positivos. Países extranjeros se filtran
    antes con la lista `PAISES_EXTRANJEROS`.
    """
    if not token or len(token) < 4:
        return None
    found = difflib.get_close_matches(token, candidates, n=1, cutoff=cutoff)
    return found[0] if found else None


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------


class GeoResolver:
    """Resolver geográfico para preguntas sobre territorios colombianos.

    Uso:
        ctx = GeoResolver().resolve("¿Cuántos municipios tiene Antioquia?")
        if ctx is not None:
            ...  # aplicar boost o filtro
    """

    def resolve(self, question: str) -> GeoContext | None:
        if not question or not question.strip():
            return None

        norm = _normalize(question)

        # Protección anti falso positivo: si nombra un país extranjero
        # y NO menciona Colombia, retornar None (caso adversarial Ecuador).
        if any(p in norm.split() for p in PAISES_EXTRANJEROS) and not _is_national(question):
            return None

        groupby = _detect_breakdown(question)
        national = _is_national(question)
        plural_generic = _has_plural_generic(question)
        comparison_mode, top_n = self._detect_comparison_mode(question, groupby)

        # Si es ranking pero no hay groupby explícito, derivar de la palabra
        # geográfica mencionada (plural o singular en ranking implícito).
        # Convenciones es-CO:
        #   - ciudad/ciudades   → cod_mpio
        #   - municipio/s       → cod_mpio
        #   - departamento/s    → cod_dpto
        #   - territorio/s      → cod_dpto
        #   - región/regiones   → cod_dpto (más cercano semánticamente a dpto)
        if comparison_mode == "ranking" and not groupby:
            ql = question.lower()
            # Detectar primero mpio (más específico) antes que dpto.
            mpio_singular = re.search(r"\b(municipio|ciudad)\b", ql)
            mpio_plural = re.search(r"\b(municipios|ciudades)\b", ql)
            dpto_singular = re.search(r"\b(departamento|territorio|regi[oó]n)\b", ql)
            dpto_plural = re.search(r"\b(departamentos|territorios|regiones)\b", ql)
            if mpio_plural or mpio_singular:
                groupby = "cod_mpio"
            elif dpto_plural or dpto_singular:
                groupby = "cod_dpto"

        # Mpio antes que dpto: si dice "Medellín" preferimos el mpio específico.
        mpio_hits = _find_mpio(norm)
        dpto_hits = _find_dpto(norm)

        # Fuzzy fallback si no hay match exacto pero hay tokens largos.
        # Si la pregunta es nacional (menciona Colombia), NO hacer fuzzy:
        # palabras como "colombia" matchean falsamente con "Cómbita" (mpio Boyacá).
        if not mpio_hits and not dpto_hits and not national:
            mpio_hits, dpto_hits = self._fuzzy_search(norm)

        # REGLA ANTI-CAPITAL (fix P1 2026-05-18):
        # Si la pregunta usa plural genérico ('municipios', 'departamentos')
        # Y NO menciona explícitamente el nombre del municipio capital,
        # descartar matches de mpio que sean capitales del dpto mencionado.
        if plural_generic and dpto_hits:
            dpto_codes_named = {h[1] for h in dpto_hits}
            mpio_hits = [
                m for m in mpio_hits
                if not (m[2] in dpto_codes_named and self._is_capital(m[0], m[2]))
            ]

        # Si no hay nada geográfico ni breakdown ni nacional → None.
        if not (mpio_hits or dpto_hits or groupby or national):
            return None

        # Construir lista de targets.
        targets: list[GeoTarget] = []
        notes: list[str] = []
        confidence = 1.0

        # Si comparison_mode = "vs", agregamos múltiples targets.
        # En modo singular, solo el primero.
        max_targets = 5 if comparison_mode == "vs" else 1

        # Mpios primero (más específicos).
        for m in mpio_hits[:max_targets]:
            name, mcode, _dcode, conf = m
            targets.append(GeoTarget(name=name, code=mcode, level="mpio"))
            confidence = min(confidence, conf)

        # Dptos: si ya hay mpios, agregamos solo los dptos NO incluidos como
        # padres de mpios. En vs mode, evitamos duplicados.
        included_dpto_codes = {
            self._dpto_of_mpio(t.code) for t in targets if t.level == "mpio"
        }
        for d in dpto_hits:
            if len(targets) >= max_targets:
                break
            name, code, conf = d
            if code in included_dpto_codes:
                continue
            targets.append(GeoTarget(name=name, code=code, level="dpto"))
            confidence = min(confidence, conf)

        # Notas para targets extras descartados.
        total_hits = len(mpio_hits) + len(dpto_hits)
        if total_hits > len(targets):
            notes.append(
                f"Detectados {total_hits} territorios; usando {len(targets)} principales."
            )

        # Scope: national si dijo "Colombia" y NO hay subnacionales o si plural+national.
        if national and not targets:
            scope = "national"
        elif national and plural_generic and not targets:
            scope = "national"
        elif national and not any(t.level in ("dpto", "mpio") for t in targets):
            scope = "national"
        else:
            scope = "subnational" if targets else "national"

        # En "vs_national", agregamos un target sintético nacional.
        if comparison_mode == "vs_national":
            targets.append(GeoTarget(name="Colombia", code=None, level="national"))

        # Promoción implícita a "vs": si no había mode explícito pero hay 2+
        # targets del mismo nivel, asumimos comparativa.
        if comparison_mode is None and self._detect_implicit_vs(targets):
            comparison_mode = "vs"

        # count_in requiere territorio subnacional concreto. Si no hay
        # ningún dpto o mpio resuelto, invalidamos count_in.
        if comparison_mode == "count_in":
            has_subnacional = any(t.level in ("dpto", "mpio") for t in targets)
            if not has_subnacional:
                comparison_mode = None

        # Fallback: si no hay nada útil, devolver None.
        if not targets and not groupby and not national and not comparison_mode:
            return None

        return GeoContext(
            targets=targets,
            comparison_mode=comparison_mode,
            groupby=groupby,
            scope=scope,
            confidence=confidence,
            notes=notes,
            top_n=top_n or 5,
        )

    # ------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------

    @staticmethod
    def _is_capital(mpio_name: str, dpto_code: str) -> bool:
        """True si `mpio_name` es la capital del dpto."""
        for name, _mcode, dcode in CAPITALES:
            if dcode == dpto_code and name == mpio_name:
                # Las capitales tienen código mpio terminado en '001'
                return True
        return False

    @staticmethod
    def _dpto_of_mpio(mpio_code: str | None) -> str | None:
        """Devuelve el dpto_code padre dado un mpio_code (los primeros 2 dígitos)."""
        if mpio_code and len(mpio_code) == 5:
            return mpio_code[:2]
        return None

    @staticmethod
    def _detect_comparison_mode(
        question: str, groupby: str | None
    ) -> tuple[str | None, int]:
        """Devuelve (comparison_mode, top_n).

        - vs_national: explícitamente menciona promedio nacional / vs Colombia.
        - ranking: 'top N', 'los N más', 'ranking'.
        - vs: 'compara A y B', 'A vs B', 'A versus B'.
        """
        if _VS_NATIONAL_PATTERN.search(question):
            return "vs_national", 0
        if _RANKING_PATTERN.search(question):
            return "ranking", _detect_ranking_n(question)
        # Ranking implícito ("qué dpto tiene más X" / "cuál ciudad mayor Y")
        if _IMPLICIT_RANKING_PATTERN.search(question):
            # n=5 por default — ranking implícito sin número explícito
            return "ranking", 5
        # 'vs' requiere o token explícito (vs/versus/compara) o 2+ territorios separados por 'y'
        if _VS_PATTERN.search(question):
            return "vs", 0
        # Count-in: "cuántos X tiene Antioquia" — solo válido si HAY territorio
        # subnacional. La verificación de territorio se hace en `resolve()`
        # (mode='count_in' se invalida si no hay dpto ni mpio resuelto).
        if _COUNT_IN_PATTERN.search(question):
            return "count_in", 0
        # heurística: si hay ' y ' entre tokens largos podría ser comparación
        # (lo confirmamos cuando llegamos a contar territorios). Aquí lo detectamos.
        return None, 0

    @staticmethod
    def _detect_implicit_vs(targets: list[GeoTarget]) -> bool:
        """Si hay 2+ targets del mismo nivel, asume comparativa implícita."""
        if len(targets) < 2:
            return False
        levels = {t.level for t in targets}
        return len(levels) <= 2 and "national" not in levels

    def _fuzzy_search(self, norm_text: str) -> tuple[list, list]:
        """Búsqueda fuzzy token-a-token. Solo se invoca si no hubo match exacto.

        Excluye stopwords funcionales que producen falsos positivos
        (ej. "cual" → "Cumbal" ratio 0.80, "como" → "Cómbita").
        """
        # Filtrar tokens ≥4 chars Y NO stopwords
        tokens = [
            t for t in norm_text.split()
            if len(t) >= 4 and t not in _FUZZY_STOPWORDS
        ]
        mpio_hits: list[tuple[str, str, str, float]] = []
        dpto_hits: list[tuple[str, str, float]] = []

        mpio_keys = list(_MPIO_LOOKUP.keys())
        dpto_keys = list(_DPTO_LOOKUP.keys())

        for token in tokens:
            # Mpio fuzzy
            match = _fuzzy_match_token(token, mpio_keys, cutoff=0.78)
            if match:
                canonical, mcode, dcode = _MPIO_LOOKUP[match]
                ratio = difflib.SequenceMatcher(None, token, match).ratio()
                mpio_hits.append((canonical, mcode, dcode, ratio))
                continue
            # Dpto fuzzy
            match = _fuzzy_match_token(token, dpto_keys, cutoff=0.85)
            if match:
                canonical, code = _DPTO_LOOKUP[match]
                ratio = difflib.SequenceMatcher(None, token, match).ratio()
                dpto_hits.append((canonical, code, ratio))

        return mpio_hits, dpto_hits


# ----------------------------------------------------------------------
# Plantillas SoQL deterministas (Opción A — flujo comparativo)
# ----------------------------------------------------------------------


# Patrones de columna territorial en datos.gov.co (heterogéneo).
_DPTO_CODE_COLS = (
    "cod_dpto",
    "codigo_dpto",
    "codigo_departamento",
    "codigo_dane_departamento",
)
_DPTO_NAME_COLS = (
    "departamento",
    "depa_nombre",
    "depto",
    "nom_dpto",
    "departamento_hecho",
    "departamento_del_hecho_dane",
    "departamento_del_hecho",
)
_MPIO_CODE_COLS = (
    "cod_mpio",
    "codigo_mpio",
    "codigo_municipio",
    "codigo_dane_municipio",
)
_MPIO_NAME_COLS = (
    "municipio",
    "nom_mpio",
    "mpio_nombre",
    "municipio_hecho",
    "municipio_del_hecho_dane",
    "municipio_del_hecho",
    "nombremunicipio",
)


def _find_geo_column(columns: set[str], level: str) -> tuple[str | None, bool]:
    """Devuelve (column_name, is_code) o (None, False).

    Prioriza columnas de código (códigos DIVIPOLA) sobre nombre.
    `columns` debe estar en lowercase.
    """
    code_patterns = _DPTO_CODE_COLS if level == "dpto" else _MPIO_CODE_COLS
    name_patterns = _DPTO_NAME_COLS if level == "dpto" else _MPIO_NAME_COLS
    for p in code_patterns:
        if p in columns:
            return p, True
    for p in name_patterns:
        if p in columns:
            return p, False
    return None, False


def _name_variants(name: str) -> list[str]:
    """Devuelve variantes del nombre para matching case-insensitive sin tildes.

    Ej: 'Medellín' → ['medellin', 'medellín'].
    """
    if not name:
        return []
    bare = _normalize(name)  # lowercase + sin tildes
    return sorted({bare, name.lower()})


def build_comparison_soql(
    ctx: GeoContext | None,
    columns: set[str],
) -> str | None:
    """Construye SoQL determinista para comparativas, sin pasar por LLM.

    Soporta columnas-código (`cod_dpto`, `codigo_dane_departamento`) y
    columnas-nombre (`departamento`, `municipio`, `departamento_del_hecho_dane`).
    Para columnas-nombre usa `lower(col) IN (...)` con variantes sin tildes.

    Args:
        ctx: GeoContext con `comparison_mode` seteado.
        columns: nombres de columnas (lowercase) disponibles en el dataset.

    Returns:
        SoQL ejecutable o `None` si no aplica.
    """
    if ctx is None or ctx.comparison_mode is None:
        return None

    columns_lower = {c.lower() for c in columns}

    # Decidir nivel de la consulta: si los targets mpio están presentes y el
    # dataset tiene una columna mpio, preferir mpio. Si no, usar dpto.
    mpio_targets = [t for t in ctx.targets if t.level == "mpio"]
    dpto_targets = [t for t in ctx.targets if t.level == "dpto"]

    geo_col: str | None = None
    is_code = False
    targets_for_filter: list[GeoTarget] = []

    if mpio_targets:
        geo_col, is_code = _find_geo_column(columns_lower, "mpio")
        targets_for_filter = mpio_targets
    if not geo_col and dpto_targets:
        geo_col, is_code = _find_geo_column(columns_lower, "dpto")
        targets_for_filter = dpto_targets
    if not geo_col and ctx.comparison_mode == "ranking":
        # Ranking sin targets específicos: derivar de groupby o heurística.
        groupby = (ctx.groupby or "").lower()
        if groupby == "cod_mpio":
            geo_col, is_code = _find_geo_column(columns_lower, "mpio")
        elif groupby == "cod_dpto":
            geo_col, is_code = _find_geo_column(columns_lower, "dpto")
        if not geo_col:
            for level in ("dpto", "mpio"):
                geo_col, is_code = _find_geo_column(columns_lower, level)
                if geo_col:
                    break
    if not geo_col:
        return None

    # --- Construir WHERE ---
    def _build_in_clause(targets: list[GeoTarget]) -> str | None:
        if not targets:
            return None
        if is_code:
            codes = [t.code for t in targets if t.code]
            if not codes:
                return None
            in_list = ", ".join(f"'{c}'" for c in codes)
            return f"{geo_col} IN ({in_list})"
        # Columna-nombre: usar lower() + variantes sin tildes.
        variants: set[str] = set()
        for t in targets:
            variants.update(_name_variants(t.name))
        if not variants:
            return None
        in_list = ", ".join(f"'{v}'" for v in sorted(variants))
        return f"lower({geo_col}) IN ({in_list})"

    if ctx.comparison_mode == "vs":
        if len(targets_for_filter) < 2:
            return None
        where = _build_in_clause(targets_for_filter)
        if not where:
            return None
        return (
            f"SELECT {geo_col}, count(*) AS n "
            f"WHERE {where} "
            f"GROUP BY {geo_col} "
            f"ORDER BY n DESC"
        )

    if ctx.comparison_mode == "ranking":
        n = ctx.top_n or 5
        return (
            f"SELECT {geo_col}, count(*) AS n "
            f"GROUP BY {geo_col} "
            f"ORDER BY n DESC "
            f"LIMIT {n}"
        )

    if ctx.comparison_mode == "vs_national":
        # GROUP BY territorio sin WHERE — stats_computer compara el local
        # target contra el resto. Útil cuando hay un solo target subnacional.
        return (
            f"SELECT {geo_col}, count(*) AS n "
            f"GROUP BY {geo_col} "
            f"ORDER BY n DESC "
            f"LIMIT 50"
        )

    if ctx.comparison_mode == "count_in":
        # Count simple sobre un territorio específico.
        # "¿Cuántos municipios tiene Antioquia?" → WHERE cod_dpto='05'
        if not targets_for_filter:
            return None
        first_target = targets_for_filter[0]
        if is_code:
            if not first_target.code:
                return None
            return (
                f"SELECT count(*) AS n "
                f"WHERE {geo_col} = '{first_target.code}'"
            )
        # Columna-nombre: case-insensitive con variantes sin tildes.
        variants = _name_variants(first_target.name)
        if not variants:
            return None
        in_list = ", ".join(f"'{v}'" for v in sorted(set(variants)))
        return (
            f"SELECT count(*) AS n "
            f"WHERE lower({geo_col}) IN ({in_list})"
        )

    return None
