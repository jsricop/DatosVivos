"""Diccionario de acrónimos y tesauros del sector público colombiano.

Permite que `DiscoveryClient.search()` expanda automáticamente acrónimos
y formas coloquiales al nombre canónico antes de pegarle a Socrata. Esto
mejora la calidad de resultados cuando el ciudadano escribe con jerga
ministerial ("MinTIC", "MEN") o formas descriptivas ("instituto del clima",
"pruebas Saber") en vez del nombre completo de la entidad.

Decisiones de diseño:
- `canonical`: nombre oficial EXACTO como aparece en `attribution` de
  datos.gov.co (extraído programáticamente del catálogo de 8.389 datasets).
- `aliases`: lista de variantes — sigla oficial, abreviaciones, variantes
  con/sin acentos, nombres antiguos, formas descriptivas, tesauros que la
  gente usa REALMENTE en redes / búsquedas / habla coloquial.
- `category`: ministerio, departamento_administrativo, instituto, agencia,
  unidad, superintendencia, organismo_control, empresa_estado, otro.

Matching: case-insensitive con word-boundary regex que respeta caracteres
acentuados (evita falsos positivos tipo "ANI" dentro de "anillo").

Cobertura: ≥3 aliases por entidad en al menos 90% del diccionario (verificado
en `test_acronyms_thesaurus_coverage_at_least_90_percent`).

Fuente principal: extracción automática del catálogo de datos.gov.co
(2026-05-16, 8.389 datasets). Tesauros complementarios derivados de
búsqueda web + conocimiento del dominio gubernamental colombiano.
"""

from __future__ import annotations

import re
from typing import Final


def _entry(canonical: str, aliases: list[str], category: str) -> dict:
    return {"canonical": canonical, "aliases": aliases, "category": category}


