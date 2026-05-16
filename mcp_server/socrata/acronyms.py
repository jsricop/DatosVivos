"""Diccionario de acrónimos y tesauros del sector público colombiano.

Permite que `DiscoveryClient.search()` expanda automáticamente acrónimos
y formas coloquiales al nombre canónico antes de pegarle a Socrata. Esto
mejora la calidad de resultados cuando el ciudadano escribe con jerga
ministerial ("MinTIC", "MEN") en vez del nombre completo de la entidad.

Decisiones de diseño:
- `canonical`: nombre oficial EXACTO como aparece en `attribution` de
  datos.gov.co (extraído programáticamente del catálogo de 8.389 datasets).
- `aliases`: lista de variantes que la gente usa REALMENTE (siglas oficiales,
  abreviaciones, variantes con/sin acentos, nombres antiguos, tesauros).
- `category`: ministerio, departamento_administrativo, instituto, agencia,
  unidad, superintendencia, organismo_control, empresa_estado, otro.

Matching: case-insensitive con word-boundary regex que respeta caracteres
acentuados (evita falsos positivos tipo "ANI" dentro de "anillo").

Fuente principal: extracción automática del catálogo de datos.gov.co
(2026-05-16, 8.389 datasets). Complementado con tesauros y nombres
antiguos comunes (Colciencias→MinCiencias, Coldeportes→MinDeporte, etc.).
"""

from __future__ import annotations

import re
from typing import Final


def _entry(canonical: str, aliases: list[str], category: str) -> dict:
    return {"canonical": canonical, "aliases": aliases, "category": category}


