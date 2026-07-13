"""Diccionario ciudadano ↔ institucional (solución transversal, 2026-07-13).

El ciudadano pregunta con SUS palabras ("colegios", "plata", "robos"); los
datos abiertos están titulados en lenguaje institucional ("establecimientos
educativos", "ejecución presupuestal", "hurto"). Este diccionario cierra esa
brecha de forma DETERMINISTA — versionado en git, testeable, sin LLM: el
prompt del mapper también expande vocabulario, pero esto garantiza el piso
aunque el LLM no lo haga.

Se aplica en `query_chips` (api/routes/chips.py): los términos oficiales se
suman al word-boost y al texto del re-ranking semántico. NO filtra ni
inventa — solo mejora el ORDEN de candidatos.

Curado manualmente desde el ciclo ciudadano de 50 preguntas
(eval/ciudadano/preguntas_50.yaml) y los dominios del catálogo. Convención:
claves en minúscula SIN tildes (el matching normaliza); las claves
multi-palabra se evalúan primero.
"""

from __future__ import annotations

import re

VOCABULARIO: dict[str, list[str]] = {
    # ---- Educación ----
    "colegios": ["establecimientos educativos", "instituciones educativas"],
    "colegio": ["establecimientos educativos", "instituciones educativas"],
    "escuelas": ["establecimientos educativos", "sedes educativas"],
    "guarderias": ["hogares comunitarios", "centros de desarrollo infantil"],
    "jardines infantiles": ["centros de desarrollo infantil", "primera infancia"],
    "cupos escolares": ["matricula", "cobertura educativa"],
    "profesores": ["docentes", "planta docente"],
    "maestros": ["docentes"],
    "universidades": ["instituciones de educacion superior", "IES"],
    "universidad": ["educacion superior"],
    "becas": ["creditos educativos", "ICETEX", "fondos condonables"],
    "desertaron": ["desercion escolar"],
    "desercion del colegio": ["desercion escolar"],
    "publicos": ["oficial"],
    "publicas": ["oficial"],
    "privados": ["no oficial"],
    "privadas": ["no oficial"],

    # ---- Salud ----
    "camas uci": ["capacidad instalada", "unidades de cuidado intensivo"],
    "hospitales": ["IPS", "instituciones prestadoras de salud", "prestadores"],
    "hospital": ["IPS", "prestadores de servicios de salud"],
    "puestos de salud": ["IPS", "sedes de prestadores"],
    "medicos": ["talento humano en salud", "profesionales de la salud"],
    "citas medicas": ["oportunidad de citas", "asignacion de citas"],
    "vacunas": ["vacunacion", "inmunizacion", "PAI"],
    "drogas": ["medicamentos", "sustancias psicoactivas"],
    "medicinas": ["medicamentos"],
    "embarazadas": ["gestantes", "control prenatal"],
    "salud mental": ["trastornos mentales", "intento de suicidio"],

    # ---- Seguridad y justicia ----
    "robos": ["hurto"],
    "robo": ["hurto"],
    "atracos": ["hurto a personas"],
    "asesinatos": ["homicidios"],
    "matan": ["homicidios"],
    "peleas": ["lesiones personales", "rinas"],
    "violencia en la casa": ["violencia intrafamiliar"],
    "maltrato": ["violencia intrafamiliar", "violencia de genero"],
    "pandillas": ["delitos", "convivencia"],
    "carcel": ["establecimientos de reclusion", "poblacion carcelaria", "INPEC"],
    "presos": ["poblacion privada de la libertad", "reclusos"],
    "demandas": ["procesos judiciales"],
    "peligrosos": ["delitos", "seguridad ciudadana"],
    "inseguridad": ["delitos", "convivencia y seguridad"],

    # ---- Economía, empleo y plata pública ----
    "plata": ["presupuesto", "recursos"],
    "gasta la plata": ["ejecucion presupuestal", "gastos de inversion"],
    "gastos": ["ejecucion presupuestal", "gasto publico"],
    "presupuesto de mi alcaldia": ["presupuesto municipal", "ejecucion presupuestal"],
    "deuda": ["deuda publica", "endeudamiento"],
    "impuestos": ["recaudo tributario", "predial", "industria y comercio"],
    "sueldo": ["salarios", "ingresos", "remuneracion"],
    "gana en promedio": ["salario promedio", "ingresos laborales"],
    "desempleo": ["tasa de desempleo", "mercado laboral"],
    "trabajo informal": ["informalidad laboral"],
    "empresas nuevas": ["sociedades constituidas", "registro mercantil"],
    "empresas": ["sociedades", "establecimientos de comercio"],
    "ayudas": ["subsidios", "transferencias monetarias"],
    "subsidios": ["transferencias monetarias", "familias en accion"],
    "contratos": ["contratacion publica", "SECOP"],
    "contratacion a dedo": ["contratacion directa"],
    "nomina": ["planta de personal", "empleos publicos"],
    "funcionarios": ["servidores publicos", "planta de personal"],
    "transferencias a mi municipio": ["sistema general de participaciones", "SGP"],
    "regalias": ["sistema general de regalias"],

    # ---- Transporte y movilidad ----
    "trancones": ["movilidad", "congestion vehicular"],
    "buses": ["transporte publico", "rutas"],
    "multas de transito": ["comparendos", "infracciones de transito"],
    "multas": ["comparendos", "sanciones"],
    "accidentes de transito": ["siniestros viales", "accidentalidad vial"],
    "carros": ["parque automotor", "vehiculos"],
    "motos": ["motocicletas", "parque automotor"],
    "pico y placa": ["restriccion vehicular"],
    "huecos": ["malla vial", "mantenimiento vial"],
    "vias": ["malla vial", "infraestructura vial"],

    # ---- Vivienda y servicios públicos ----
    "arriendo": ["canon de arrendamiento", "arrendamiento"],
    "casas": ["vivienda", "unidades habitacionales"],
    "vivienda gratis": ["vivienda de interes social", "vivienda gratuita"],
    "luz": ["energia electrica"],
    "agua": ["acueducto"],
    "alcantarillado": ["saneamiento basico"],
    "basura": ["residuos solidos", "aseo"],
    "recogen la basura": ["recoleccion de residuos", "aseo"],
    "internet": ["conectividad", "banda ancha", "acceso a internet"],
    "estrato": ["estratificacion socioeconomica"],

    # ---- Ambiente ----
    "contaminacion del aire": ["calidad del aire", "material particulado"],
    "contaminacion": ["calidad del aire", "calidad del agua"],
    "rios": ["recurso hidrico", "calidad del agua", "fuentes hidricas"],
    "arboles": ["arbolado urbano", "silvicultura"],
    "deforestacion": ["perdida de bosque", "cobertura boscosa"],
    "reciclaje": ["aprovechamiento de residuos", "residuos solidos"],
    "animales": ["fauna", "bienestar animal"],
    "mascotas": ["caninos y felinos", "bienestar animal"],
    "clima": ["precipitacion", "temperatura", "hidrometeorologia"],
    "inundaciones": ["gestion del riesgo", "eventos de emergencia"],
    "derrumbes": ["movimientos en masa", "gestion del riesgo"],

    # ---- Estado, trámites y participación ----
    "quejas": ["PQRS", "peticiones quejas y reclamos"],
    "tramites": ["tramites y servicios"],
    "corrupcion": ["sanciones disciplinarias", "transparencia"],
    "elecciones": ["resultados electorales", "votacion"],
    "votar": ["censo electoral", "puestos de votacion"],
    "personeria": ["ministerio publico"],

    # ---- Población ----
    "ninos": ["primera infancia", "menores de edad"],
    "jovenes": ["juventud", "adolescentes"],
    "viejitos": ["adulto mayor", "persona mayor"],
    "abuelos": ["adulto mayor"],
    "adultos mayores": ["persona mayor", "centro vida"],
    "discapacitados": ["personas con discapacidad"],
    "desplazados": ["victimas del conflicto", "desplazamiento forzado"],
    "victimas": ["victimas del conflicto armado"],
    "migrantes": ["poblacion migrante", "venezolanos"],
    "indigenas": ["pueblos indigenas", "resguardos"],
    "campesinos": ["poblacion rural", "agropecuario"],
    "habitantes de calle": ["habitante de calle"],

    # ---- Agro y alimentos ----
    "cultivos": ["produccion agricola", "area sembrada"],
    "cosechas": ["produccion agricola", "rendimiento"],
    "comida": ["seguridad alimentaria", "abastecimiento"],
    "precios de la comida": ["precios mayoristas", "SIPSA", "abastecimiento"],
    "ganado": ["inventario bovino", "pecuario"],

    # ---- Cultura, deporte y turismo ----
    "canchas": ["escenarios deportivos", "infraestructura deportiva"],
    "parques": ["espacio publico", "parques"],
    "bibliotecas": ["red de bibliotecas"],
    "turistas": ["visitantes", "turismo"],
    "conciertos": ["eventos culturales", "agenda cultural"],
}

# Claves multi-palabra primero (más específicas ganan): "camas uci" debe
# matchear antes que cualquier término suelto.
_CLAVES = sorted(VOCABULARIO, key=lambda k: -len(k.split()))

_TRANS = str.maketrans("áéíóúüñ", "aeiouun")


def _norm(s: str) -> str:
    return s.lower().translate(_TRANS)


def expandir(texto: str | None, max_terms: int = 6) -> str:
    """Términos OFICIALES equivalentes a las palabras ciudadanas de `texto`.

    Devuelve un string con los términos institucionales encontrados (sin
    repetir los que ya están en el texto), para sumarlos al word-boost y al
    embedding del re-ranking. Vacío si no hay matches.
    """
    if not texto:
        return ""
    q = f" {_norm(texto)} "
    out: list[str] = []
    for clave in _CLAVES:
        if len(out) >= max_terms:
            break
        if re.search(rf"(?<![a-z0-9]){re.escape(clave)}(?![a-z0-9])", q):
            for oficial in VOCABULARIO[clave]:
                if _norm(oficial) not in q and oficial not in out:
                    out.append(oficial)
                    if len(out) >= max_terms:
                        break
    return " ".join(out)