# ============================================================
# Ministerios
# ============================================================
MINISTERIOS: Final[list[dict]] = [
    _entry(
        "Ministerio de Tecnologías de la Información y las Comunicaciones",
        [
            "MinTIC", "Min TIC", "Min Tic",
            "Ministerio de las TIC", "Ministerio TIC",
            "Ministerio de tecnologías", "Ministerio de Tecnologías",
            "Ministerio TICs", "ministerio de comunicaciones",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Educación Nacional",
        [
            "MinEducación", "MinEducacion", "MEN",
            "Min Educación", "Min Educacion",
            "Ministerio de Educación", "Ministerio de Educacion",
            "Educación Nacional", "ministerio educación",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Salud y Protección Social",
        [
            "MinSalud", "Min Salud",
            "Ministerio de Salud", "Ministerio de la Salud",
            "Protección Social", "salud pública nacional",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Hacienda y Crédito Público",
        [
            "MinHacienda", "MHCP", "Min Hacienda",
            "Ministerio de Hacienda", "Hacienda Pública",
            "Crédito Público", "ministerio de finanzas",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Ambiente y Desarrollo Sostenible",
        [
            "MinAmbiente", "MADS", "Min Ambiente",
            "Ministerio de Ambiente", "Ministerio del Medio Ambiente",
            "Medio Ambiente", "Desarrollo Sostenible",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Defensa Nacional",
        [
            "MinDefensa", "Min Defensa",
            "Ministerio de Defensa", "Defensa Nacional",
            "Fuerzas Militares", "ministerio fuerzas armadas",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio del Interior",
        [
            "MinInterior", "Min Interior",
            "Ministerio del Interior", "Gobernación Nacional",
            "ministerio de gobierno",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Justicia y del derecho",
        [
            "MinJusticia", "Min Justicia",
            "Ministerio de Justicia", "Ministerio de Justicia y del Derecho",
            "Justicia y del Derecho",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Agricultura y Desarrollo Rural",
        [
            "MinAgricultura", "MADR", "Min Agricultura",
            "Ministerio de Agricultura", "Agricultura Nacional",
            "Desarrollo Rural", "ministerio agropecuario",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Comercio, Industria y Turismo",
        [
            "MinCIT", "MinComercio", "Min Comercio", "Min CIT",
            "Ministerio de Comercio", "Comercio Industria Turismo",
            "ministerio de turismo",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio del Trabajo",
        [
            "MinTrabajo", "Min Trabajo",
            "Ministerio del Trabajo", "Ministerio de Trabajo",
            "Trabajo Nacional",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Transporte",
        [
            "MinTransporte", "Min Transporte",
            "Ministerio de Transporte", "Transporte Nacional",
            "ministerio de movilidad",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Vivienda, Ciudad y Territorio",
        [
            "MinVivienda", "Min Vivienda",
            "Ministerio de Vivienda", "Vivienda Ciudad Territorio",
            "ministerio de ciudad",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Minas y Energía",
        [
            "MinMinas", "MinEnergía", "MME",
            "Min Minas", "Min Energía",
            "Ministerio de Minas", "Ministerio de Energía",
            "Minas y Energía",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de las Culturas, las Artes y los Saberes",
        [
            "MinCultura", "Min Cultura",
            "Ministerio de Cultura", "Ministerio de las Culturas",
            "Ministerio de Cultura, las Artes y los Saberes",
            "Cultura Nacional",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Ciencia, Tecnología e Innovación",
        [
            "MinCiencias", "MinCiencia", "Minciencias", "Min Ciencias",
            "Colciencias",  # nombre antiguo
            "Ministerio de Ciencias", "Ciencia y Tecnología",
            "Ciencia Tecnología e Innovación",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio del Deporte",
        [
            "MinDeporte", "Min Deporte",
            "Coldeportes",  # nombre antiguo
            "Ministerio del Deporte", "Ministerio de Deportes",
            "Deporte Nacional",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Igualdad y Equidad",
        [
            "MinIgualdad", "Min Igualdad",
            "Ministerio de Igualdad", "Igualdad y Equidad",
            "Ministerio de la Igualdad",
        ],
        "ministerio",
    ),
    _entry(
        "Ministerio de Relaciones Exteriores",
        [
            "MinExterior", "MinExteriores", "Min Exteriores",
            "Cancillería", "Cancilleria",
            "Ministerio de Exteriores", "Relaciones Exteriores",
        ],
        "ministerio",
    ),
]


# ============================================================
# Departamentos Administrativos
# ============================================================
DEPARTAMENTOS_ADMINISTRATIVOS: Final[list[dict]] = [
    _entry(
        "Departamento Administrativo Nacional de Estadísticas",
        [
            "DANE", "Dane",
            "Departamento Administrativo Nacional de Estadística",
            "Estadísticas Nacionales", "Estadística Nacional",
            "Censo Nacional",
        ],
        "departamento_administrativo",
    ),
    _entry(
        "Departamento Nacional de Planeación",
        [
            "DNP",
            "Planeación Nacional", "Departamento de Planeación",
            "Planeación del Estado",
        ],
        "departamento_administrativo",
    ),
    _entry(
        "Departamento Administrativo de la Función Pública",
        [
            "DAFP",
            "Función Pública", "Funcion Publica",
            "Departamento de Función Pública",
        ],
        "departamento_administrativo",
    ),
    _entry(
        "Departamento Administrativo para la Prosperidad Social",
        [
            "DPS",
            "Prosperidad Social", "Departamento de Prosperidad",
            "Prosperidad",
        ],
        "departamento_administrativo",
    ),
    _entry(
        "Departamento Administrativo de la Presidencia de La República",
        [
            "DAPRE",
            "Presidencia", "Casa de Nariño",
            "Departamento Administrativo de la Presidencia",
            "Presidencia de la República",
        ],
        "departamento_administrativo",
    ),
    _entry(
        "Departamento Administrativo Dirección Nacional de Inteligencia",
        [
            "DNI",
            "Dirección Nacional de Inteligencia", "Inteligencia Nacional",
            "Inteligencia del Estado",
        ],
        "departamento_administrativo",
    ),
]


# ============================================================
# Institutos
# ============================================================
INSTITUTOS: Final[list[dict]] = [
    _entry(
        "Instituto Colombiano de Bienestar Familiar",
        [
            "ICBF",
            "Bienestar Familiar", "Instituto de Bienestar",
            "Bienestar Familiar Colombia",
        ],
        "instituto",
    ),
    _entry(
        "Instituto de Hidrología, Meteorología y Estudios Ambientales",
        [
            "IDEAM",
            "Hidrología y Meteorología", "Meteorología Colombia",
            "instituto del clima", "instituto de meteorología",
            "Estudios Ambientales",
        ],
        "instituto",
    ),
    _entry(
        "Instituto Nacional de Vigilancia de Medicamentos y Alimentos",
        [
            "INVIMA",
            "Vigilancia de Medicamentos", "Control de Medicamentos",
            "Vigilancia Sanitaria", "control sanitario",
            "Medicamentos y Alimentos",
        ],
        "instituto",
    ),
    _entry(
        "Instituto Nacional de Vías",
        [
            "INVÍAS", "INVIAS",
            "Instituto de Vías", "Vías Nacionales",
            "Carreteras Nacionales", "infraestructura vial",
        ],
        "instituto",
    ),
    _entry(
        "Instituto Colombiano para la Evaluación de la Educación",
        [
            "ICFES",
            "Pruebas Saber", "exámenes de Estado",
            "examen ICFES", "Saber 11",
            "Evaluación de la Educación",
        ],
        "instituto",
    ),
    _entry(
        "Instituto Nacional Penitenciario y Carcelario",
        [
            "INPEC",
            "Sistema Penitenciario", "cárceles",
            "Penitenciario y Carcelario", "prisiones",
        ],
        "instituto",
    ),
    _entry(
        "Instituto Geográfico Agustín Codazzi",
        [
            "IGAC",
            "Agustín Codazzi", "Agustin Codazzi",
            "Catastro Nacional", "Instituto Geográfico",
            "cartografía nacional",
        ],
        "instituto",
    ),
    _entry(
        "Instituto Colombiano Agropecuario",
        [
            "ICA",
            "Instituto Agropecuario", "Control Agropecuario",
            "ICA Colombia", "Sanidad Agropecuaria",
        ],
        "instituto",
    ),
    _entry(
        "Instituto Nacional de Salud",
        [
            "INS",
            "Salud Pública Nacional", "Instituto de Salud",
            "INS Colombia", "Vigilancia Epidemiológica",
        ],
        "instituto",
    ),
    _entry(
        "Instituto Nacional de Metrología",
        [
            "INM",
            "Metrología Colombia", "Instituto de Metrología",
            "Metrología Nacional",
        ],
        "instituto",
    ),
    _entry(
        "Instituto Nacional para Sordos",
        [
            "INSOR",
            "Instituto para Sordos", "Discapacidad Auditiva",
            "personas sordas",
        ],
        "instituto",
    ),
    _entry(
        "Instituto Nacional para Ciegos",
        [
            "INCI",
            "Instituto para Ciegos", "Discapacidad Visual",
            "personas ciegas",
        ],
        "instituto",
    ),
    _entry(
        "Instituto Colombiano de Crédito Educativo y Estudios Técnicos en el Exterior",
        [
            "ICETEX",
            "Crédito Educativo", "Préstamos Educativos",
            "Becas ICETEX", "Crédito para Estudios",
        ],
        "instituto",
    ),
    _entry(
        "Instituto Colombiano de Antropología e Historia",
        [
            "ICANH",
            "Antropología e Historia", "Instituto de Antropología",
            "Antropología Colombia",
        ],
        "instituto",
    ),
    _entry(
        "Instituto de Casas Fiscales del Ejército",
        [
            "ICFE",
            "Casas Fiscales", "Vivienda del Ejército",
            "Casas Fiscales Ejército",
        ],
        "instituto",
    ),
    _entry(
        "Instituto Financiero para el Desarrollo del Valle del Cauca",
        [
            "INFIVALLE",
            "Instituto Financiero del Valle", "Desarrollo Valle del Cauca",
            "Financiero Valle",
        ],
        "instituto",
    ),
]


# ============================================================
# Agencias
# ============================================================
AGENCIAS: Final[list[dict]] = [
    _entry(
        "Dirección de Impuestos y Aduanas Nacionales",
        [
            "DIAN", "Dian",
            "Impuestos Nacionales", "Aduanas Nacionales",
            "Impuestos y Aduanas", "recaudo nacional",
        ],
        "agencia",
    ),
    _entry(
        "Dirección General de la Policía Nacional",
        [
            "DIPON",
            "Dirección de Policía", "Policía Nacional",
            "PONAL", "Dirección General Policía",
        ],
        "agencia",
    ),
    _entry(
        "Agencia Nacional de Infraestructura",
        [
            "ANI",
            "Agencia de Infraestructura", "Infraestructura Nacional",
            "Concesiones de Infraestructura",
        ],
        "agencia",
    ),
    _entry(
        "Agencia Nacional de Hidrocarburos",
        [
            "ANH",
            "Hidrocarburos Nacionales", "Agencia de Hidrocarburos",
            "Petróleo y Gas",
        ],
        "agencia",
    ),
    _entry(
        "Agencia Nacional de Minería",
        [
            "ANM",
            "Minería Nacional", "Agencia de Minería",
            "Títulos Mineros",
        ],
        "agencia",
    ),
    _entry(
        "Autoridad Nacional de Licencias Ambientales",
        [
            "ANLA",
            "Licencias Ambientales", "Autoridad Ambiental Nacional",
            "Permisos Ambientales",
        ],
        "agencia",
    ),
    _entry(
        "Agencia Nacional de Tierras",
        [
            "ANT",
            "Tierras Nacionales", "Agencia de Tierras",
            "Adjudicación de Tierras",
        ],
        "agencia",
    ),
    _entry(
        "Agencia Nacional de Seguridad Vial",
        [
            "ANSV",
            "Seguridad Vial", "Agencia Vial",
            "Tránsito Nacional",
        ],
        "agencia",
    ),
    _entry(
        "Agencia Nacional del Espectro",
        [
            "ANE",
            "Espectro Radioeléctrico", "Espectro Nacional",
            "Agencia del Espectro",
        ],
        "agencia",
    ),
    _entry(
        "Agencia Nacional Inmobiliaria Virgilio Barco Vargas",
        [
            "ANIM", "Virgilio Barco",
            "Inmobiliaria Nacional", "Agencia Inmobiliaria",
        ],
        "agencia",
    ),
    _entry(
        "Agencia para la Reincorporación y la Normalización",
        [
            "ARN",
            "Reincorporación y Normalización", "Agencia de Reincorporación",
            "Desmovilizados", "reintegración",
        ],
        "agencia",
    ),
    _entry(
        "Agencia de Desarrollo Rural",
        [
            "ADR",
            "Desarrollo Rural", "Agencia Rural",
            "Agencia Desarrollo Rural",
        ],
        "agencia",
    ),
    _entry(
        "Agencia de Renovación del Territorio",
        [
            "ART",
            "Renovación del Territorio", "Agencia de Renovación",
            "PDET", "Programas de Desarrollo con Enfoque Territorial",
        ],
        "agencia",
    ),
    _entry(
        "Agencia Nacional de Contratación Pública - Colombia Compra Eficiente",
        [
            "Colombia Compra Eficiente", "Colombia Compra",
            "ANCP", "Compra Eficiente",
            "Contratación Pública", "Agencia de Contratación",
        ],
        "agencia",
    ),
    _entry(
        "Autoridad Nacional de Acuicultura y Pesca",
        [
            "AUNAP",
            "Acuicultura y Pesca", "Autoridad de Pesca",
            "Pesca Nacional",
        ],
        "agencia",
    ),
    _entry(
        "Corporación Agencia Nacional de Gobierno Digital",
        [
            "AND",
            "Agencia de Gobierno Digital", "Gobierno Digital",
            "Agencia Digital Colombia",
        ],
        "agencia",
    ),
]


# ============================================================
# Unidades Administrativas Especiales
# ============================================================
UNIDADES: Final[list[dict]] = [
    _entry(
        "Unidad de Planificación de Tierras Rurales, Adecuación de Tierras y Usos Agropecuarios",
        [
            "UPRA",
            "Planificación Rural", "Tierras Rurales",
            "Usos Agropecuarios", "Planificación Agropecuaria",
        ],
        "unidad",
    ),
    _entry(
        "Unidad de Planeación Minero Energética",
        [
            "UPME",
            "Planeación Minero Energética", "Planeación Energética",
            "Planeación Minera",
        ],
        "unidad",
    ),
    _entry(
        "Unidad Nacional para la Gestión del Riesgo de desastres",
        [
            "UNGRD",
            "Gestión del Riesgo", "Riesgo de Desastres",
            "Gestión del Riesgo de Desastres", "Atención de Desastres",
            "Unidad Nacional para la Gestión del Riesgo de Desastres",
        ],
        "unidad",
    ),
    _entry(
        "Unidad Administrativa Especial de Gestión de Restitución de Tierras despojadas",
        [
            "URT",
            "Unidad de Restitución de Tierras", "Restitución de Tierras",
            "Tierras Despojadas", "Restitución Despojados",
        ],
        "unidad",
    ),
    _entry(
        "Unidad Nacional de Protección",
        [
            "UNP",
            "Protección de Personas", "Esquemas de Seguridad",
            "Unidad de Protección",
        ],
        "unidad",
    ),
    _entry(
        "Unidad de Servicios Penitenciarios y Carcelarios",
        [
            "USPEC",
            "Servicios Penitenciarios", "Infraestructura Penitenciaria",
            "Servicios Carcelarios",
        ],
        "unidad",
    ),
    _entry(
        "Unidad Administrativa Especial de Gestión Pensional y Contribuciones Parafiscales",
        [
            "UGPP",
            "Gestión Pensional", "Contribuciones Parafiscales",
            "Parafiscales", "Pensiones Parafiscales",
        ],
        "unidad",
    ),
    _entry(
        "Unidad Administrativa Especial de Aeronáutica Civil",
        [
            "AEROCIVIL",
            "Aeronáutica Civil", "Aviación Civil",
            "Aviación Colombia", "Aerocivil Colombia",
        ],
        "unidad",
    ),
    _entry(
        "Unidad de Proyección Normativa y Estudios de Regulación Financiera",
        [
            "URF",
            "Regulación Financiera", "Unidad Regulación Financiera",
            "Proyección Normativa Financiera",
        ],
        "unidad",
    ),
    _entry(
        "Unidad Administrativa Especial para la Atención y Reparación Integral a las Víctimas",
        [
            "UARIV", "Unidad de Víctimas", "Unidad para las Víctimas",
            "Atención a Víctimas", "Reparación a Víctimas",
            "Víctimas del Conflicto",
        ],
        "unidad",
    ),
    _entry(
        "Unidad Administrativa Especial Junta Central de Contadores",
        [
            "JCC",
            "Junta Central de Contadores", "Junta de Contadores",
            "Contadores Públicos Colombia",
        ],
        "unidad",
    ),
]


# ============================================================
# Superintendencias
# ============================================================
SUPERINTENDENCIAS: Final[list[dict]] = [
    _entry(
        "Superintendencia Financiera de Colombia",
        [
            "SUPERFINANCIERA", "SuperFinanciera", "Super Financiera",
            "Vigilancia Financiera", "Súper Financiera",
        ],
        "superintendencia",
    ),
    _entry(
        "Superintendencia de Servicios Públicos Domiciliarios",
        [
            "SUPERSERVICIOS", "SuperServicios", "SSPD", "Super Servicios",
            "Servicios Públicos Domiciliarios", "Vigilancia de Servicios Públicos",
        ],
        "superintendencia",
    ),
    _entry(
        "Superintendencia Nacional de Salud",
        [
            "SUPERSALUD", "SuperSalud", "Super Salud",
            "Vigilancia de Salud", "Súper Salud",
        ],
        "superintendencia",
    ),
    _entry(
        "Superintendencia de Industria y Comercio",
        [
            "SIC",
            "Industria y Comercio", "Súper de Industria",
            "Vigilancia Industria Comercio", "Protección al Consumidor",
        ],
        "superintendencia",
    ),
    _entry(
        "Superintendencia de Transporte",
        [
            "SUPERTRANSPORTE", "SuperTransporte", "Super Transporte",
            "Vigilancia de Transporte",
        ],
        "superintendencia",
    ),
    _entry(
        "Superintendencia del Subsidio Familiar",
        [
            "SUPERSUBSIDIO", "SuperSubsidio", "Super Subsidio",
            "Subsidio Familiar", "Vigilancia Subsidio Familiar",
        ],
        "superintendencia",
    ),
    _entry(
        "Superintendencia de la Economía Solidaria",
        [
            "SUPERSOLIDARIA",
            "Super Solidaria", "Economía Solidaria",
            "Vigilancia Economía Solidaria",
        ],
        "superintendencia",
    ),
    _entry(
        "Superintendencia de Notariado y Registro",
        [
            "SuperNotariado", "SNR", "Super Notariado",
            "Notariado y Registro", "Vigilancia de Notarías",
        ],
        "superintendencia",
    ),
]


# ============================================================
# Organismos de Control
# ============================================================
ORGANISMOS_CONTROL: Final[list[dict]] = [
    _entry(
        "Procuraduría General de la Nación",
        [
            "PGN", "Procuraduría", "Procurador General",
            "Procuraduría Nacional", "Procuraduria",
        ],
        "organismo_control",
    ),
    _entry(
        "Contraloría General de la República",
        [
            "CGR", "Contraloría", "Contralor General",
            "Contraloría Nacional", "Contraloria",
        ],
        "organismo_control",
    ),
    _entry(
        "Defensoría del Pueblo",
        [
            "Defensoría", "Defensor del Pueblo",
            "Defensoría Nacional", "Defensoria del Pueblo",
        ],
        "organismo_control",
    ),
    _entry(
        "Fiscalía General de la Nación",
        [
            "FGN", "Fiscalía", "Fiscal General",
            "Fiscalía Nacional", "Fiscalia General",
        ],
        "organismo_control",
    ),
    _entry(
        "Auditoría General de la República",
        [
            "AGR", "Auditoría", "Auditor General",
            "Auditoría Nacional",
        ],
        "organismo_control",
    ),
    _entry(
        "Jurisdicción Especial para la Paz",
        [
            "JEP",
            "Justicia Especial para la Paz", "Justicia Transicional",
            "Jurisdicción de Paz",
        ],
        "organismo_control",
    ),
]


# ============================================================
# Otros: empresas del Estado, fondos, comisiones, escuelas
# ============================================================
OTROS: Final[list[dict]] = [
    _entry(
        "Servicio Nacional de Aprendizaje",
        [
            "SENA",
            "Servicio de Aprendizaje", "Formación SENA",
            "Capacitación SENA", "el SENA",
        ],
        "otro",
    ),
    _entry(
        "Escuela Superior de Administración Pública",
        [
            "ESAP",
            "Escuela de Administración Pública", "Administración Pública",
            "Escuela Superior AP",
        ],
        "otro",
    ),
    _entry(
        "Comisión Nacional del Servicio Civil",
        [
            "CNSC",
            "Servicio Civil", "Comisión del Servicio Civil",
            "Concursos Públicos",
        ],
        "otro",
    ),
    _entry(
        "Comisión de Regulación de Energía y Gas",
        [
            "CREG",
            "Regulación de Energía", "Regulación de Gas",
            "Comisión Energía Gas",
        ],
        "otro",
    ),
    _entry(
        "Comisión de Regulación de Agua Potable y Saneamiento Básico",
        [
            "CRA",
            "Regulación de Agua", "Agua Potable",
            "Saneamiento Básico", "Comisión de Agua",
        ],
        "otro",
    ),
    _entry(
        "Servicio Geológico Colombiano",
        [
            "SGC",
            "Geológico Colombiano", "Servicio Geológico",
            "Geología Colombia",
        ],
        "otro",
    ),
    _entry(
        "Archivo General de la Nación",
        [
            "AGN",
            "Archivo Nacional", "Archivo de la Nación",
            "Archivo Histórico Nacional",
        ],
        "otro",
    ),
    _entry(
        "Sistema Nacional de Información Cultural",
        [
            "SINIC",
            "Información Cultural", "Sistema Cultural",
            "Cultura Colombia Sistema",
        ],
        "otro",
    ),
    _entry(
        "Centro de Memoria Histórica",
        [
            "Memoria Histórica", "CNMH",
            "Centro Nacional de Memoria",
            "Centro Memoria",
        ],
        "otro",
    ),
    _entry(
        "Consejo Nacional Electoral",
        [
            "CNE",
            "Consejo Electoral", "Electoral Nacional",
            "Tribunal Electoral",
        ],
        "otro",
    ),
    _entry(
        "Registraduría Nacional del Estado Civil",
        [
            "Registraduría", "RNEC",
            "Registraduria Nacional", "Cédulas Colombia",
            "Estado Civil",
        ],
        "otro",
    ),
    _entry(
        "Sociedad de Radio Televisión Nacional de Colombia",
        [
            "RTVC",
            "Radio Televisión Nacional", "Señal Colombia",
            "Radio Nacional",
        ],
        "otro",
    ),
    _entry(
        "Administradora de los Recursos del Sistema General de Seguridad Social en Salud",
        [
            "ADRES",
            "Recursos de Salud", "Recursos SGSSS",
            "Administradora de Salud",
        ],
        "otro",
    ),
    _entry(
        "Corporación Colombiana de Investigación Agropecuaria",
        [
            "AGROSAVIA",
            "Investigación Agropecuaria", "Corporación Agropecuaria",
            "I+D Agropecuaria",
        ],
        "otro",
    ),
    _entry(
        "Federación Colombiana de Municipios",
        [
            "FCM",
            "Federación de Municipios", "Municipios Colombia",
            "Federación Municipal",
        ],
        "otro",
    ),
    _entry(
        "Empresa Colombiana de Petróleos",
        [
            "Ecopetrol", "ECOPETROL",
            "Petróleos Colombia", "Empresa de Petróleos",
            "Petroleos Colombianos",
        ],
        "empresa_estado",
    ),
    _entry(
        "Interconexión Eléctrica S.A.",
        [
            "ISA",
            "Interconexión Eléctrica", "ISA Colombia",
            "Energía Eléctrica Interconexión",
        ],
        "empresa_estado",
    ),
    _entry(
        "E.S.P. Empresas Públicas de Medellín",
        [
            "EPM",
            "Empresas Públicas de Medellín", "EPM Medellín",
            "Servicios Públicos Medellín",
        ],
        "empresa_estado",
    ),
    _entry(
        "Fondo Nacional del Ahorro",
        [
            "FNA",
            "Fondo de Ahorro", "Ahorro Nacional",
            "Cesantías Nacionales",
        ],
        "empresa_estado",
    ),
    _entry(
        "Fondo Nacional de Garantías",
        [
            "FNG",
            "Garantías Nacionales", "Fondo de Garantías",
            "Garantías para Pymes",
        ],
        "empresa_estado",
    ),
    _entry(
        "Fondo para el Financiamiento del Sector Agropecuario",
        [
            "FINAGRO",
            "Financiamiento Agropecuario", "Fondo Agropecuario",
            "Crédito Agropecuario",
        ],
        "empresa_estado",
    ),
    _entry(
        "Financiera de Desarrollo Territorial S.A.",
        [
            "FINDETER",
            "Desarrollo Territorial", "Financiera Territorial",
            "Financiamiento Territorial",
        ],
        "empresa_estado",
    ),
    _entry(
        "Financiera de Desarrollo Nacional",
        [
            "FDN",
            "Desarrollo Nacional", "Financiera Nacional",
            "Financiamiento Nacional",
        ],
        "empresa_estado",
    ),
    _entry(
        "Administradora Colombiana de Pensiones",
        [
            "COLPENSIONES",
            "Pensiones Colombia", "Administradora de Pensiones",
            "Régimen de Prima Media",
        ],
        "empresa_estado",
    ),
    _entry(
        "Administradora del Monopolio Rentístico de los Juegos de Suerte y Azar",
        [
            "COLJUEGOS",
            "Juegos de Suerte y Azar", "Juegos de Azar",
            "Monopolio de Juegos", "Apuestas Nacionales",
        ],
        "empresa_estado",
    ),
    _entry(
        "Sociedad Fiduciaria de Desarrollo Agropecuario",
        [
            "FIDUAGRARIA",
            "Fiduciaria Agropecuaria", "Fiduagraria Colombia",
            "Fiduciaria Desarrollo Agropecuario",
        ],
        "empresa_estado",
    ),
    _entry(
        "Sociedad de Activos Especiales S.A.S.",
        [
            "SAE",
            "Activos Especiales", "Sociedad Activos",
            "Bienes Incautados",
        ],
        "empresa_estado",
    ),
    _entry(
        "Servicio Aéreo A Territorios Nacionales",
        [
            "SATENA",
            "Aerolínea estatal", "Servicio Aéreo",
            "SATENA Colombia",
        ],
        "empresa_estado",
    ),
    _entry(
        "Caja de Retiro de las Fuerzas Armadas",
        [
            "CREMIL",
            "Retiro Fuerzas Armadas", "Caja Retiro Militar",
            "Pensiones Militares",
        ],
        "otro",
    ),
    _entry(
        "Caja de Sueldos de Retiro de la Policía Nacional",
        [
            "CASUR",
            "Sueldos Retiro Policía", "Caja Policía",
            "Pensiones Policía",
        ],
        "otro",
    ),
    _entry(
        "Fondo de Previsión Social del Congreso de la República",
        [
            "FONPRECON",
            "Previsión Congreso", "Fondo Congreso",
            "Pensiones Congreso",
        ],
        "otro",
    ),
    _entry(
        "Fondo de Garantías de Entidades Cooperativas",
        [
            "FOGACOOP",
            "Garantías Cooperativas", "Fondo Cooperativas",
            "Garantías de Cooperativas",
        ],
        "otro",
    ),
    _entry(
        "Fondo de Desarrollo de la Educación Superior",
        [
            "FODESEP",
            "Desarrollo Educación Superior", "Fondo Educación Superior",
            "Crédito Educación Superior",
        ],
        "otro",
    ),
    _entry(
        "Consejo Profesional Nacional de Ingeniería",
        [
            "COPNIA",
            "Consejo de Ingeniería", "Profesional de Ingeniería",
            "Ingenieros Colombia",
        ],
        "otro",
    ),
    _entry(
        "Consejo Profesional de Administración de Empresas",
        [
            "CPAE",
            "Consejo de Administración de Empresas",
            "Profesional Administración", "Administradores de Empresas",
        ],
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