# ============================================================
# Ministerios (canónicos exactos del catálogo)
# ============================================================
MINISTERIOS: Final[list[dict]] = [
    _entry(
        "Ministerio de Tecnologías de la Información y las Comunicaciones",
        [
            "MinTIC",
            "Min TIC",
            "Ministerio de las TIC",
            "Ministerio TIC",
            "Ministerio de tecnologías",
            "Min Tic",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Educación Nacional",
        [
            "MinEducación",
            "MinEducacion",
            "MEN",
            "Min Educación",
            "Ministerio de Educación",
            "Min Educacion",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Salud y Protección Social",
        ["MinSalud", "Min Salud", "Ministerio de Salud"],
        "ministerio",
    ),
    _entry(
        "Ministerio de Hacienda y Crédito Público",
        ["MinHacienda", "MHCP", "Min Hacienda", "Ministerio de Hacienda"],
        "ministerio",
    ),
    _entry(
        "Ministerio de Ambiente y Desarrollo Sostenible",
        ["MinAmbiente", "MADS", "Min Ambiente", "Ministerio de Ambiente"],
        "ministerio",
    ),
    _entry(
        "Ministerio de Defensa Nacional",
        ["MinDefensa", "Min Defensa", "Ministerio de Defensa"],
        "ministerio",
    ),
    _entry(
        "Ministerio del Interior",
        ["MinInterior", "Min Interior"],
        "ministerio",
    ),
    _entry(
        "Ministerio de Justicia y del derecho",  # canonical EXACTO del catálogo (con "del derecho" en minúscula)
        [
            "MinJusticia",
            "Min Justicia",
            "Ministerio de Justicia",
            "Ministerio de Justicia y del Derecho",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Agricultura y Desarrollo Rural",
        ["MinAgricultura", "MADR", "Min Agricultura", "Ministerio de Agricultura"],
        "ministerio",
    ),
    _entry(
        "Ministerio de Comercio, Industria y Turismo",
        ["MinCIT", "MinComercio", "Min Comercio", "Ministerio de Comercio"],
        "ministerio",
    ),
    _entry(
        "Ministerio del Trabajo",
        ["MinTrabajo", "Min Trabajo"],
        "ministerio",
    ),
    _entry(
        "Ministerio de Transporte",
        ["MinTransporte", "Min Transporte"],
        "ministerio",
    ),
    _entry(
        "Ministerio de Vivienda, Ciudad y Territorio",
        ["MinVivienda", "Min Vivienda", "Ministerio de Vivienda"],
        "ministerio",
    ),
    _entry(
        "Ministerio de Minas y Energía",
        [
            "MinMinas",
            "MinEnergía",
            "MME",
            "Min Minas",
            "Min Energía",
            "Ministerio de Minas",
            "Ministerio de Energía",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de las Culturas, las Artes y los Saberes",  # canonical actualizado del catálogo
        [
            "MinCultura",
            "Min Cultura",
            "Ministerio de Cultura",
            "Ministerio de Cultura, las Artes y los Saberes",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Ciencia, Tecnología e Innovación",
        [
            "MinCiencias",
            "MinCiencia",
            "Minciencias",
            "Min Ciencias",
            "Colciencias",
        ],  # nombre antiguo
        "ministerio",
    ),
    _entry(
        "Ministerio del Deporte",
        ["MinDeporte", "Min Deporte", "Coldeportes"],  # nombre antiguo
        "ministerio",
    ),
    _entry(
        "Ministerio de Igualdad y Equidad",
        ["MinIgualdad", "Min Igualdad"],
        "ministerio",
    ),
    _entry(
        "Ministerio de Relaciones Exteriores",
        [
            "MinExterior",
            "MinExteriores",
            "Cancillería",
            "Cancilleria",
            "Min Exteriores",
        ],  # Cancillería como tesauro común
        "ministerio",
    ),
]


# ============================================================
# Departamentos Administrativos
# ============================================================
DEPARTAMENTOS_ADMINISTRATIVOS: Final[list[dict]] = [
    _entry(
        "Departamento Administrativo Nacional de Estadísticas",  # plural EXACTO del catálogo
        [
            "DANE",
            "Dane",
            "Departamento Administrativo Nacional de Estadística",
        ],  # variante singular común
        "departamento_administrativo",
    ),
    _entry(
        "Departamento Nacional de Planeación",
        ["DNP"],
        "departamento_administrativo",
    ),
    _entry(
        "Departamento Administrativo de la Función Pública",
        ["DAFP", "Función Pública", "Funcion Publica"],
        "departamento_administrativo",
    ),
    _entry(
        "Departamento Administrativo para la Prosperidad Social",
        ["DPS", "Prosperidad Social"],
        "departamento_administrativo",
    ),
    _entry(
        "Departamento Administrativo de la Presidencia de La República",  # capitalización EXACTA del catálogo
        ["DAPRE", "Presidencia", "Departamento Administrativo de la Presidencia"],
        "departamento_administrativo",
    ),
    _entry(
        "Departamento Administrativo Dirección Nacional de Inteligencia",
        ["DNI"],
        "departamento_administrativo",
    ),
]


# ============================================================
# Institutos
# ============================================================
INSTITUTOS: Final[list[dict]] = [
    _entry(
        "Instituto Colombiano de Bienestar Familiar",
        ["ICBF", "Bienestar Familiar"],
        "instituto",
    ),
    _entry(
        "Instituto de Hidrología, Meteorología y Estudios Ambientales",
        ["IDEAM"],
        "instituto",
    ),
    _entry(
        "Instituto Nacional de Vigilancia de Medicamentos y Alimentos",
        ["INVIMA"],
        "instituto",
    ),
    _entry(
        "Instituto Nacional de Vías",
        ["INVÍAS", "INVIAS"],
        "instituto",
    ),
    _entry(
        "Instituto Colombiano para la Evaluación de la Educación",
        ["ICFES"],
        "instituto",
    ),
    _entry(
        "Instituto Nacional Penitenciario y Carcelario",
        ["INPEC"],
        "instituto",
    ),
    _entry(
        "Instituto Geográfico Agustín Codazzi",
        ["IGAC"],
        "instituto",
    ),
    _entry(
        "Instituto Colombiano Agropecuario",
        ["ICA"],
        "instituto",
    ),
    _entry(
        "Instituto Nacional de Salud",
        ["INS"],
        "instituto",
    ),
    _entry(
        "Instituto Nacional de Metrología",
        ["INM"],
        "instituto",
    ),
    _entry(
        "Instituto Nacional para Sordos",
        ["INSOR"],
        "instituto",
    ),
    _entry(
        "Instituto Nacional para Ciegos",
        ["INCI"],
        "instituto",
    ),
    _entry(
        "Instituto Colombiano de Crédito Educativo y Estudios Técnicos en el Exterior",
        ["ICETEX"],
        "instituto",
    ),
    _entry(
        "Instituto Colombiano de Antropología e Historia",
        ["ICANH"],
        "instituto",
    ),
    _entry(
        "Instituto de Casas Fiscales del Ejército",
        ["ICFE"],
        "instituto",
    ),
    _entry(
        "Instituto Financiero para el Desarrollo del Valle del Cauca",
        ["INFIVALLE"],
        "instituto",
    ),
]


# ============================================================
# Agencias
# ============================================================
AGENCIAS: Final[list[dict]] = [
    _entry(
        "Dirección de Impuestos y Aduanas Nacionales",
        ["DIAN", "Dian"],
        "agencia",
    ),
    _entry(
        "Dirección General de la Policía Nacional",
        ["DIPON", "Policía Nacional"],
        "agencia",
    ),
    _entry(
        "Agencia Nacional de Infraestructura",
        ["ANI"],  # Cuidado: word-boundary evita matchear 'anillo' / 'daniela'
        "agencia",
    ),
    _entry(
        "Agencia Nacional de Hidrocarburos",
        ["ANH"],
        "agencia",
    ),
    _entry(
        "Agencia Nacional de Minería",
        ["ANM"],
        "agencia",
    ),
    _entry(
        "Autoridad Nacional de Licencias Ambientales",
        ["ANLA"],
        "agencia",
    ),
    _entry(
        "Agencia Nacional de Tierras",
        ["ANT"],
        "agencia",
    ),
    _entry(
        "Agencia Nacional de Seguridad Vial",
        ["ANSV"],
        "agencia",
    ),
    _entry(
        "Agencia Nacional del Espectro",
        ["ANE"],
        "agencia",
    ),
    _entry(
        "Agencia Nacional Inmobiliaria Virgilio Barco Vargas",
        ["ANIM"],
        "agencia",
    ),
    _entry(
        "Agencia para la Reincorporación y la Normalización",
        ["ARN"],
        "agencia",
    ),
    _entry(
        "Agencia de Desarrollo Rural",
        ["ADR"],
        "agencia",
    ),
    _entry(
        "Agencia de Renovación del Territorio",
        ["ART"],
        "agencia",
    ),
    _entry(
        "Agencia Nacional de Contratación Pública - Colombia Compra Eficiente",
        ["Colombia Compra Eficiente", "ANCP", "Colombia Compra"],
        "agencia",
    ),
    _entry(
        "Autoridad Nacional de Acuicultura y Pesca",
        ["AUNAP"],
        "agencia",
    ),
    _entry(
        "Corporación Agencia Nacional de Gobierno Digital",
        ["AND"],
        "agencia",
    ),
]


# ============================================================
# Unidades Administrativas Especiales
# ============================================================
UNIDADES: Final[list[dict]] = [
    _entry(
        "Unidad de Planificación de Tierras Rurales, Adecuación de Tierras y Usos Agropecuarios",
        ["UPRA"],
        "unidad",
    ),
    _entry(
        "Unidad de Planeación Minero Energética",
        ["UPME"],
        "unidad",
    ),
    _entry(
        "Unidad Nacional para la Gestión del Riesgo de desastres",  # canonical EXACTO (minúscula)
        [
            "UNGRD",
            "Unidad de Gestión del Riesgo",
            "Unidad Nacional para la Gestión del Riesgo de Desastres",
        ],  # capitalizado común
        "unidad",
    ),
    _entry(
        "Unidad Administrativa Especial de Gestión de Restitución de Tierras despojadas",
        ["URT", "Unidad de Restitución de Tierras"],
        "unidad",
    ),
    _entry(
        "Unidad Nacional de Protección",
        ["UNP"],
        "unidad",
    ),
    _entry(
        "Unidad de Servicios Penitenciarios y Carcelarios",
        ["USPEC"],
        "unidad",
    ),
    _entry(
        "Unidad Administrativa Especial de Gestión Pensional y Contribuciones Parafiscales",
        ["UGPP"],
        "unidad",
    ),
    _entry(
        "Unidad Administrativa Especial de Aeronáutica Civil",
        ["AEROCIVIL", "Aeronáutica Civil"],
        "unidad",
    ),
    _entry(
        "Unidad de Proyección Normativa y Estudios de Regulación Financiera",
        ["URF"],
        "unidad",
    ),
    _entry(
        "Unidad Administrativa Especial para la Atención y Reparación Integral a las Víctimas",
        ["UARIV", "Unidad de Víctimas", "Unidad para las Víctimas"],
        "unidad",
    ),
    _entry(
        "Unidad Administrativa Especial Junta Central de Contadores",
        ["JCC"],
        "unidad",
    ),
]


# ============================================================
# Superintendencias
# ============================================================
SUPERINTENDENCIAS: Final[list[dict]] = [
    _entry(
        "Superintendencia Financiera de Colombia",
        ["SUPERFINANCIERA", "SuperFinanciera", "Super Financiera"],
        "superintendencia",
    ),
    _entry(
        "Superintendencia de Servicios Públicos Domiciliarios",
        ["SUPERSERVICIOS", "SuperServicios", "SSPD", "Super Servicios"],
        "superintendencia",
    ),
    _entry(
        "Superintendencia Nacional de Salud",
        ["SUPERSALUD", "SuperSalud", "Super Salud"],
        "superintendencia",
    ),
    _entry(
        "Superintendencia de Industria y Comercio",
        ["SIC"],
        "superintendencia",
    ),
    _entry(
        "Superintendencia de Transporte",
        ["SUPERTRANSPORTE", "SuperTransporte"],
        "superintendencia",
    ),
    _entry(
        "Superintendencia del Subsidio Familiar",
        ["SUPERSUBSIDIO", "SuperSubsidio"],
        "superintendencia",
    ),
    _entry(
        "Superintendencia de la Economía Solidaria",
        ["SUPERSOLIDARIA"],
        "superintendencia",
    ),
    _entry(
        "Superintendencia de Notariado y Registro",
        ["SuperNotariado", "SNR"],
        "superintendencia",
    ),
]


# ============================================================
# Organismos de Control
# ============================================================
ORGANISMOS_CONTROL: Final[list[dict]] = [
    _entry(
        "Procuraduría General de la Nación",
        ["PGN", "Procuraduría"],
        "organismo_control",
    ),
    _entry(
        "Contraloría General de la República",
        ["CGR", "Contraloría"],
        "organismo_control",
    ),
    _entry(
        "Defensoría del Pueblo",
        ["Defensoría"],
        "organismo_control",
    ),
    _entry(
        "Fiscalía General de la Nación",
        ["Fiscalía", "FGN"],
        "organismo_control",
    ),
    _entry(
        "Auditoría General de la República",
        ["Auditoría", "AGR"],
        "organismo_control",
    ),
    _entry(
        "Jurisdicción Especial para la Paz",
        ["JEP"],
        "organismo_control",
    ),
]


# ============================================================
# Otros: empresas del Estado, fondos, comisiones
# ============================================================
OTROS: Final[list[dict]] = [
    _entry(
        "Servicio Nacional de Aprendizaje",
        ["SENA"],
        "otro",
    ),
    _entry(
        "Escuela Superior de Administración Pública",
        ["ESAP"],
        "otro",
    ),
    _entry(
        "Comisión Nacional del Servicio Civil",
        ["CNSC"],
        "otro",
    ),
    _entry(
        "Comisión de Regulación de Energía y Gas",
        ["CREG"],
        "otro",
    ),
    _entry(
        "Comisión de Regulación de Agua Potable y Saneamiento Básico",
        ["CRA"],
        "otro",
    ),
    _entry(
        "Servicio Geológico Colombiano",
        ["SGC"],
        "otro",
    ),
    _entry(
        "Archivo General de la Nación",
        ["AGN"],
        "otro",
    ),
    _entry(
        "Sistema Nacional de Información Cultural",
        ["SINIC"],
        "otro",
    ),
    _entry(
        "Centro de Memoria Histórica",
        ["Memoria Histórica", "CNMH"],
        "otro",
    ),
    _entry(
        "Consejo Nacional Electoral",
        ["CNE"],
        "otro",
    ),
    _entry(
        "Registraduría Nacional del Estado Civil",
        ["Registraduría", "RNEC"],
        "otro",
    ),
    _entry(
        "Sociedad de Radio Televisión Nacional de Colombia",
        ["RTVC"],
        "otro",
    ),
    _entry(
        "Administradora de los Recursos del Sistema General de Seguridad Social en Salud",
        ["ADRES"],
        "otro",
    ),
    _entry(
        "Corporación Colombiana de Investigación Agropecuaria",
        ["AGROSAVIA"],
        "otro",
    ),
    _entry(
        "Federación Colombiana de Municipios",
        ["FCM"],
        "otro",
    ),
    _entry(
        "Empresa Colombiana de Petróleos",
        ["Ecopetrol", "ECOPETROL"],
        "empresa_estado",
    ),
    _entry(
        "Interconexión Eléctrica S.A.",
        ["ISA"],
        "empresa_estado",
    ),
    _entry(
        "E.S.P. Empresas Públicas de Medellín",
        ["EPM", "Empresas Públicas de Medellín"],
        "empresa_estado",
    ),
    _entry(
        "Fondo Nacional del Ahorro",
        ["FNA"],
        "empresa_estado",
    ),
    _entry(
        "Fondo Nacional de Garantías",
        ["FNG"],
        "empresa_estado",
    ),
    _entry(
        "Fondo para el Financiamiento del Sector Agropecuario",
        ["FINAGRO"],
        "empresa_estado",
    ),
    _entry(
        "Financiera de Desarrollo Territorial S.A.",
        ["FINDETER"],
        "empresa_estado",
    ),
    _entry(
        "Financiera de Desarrollo Nacional",
        ["FDN"],
        "empresa_estado",
    ),
    _entry(
        "Administradora Colombiana de Pensiones",
        ["COLPENSIONES"],
        "empresa_estado",
    ),
    _entry(
        "Administradora del Monopolio Rentístico de los Juegos de Suerte y Azar",
        ["COLJUEGOS"],
        "empresa_estado",
    ),
    _entry(
        "Sociedad Fiduciaria de Desarrollo Agropecuario",
        ["FIDUAGRARIA"],
        "empresa_estado",
    ),
    _entry(
        "Sociedad de Activos Especiales S.A.S.",
        ["SAE"],
        "empresa_estado",
    ),
    _entry(
        "Servicio Aéreo A Territorios Nacionales",
        ["SATENA"],
        "empresa_estado",
    ),
    _entry(
        "Caja de Retiro de las Fuerzas Armadas",
        ["CREMIL"],
        "otro",
    ),
    _entry(
        "Caja de Sueldos de Retiro de la Policía Nacional",
        ["CASUR"],
        "otro",
    ),
    _entry(
        "Fondo de Previsión Social del Congreso de la República",
        ["FONPRECON"],
        "otro",
    ),
    _entry(
        "Fondo de Garantías de Entidades Cooperativas",
        ["FOGACOOP"],
        "otro",
    ),
    _entry(
        "Fondo de Desarrollo de la Educación Superior",
        ["FODESEP"],
        "otro",
    ),
    _entry(
        "Consejo Profesional Nacional de Ingeniería",
        ["COPNIA"],
        "otro",
    ),
    _entry(
        "Consejo Profesional de Administración de Empresas",
        ["CPAE"],
        "otro",
    ),
]


# ============================================================
# Lista consolidada
# ============================================================
ENTITIES: Final[list[dict]] = (
    MINISTERIOS
    + DEPARTAMENTOS_ADMINISTRATIVOS
    + INSTITUTOS
    + AGENCIAS
    + UNIDADES
    + SUPERINTENDENCIAS
    + ORGANISMOS_CONTROL
    + OTROS
)


def _build_alias_lookup() -> list[tuple[re.Pattern, str]]:
    """Compila patrones regex case-insensitive con word boundaries unicode-aware.

    Ordena por longitud descendente del alias — así "Ministerio de las TIC"
    matchea antes que "TIC" sola y evitamos overlaps.
    """
    items: list[tuple[int, re.Pattern, str]] = []
    for entry in ENTITIES:
        canonical = entry["canonical"]
        for alias in entry["aliases"]:
            escaped = re.escape(alias)
            # Lookbehind/lookahead que excluye letras (incl. acentuadas) — así
            # "ANI" no matchea en "anillo" pero sí en "datos del ANI publicados".
            pattern = re.compile(
                rf"(?<![A-Za-zÁÉÍÓÚÜáéíóúüÑñ]){escaped}(?![A-Za-zÁÉÍÓÚÜáéíóúüÑñ])",
                re.IGNORECASE,
            )
            items.append((len(alias), pattern, canonical))
    items.sort(key=lambda t: -t[0])
    return [(p, c) for _, p, c in items]


_LOOKUP = _build_alias_lookup()


def expand_query(query: str) -> str:
    """Expande acrónimos en `query` appending el nombre canónico.

    Estrategia: append, no replace. Conservamos el texto original del usuario
    y agregamos los nombres canónicos detectados para que Socrata tenga más
    términos relevantes que matchear.

    Args:
        query: texto en lenguaje natural del usuario.

    Returns:
        `query` con nombres canónicos appended (si hubo matches), o `query`
        inalterado si no se detectó ningún acrónimo conocido.
    """
    if not query or not query.strip():
        return query

    found_canonicals: list[str] = []
    seen: set[str] = set()
    for pattern, canonical in _LOOKUP:
        if pattern.search(query) and canonical not in seen:
            found_canonicals.append(canonical)
            seen.add(canonical)

    if not found_canonicals:
        return query
    return query + " " + " ".join(found_canonicals)
