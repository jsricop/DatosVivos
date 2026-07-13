#!/usr/bin/env python3
"""Genera recursos/presentacion.pptx — pitch DatosVivos, Datos al Ecosistema 2026.

12 diapositivas de pitch + 6 técnicas de respaldo. Identidad gov.co/DatosVivos:
azul institucional #004884, blanco, semáforo gov.co. Cifras = corte 2026-07-10.
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

AZUL = RGBColor(0x00, 0x48, 0x84)
AZUL2 = RGBColor(0x33, 0x66, 0xCC)
INK = RGBColor(0x20, 0x21, 0x24)
MUTED = RGBColor(0x5F, 0x63, 0x68)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)
CREMA = RGBColor(0xF4, 0xF6, 0xF9)
OK = RGBColor(0x06, 0x84, 0x60)
WARN = RGBColor(0xFF, 0xAB, 0x00)
BAD = RGBColor(0xC3, 0x2D, 0x4B)

W, H = Inches(13.333), Inches(7.5)
FONT = "Nunito Sans"
MONO = "IBM Plex Mono"

prs = Presentation()
prs.slide_width, prs.slide_height = W, H
BLANK = prs.slide_layouts[6]
N = [0]  # contador de página


def slide(bg=BLANCO):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = bg
    N[0] += 1
    return s


def box(s, x, y, w, h):
    tb = s.shapes.add_textbox(x, y, w, h)
    tb.text_frame.word_wrap = True
    return tb.text_frame


def para(tf, text, size, color=INK, bold=False, first=None, font=FONT,
         align=PP_ALIGN.LEFT, space_after=6):
    p = tf.paragraphs[0] if first is None and not tf.paragraphs[0].runs else tf.add_paragraph()
    if first is True:
        p = tf.paragraphs[0]
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.color.rgb = color
    r.font.bold = bold
    r.font.name = font
    p.alignment = align
    p.space_after = Pt(space_after)
    return p


def rect(s, x, y, w, h, color, line=False):
    from pptx.enum.shapes import MSO_SHAPE
    sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    if line:
        sh.line.color.rgb = AZUL
        sh.line.width = Pt(0.75)
    else:
        sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def footer(s, dark=False):
    tf = box(s, Inches(0.5), Inches(7.05), Inches(12.3), Inches(0.35))
    c = BLANCO if dark else MUTED
    para(tf, f"DatosVivos · datosvivos.co  —  Datos al Ecosistema 2026 · Equipo 93 · Reto 7 (id 102) · Nivel Avanzado        {N[0]:02d}",
         9, color=c, font=MONO)


def kicker_title(s, kicker, title, title_size=32, color=INK, kcolor=AZUL2):
    tf = box(s, Inches(0.6), Inches(0.45), Inches(12.1), Inches(1.7))
    para(tf, kicker.upper(), 12, color=kcolor, bold=True, font=MONO, first=True)
    para(tf, title, title_size, color=color, bold=True, space_after=0)


def bullets(s, items, x=Inches(0.65), y=Inches(2.0), w=Inches(12.0),
            h=Inches(4.7), size=17, gap=10):
    tf = box(s, x, y, w, h)
    for i, it in enumerate(items):
        if isinstance(it, tuple):
            head, body = it
            p = para(tf, head, size, color=AZUL, bold=True,
                     first=(i == 0), space_after=2)
            para(tf, body, size - 2, color=INK, space_after=gap)
        else:
            para(tf, "—  " + it, size, color=INK, first=(i == 0), space_after=gap)


def stat_cards(s, stats, y=Inches(2.1), card_h=Inches(1.9)):
    n = len(stats)
    gap = Inches(0.25)
    total_w = W - Inches(1.2)
    cw = Emu(int((total_w - gap * (n - 1)) / n))
    x = Inches(0.6)
    for i, (num, label, color) in enumerate(stats):
        r = rect(s, x, y, cw, card_h, CREMA)
        tf = r.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        para(tf, num, 30, color=color, bold=True, font=MONO,
             align=PP_ALIGN.CENTER, first=True, space_after=2)
        para(tf, label, 12, color=MUTED, align=PP_ALIGN.CENTER, space_after=0)
        x = Emu(int(x + cw + gap))


# ============================== PITCH ==============================

# 1 · Portada
s = slide(AZUL)
tf = box(s, Inches(0.9), Inches(2.0), Inches(11.5), Inches(3.4))
para(tf, "Datos|Vivos", 60, color=BLANCO, bold=True, font=MONO, first=True, space_after=4)
para(tf, "── el panorama de los datos abiertos de Colombia", 20, color=RGBColor(0xBF, 0xD4, 0xE8), font=MONO, space_after=18)
para(tf, "Datos del Estado, en tus palabras.", 26, color=BLANCO, bold=True)
tf2 = box(s, Inches(0.9), Inches(5.7), Inches(11.5), Inches(1.1))
para(tf2, "Concurso Datos al Ecosistema 2026: IA para Colombia — MinTIC", 15, color=BLANCO, first=True, space_after=2)
para(tf2, "Equipo 93 · Reto de Innovación y Tecnología (Reto 7, id 102) · Nivel Avanzado · GIT TIC — ANI", 13, color=RGBColor(0xBF, 0xD4, 0xE8), font=MONO)
footer(s, dark=True)

# 2 · El dolor
s = slide()
kicker_title(s, "El problema", "Nadie tiene el panorama")
bullets(s, [
    ("La entidad", "no sabe cuántos datasets tiene publicados ni cuántos están actualizados — la respuesta exige revisar el portal dataset por dataset."),
    ("El gerente de sector", "con N entidades adscritas no puede hacer control: no existe una vista consolidada de qué publica su sector ni con qué frescura."),
    ("El propio MinTIC", "carece de panorama: los portales federados (Bogotá, Cali, Medellín, Valle, IGAC) viven separados, con estándares distintos."),
    ("El ciudadano", "que quiere una cifra necesita saber de APIs, SQL o procesar archivos. El dato público existe, pero es inaccesible."),
])
footer(s)

# 3 · La tesis
s = slide(CREMA)
tf = box(s, Inches(1.2), Inches(2.5), Inches(11), Inches(2.6))
para(tf, "“Si no conocemos, no podemos medir.", 40, color=AZUL, bold=True, first=True, space_after=2)
para(tf, "Y si no medimos, no podemos mejorar.”", 40, color=AZUL, bold=True, space_after=16)
para(tf, "El dato bien gobernado es infraestructura — tan estratégica como las vías.", 18, color=INK)
footer(s)

# 4 · La solución: 3 niveles
s = slide()
kicker_title(s, "La solución", "DatosVivos: tres niveles, una sola fuente de verdad")
levels = [
    ("1 · INICIO", "Panorama nacional — datosvivos.co", "Cifras en vivo del ecosistema completo: cuántos datasets, quién publica, qué tan frescos, cómo se accede. Para decidir en segundos."),
    ("2 · DETALLE ENTIDAD", "/tablero (Power BI)", "El detalle explorable: filtros por sector, entidad, acceso y territorio. Para el control de gestión."),
    ("3 · BUSCAR", "/buscar (lenguaje natural)", "El ciudadano pregunta en sus palabras; el motor NL2SQL verificado responde con cifras de las filas reales, citando la fuente."),
]
x = Inches(0.6)
cw, gap = Inches(4.0), Inches(0.27)
for kick, ruta, desc in levels:
    r = rect(s, x, Inches(2.1), cw, Inches(3.9), CREMA)
    tf = r.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.22)
    para(tf, kick, 15, color=AZUL2, bold=True, font=MONO, first=True, space_after=2)
    para(tf, ruta, 16, color=AZUL, bold=True, space_after=8)
    para(tf, desc, 13.5, color=INK, space_after=0)
    x = Emu(int(x + cw + gap))
tf = box(s, Inches(0.65), Inches(6.25), Inches(12), Inches(0.6))
para(tf, "De lo general a lo puntual: panorama → detalle → dato exacto. Cada nivel dirige al siguiente.", 13, color=MUTED, first=True)
footer(s)

# 5 · Demo panorama (cifras)
s = slide()
kicker_title(s, "Demo 1/3 · Inicio · corte 2026-07-10", "El panorama, en vivo")
stat_cards(s, [
    ("25.192", "datasets integrados", AZUL),
    ("1.423", "entidades publicadoras", AZUL),
    ("6", "portales consolidados", AZUL),
    ("29", "variables curadas por dataset", AZUL),
    ("71 %", "del catálogo en ROJO", BAD),
])
bullets(s, [
    ("El hallazgo que nadie veía", "el 71 % de los datasets está desactualizado frente a la frecuencia que su PROPIA entidad declaró. Solo el 9 % está al día."),
    ("Se actualiza solo, todos los días", "ETL nocturno + cosecha semanal + clasificación automática. Ninguna cifra está quemada: el panorama nunca envejece."),
    ("Cifras que varían a diario", "estos números son el corte del 2026-07-10 — verificables en vivo en datosvivos.co/api/v1/stats/panorama."),
], y=Inches(4.35), size=15, gap=7)
footer(s)

# 6 · Tablero del decisor
s = slide()
kicker_title(s, "Demo 2/3 · Detalle entidad (Power BI)", "El control de gestión, por sector y entidad")
bullets(s, [
    ("Salud del catálogo", "semáforo de frescura por entidad: verde ≤ frecuencia declarada · amarillo ≤ 2× · rojo > 2×. El % de cumplimiento por entidad, listo para gestión."),
    ("Uso", "descargas, vistas e interés reciente: qué datasets importan a la ciudadanía."),
    ("Cobertura territorial", "mapa DIVIPOLA con drill departamento → municipio."),
    ("Filtros del decisor", "sector · entidad · tipo de acceso · calidad (Ley 1712) · territorio — la pregunta '¿cómo está MI sector?' se responde en dos clics."),
    ("IA detrás del tablero", "la depuración, consolidación y definición de los casos de calidad de datos se hizo con IA: clasificación automática, curación de metadata, inferencia territorial."),
])
footer(s)

# 7 · El ciudadano pregunta
s = slide()
kicker_title(s, "Demo 3/3 · Buscar (lenguaje natural)", "“¿Cuántos colegios públicos hay en Boyacá?”")
bullets(s, [
    ("NL2SQL / Text-to-SQL", "el ciudadano escribe en lenguaje natural; el motor genera la consulta SQL sobre el dataset correcto y la ejecuta contra los datos oficiales."),
    ("Cero cifras inventadas", "verificación determinista ANTES de ejecutar + validación de cada número de la respuesta contra las filas reales. Si no se puede verificar, se rehúsa — nunca se estima."),
    ("Fuente citada, siempre", "cada respuesta enlaza el dataset original y muestra la consulta generada (transparencia auditable)."),
    ("Accesible por diseño", "entrada por voz y respuesta narrada — Ley 1618 de 2013."),
])
footer(s)

# 8 · Dónde vive la IA
s = slide()
kicker_title(s, "Tecnologías emergentes · IA", "Un agente de IA para servicios públicos")
tf = box(s, Inches(0.65), Inches(1.55), Inches(12), Inches(0.5))
para(tf, "IA generativa + arquitectura híbrida: modelos de lenguaje que razonan, motor determinista que verifica. Pertinente, aplicable e interpretable — nunca superficial.", 13, color=MUTED, first=True)
# dos columnas
r = rect(s, Inches(0.6), Inches(2.25), Inches(6.0), Inches(4.15), CREMA)
tf = r.text_frame; tf.word_wrap = True
tf.margin_left = tf.margin_right = Inches(0.22)
para(tf, "EN LOS TABLEROS", 13, color=AZUL2, bold=True, font=MONO, first=True, space_after=6)
for t in ["Depuración y consolidación de 6 portales heterogéneos",
          "Definición de casos de calidad: clasificación automática de reportes administrativos (Ley 1712)",
          "Curación de columnas y metadata (LLM + heurísticas)",
          "Inferencia territorial DIVIPOLA (~89 % de cobertura)",
          "Guardas anti-basura (metadata placeholder)"]:
    para(tf, "—  " + t, 13.5, color=INK, space_after=7)
r = rect(s, Inches(6.85), Inches(2.25), Inches(6.0), Inches(4.15), CREMA)
tf = r.text_frame; tf.word_wrap = True
tf.margin_left = tf.margin_right = Inches(0.22)
para(tf, "EN EL BUSCADOR", 13, color=AZUL2, bold=True, font=MONO, first=True, space_after=6)
for t in ["NL2SQL generativo con verificación determinista de 3 capas (genera → verifica con código → ejecuta)",
          "Embeddings semánticos (multilingual-e5 + ChromaDB) para elegir el dataset correcto",
          "Clasificador de intención y mapeo a consultas estructuradas",
          "Narrativa anti-alucinación: todo número se valida contra las filas",
          "MCP server: las herramientas expuestas a cualquier agente de IA"]:
    para(tf, "—  " + t, 13.5, color=INK, space_after=7)
footer(s)

# 9 · Metodología
s = slide()
kicker_title(s, "Rigor técnico", "CRISP-ML(Q), adaptado a un catálogo vivo")
bullets(s, [
    ("Entendimiento", "el 'dato' es doble: la metadata de 25.192 datasets y las filas consultadas bajo demanda."),
    ("Preparación — donde la IA depura", "ETL diario + cosecha CKAN/DCAT; calidad auditada columna a columna contra la fuente (17/18 al 100 %); clasificación y curación automáticas."),
    ("Modelado — generar y VERIFICAR", "adaptación central: en vez de entrenar-y-congelar, cada consulta pasa por generación (LLM) → verificación (código) → ejecución."),
    ("Evaluación", "golden sets versionados + 35 archivos de pruebas + el verificador embebido en producción."),
    ("Despliegue y monitoreo (la Q)", "Docker reproducible; actualización diaria automática; el semáforo monitorea la deriva DEL CATÁLOGO, no del modelo."),
])
footer(s)

# 10 · Nivel Avanzado (letra del TDR)
s = slide()
kicker_title(s, "Cumplimiento del TDR", "Nivel Avanzado, con la letra del pliego")
rows = [
    ("Agentes de IA para servicios públicos", "el agente consulta y procesa datos abiertos de manera automática para responder solicitudes ciudadanas."),
    ("IA generativa y sistemas conversacionales", "buscador conversacional basado en datos abiertos: NL2SQL / Text-to-SQL generativo verificado."),
    ("Modelos de lenguaje + arquitectura híbrida", "el LLM razona, el motor determinista verifica (3 capas) — con embeddings neuronales de retrieval."),
    ("Integración de grandes volúmenes", "25.192 datasets de 6 fuentes y 3 protocolos — muy por encima de los 3-10 conjuntos del nivel intermedio."),
    ("Datos estructurados y no estructurados", "metadata estructurada + texto libre procesado con embeddings; 29 variables curadas por dataset (el intermedio pide 10-20)."),
    ("Automatización, escalabilidad y despliegue funcional", "actualización diaria automática y solución EN PRODUCCIÓN: datosvivos.co."),
]
tf = box(s, Inches(0.65), Inches(1.95), Inches(12.0), Inches(4.8))
for i, (head, body) in enumerate(rows):
    para(tf, head, 15, color=AZUL, bold=True, first=(i == 0), space_after=1)
    para(tf, body, 13, color=INK, space_after=8)
footer(s)

# 10 · Diferenciadores
s = slide()
kicker_title(s, "Por qué DatosVivos", "Lo que nadie más hace")
bullets(s, [
    ("Integra los portales federados", "datos.gov.co + IGAC + Bogotá + Cali + Medellín + Valle en un catálogo comparable. Hoy, eso exige revisar sitio por sitio."),
    ("Se actualiza solo", "panorama diario automático — no es un informe: es infraestructura viva."),
    ("Verificable de punta a punta", "cada cifra con fuente citada; API pública para auditar los números del sitio; repo abierto y replicable."),
    ("Interoperable por estándar", "MCP server: cualquier agente de IA puede consultar el catálogo colombiano."),
    ("Accesible e institucional", "identidad gov.co, voz y narración (Ley 1618), sin registro y sin rastreadores."),
])
footer(s)

# 11 · Impacto + equipo
s = slide()
kicker_title(s, "Impacto y escalabilidad", "De la entidad al país")
bullets(s, [
    ("Entidad", "ve su inventario y su rezago en segundos → corrige."),
    ("Sector", "control consolidado de las entidades adscritas → gestiona."),
    ("MinTIC", "panorama nacional medible para las Hojas de Ruta de Datos Abiertos → política basada en evidencia."),
    ("Ciudadanía", "el dato público deja de exigir conocimientos técnicos → apropiación."),
    ("Escala", "agregar un portal es configuración; el patrón sirve a cualquier país Socrata/CKAN/DCAT."),
], size=15, gap=6, h=Inches(3.4))
tf = box(s, Inches(0.65), Inches(5.7), Inches(12), Inches(1.1))
para(tf, "EQUIPO GIT TIC — AGENCIA NACIONAL DE INFRAESTRUCTURA", 12, color=AZUL2, bold=True, font=MONO, first=True, space_after=3)
para(tf, "Hernán Darío Gutiérrez Casas (líder estratégico) · Ileana Andrea Navarro Castrillón (líder de equipo y comunicaciones) · Jhonatan Sneider Rico Pinto (líder técnico y de datos)", 13, color=INK)
footer(s)

# 12 · Cierre + roadmap
s = slide(AZUL)
tf = box(s, Inches(0.9), Inches(1.6), Inches(11.5), Inches(3.2))
para(tf, "Lo que sigue", 14, color=RGBColor(0xBF, 0xD4, 0xE8), bold=True, font=MONO, first=True, space_after=8)
para(tf, "Ya ejecutado (julio 2026): motor de lenguaje en la API de Claude (~1.5 s) · bodega local Parquet COMPLETA (10.279 datasets, el buscador responde en milisegundos desde la copia local) · catalogación temática al 100 % · evaluación ciudadana de 50 preguntas convertida en mejoras estructurales del buscador.", 14, color=BLANCO, space_after=6)
para(tf, "Lo que sigue: filtros de año/municipio dentro del dataset elegido y respuestas compuestas (KPI + tendencia + per cápita).", 14, color=BLANCO, space_after=20)
para(tf, "datosvivos.co", 34, color=BLANCO, bold=True, font=MONO, space_after=4)
para(tf, "El panorama de los datos abiertos de Colombia. En vivo, verificable, para decidir.", 16, color=RGBColor(0xBF, 0xD4, 0xE8))
footer(s, dark=True)

# ========================= RESPALDO TÉCNICO =========================

def backup(kicker, title):
    s = slide()
    kicker_title(s, "Respaldo técnico · " + kicker, title, title_size=28)
    return s

# B1 arquitectura
s = backup("B1", "Arquitectura de 3 capas (fiel al plan inicial de inscripción)")
bullets(s, [
    ("Capa MCP", "servidor MCP sobre las APIs Socrata de datos.gov.co (Discovery, SODA, Metadata) — search_datasets · get_metadata · query_data · cross_datasets."),
    ("Capa motor", "FastAPI + PostgreSQL (catálogo curado, vistas _decisor) + ChromaDB (retrieval semántico en ambos caminos) + DuckDB (bodega Parquet local de 10.279 datasets + CSVs federados) + backend LLM intercambiable (producción: API de Claude)."),
    ("Capa presentación", "Next.js (panorama + buscador SSE) y Power BI (tablero publish-to-web sobre CSVs públicos de la API). Evolución documentada: Streamlit → Next.js (ADR-011)."),
    ("Despliegue", "Docker Compose con imagen reproducible, túnel seguro de salida, cron diario: ETL + regla de cola de la bodega Parquet (snapshot fresco → respuesta local en milisegundos; fuente cambió → dato vivo)."),
])
footer(s)

# B2 motor verificado
s = backup("B2", "Motor NL2SQL: generar no basta — hay que verificar")
bullets(s, [
    ("Capa 1 · Esquema real", "el LLM genera viendo SOLO columnas curadas reales del dataset (tipos semánticos: dimensión/métrica/fecha/geo). No puede alucinar columnas."),
    ("Capa 2 · Verificación estática", "código (no otro LLM) valida columnas, funciones permitidas, filtro territorial y solo-lectura ANTES de ejecutar."),
    ("Capa 3 · Validación del resultado", "toda cifra de la narrativa se contrasta contra la lista calculada de las filas; un número ajeno censura la oración."),
    ("Reparación y refusal", "si la verificación falla: ciclo de reparación acotado; si persiste, la respuesta se niega. Preferimos no responder a responder mal."),
    ("Respaldo determinista", "plantillas SoQL por tipo de pregunta (conteo/comparación/ranking/tendencia/mapa) como camino estructurado con chips."),
])
footer(s)

# B3 modelo de datos
s = backup("B3", "Modelo de datos: una vista curada como fuente única")
bullets(s, [
    ("datasets (42 columnas)", "una fila por dataset del catálogo integrado; upsert idempotente por dataset_id (auditado: 0 duplicados de clave)."),
    ("v_dataset_status_decisor (29 variables)", "la vista del decisor: identidad, semáforo de frescura, uso, acceso (directo/archivo/solo metadatos), territorio DIVIPOLA, calidad."),
    ("v_entity_summary_decisor", "agregado por entidad con pct_verdes: el indicador de cumplimiento listo para gestión."),
    ("Una sola fuente de verdad", "panorama web, tablero Power BI y CSVs públicos leen LA MISMA vista — imposible que se desalineen."),
])
footer(s)

# B4 calidad
s = backup("B4", "Calidad de datos: medida, no declarada")
bullets(s, [
    ("Auditoría columna a columna", "17/18 columnas al 100 % de fidelidad contra la fuente Socrata (reportes versionados en eval/reports/)."),
    ("Clasificación continua", "los 2.996 reportes administrativos (Ley 1712) se separan de los datos temáticos automáticamente, en cada corrida del ETL."),
    ("Inferencia territorial", "códigos DIVIPOLA asignados por IA con confianza registrada (~89 % de cobertura del catálogo)."),
    ("Guardas anti-basura", "metadata placeholder sin diligenciar ({{name}}) se descarta en la ingesta; el catálogo no acumula ruido."),
    ("Atribución por origen", "cada dataset se atribuye al portal donde su entidad publica originalmente — incluso las copias federadas del solapamiento cross-portal."),
])
footer(s)

# B5 evaluación
s = backup("B5", "Evaluación y trazabilidad")
bullets(s, [
    ("Golden sets versionados", "eval/golden_queries.yaml y golden_chips.yaml — corridas reproducibles con reportes históricos (16 en eval/reports/)."),
    ("35 archivos de pruebas", "verificador SoQL, validador anti-alucinación, reparación, geo/DIVIPOLA, cosecha, MCP (stdio/SSE), rutas de API."),
    ("Evaluación embebida", "el verificador corre en producción en cada consulta — la garantía no es una métrica de laboratorio."),
    ("Decisiones documentadas", "ADRs públicos (017-023): del principio 'la IA razona, el motor verifica' al pivote panorama-decisor."),
    ("Telemetría anónima", "lo más consultado alimenta la mejora sin datos personales."),
])
footer(s)

# B6 soberanía
s = backup("B6", "Soberanía, seguridad y cumplimiento")
bullets(s, [
    ("Infraestructura del Estado", "el servicio corre en infraestructura pública; los datos consultados son públicos por definición."),
    ("Sin datos personales", "cero registro, cero rastreadores; telemetría agregada y anónima."),
    ("Solo lectura", "el motor no puede escribir en ninguna fuente; verificación de solo-lectura en la capa 2."),
    ("Repo abierto y auditable", "código, documentación, pruebas y evaluación públicos — replicable con Docker en cualquier máquina (guía de validación para el jurado)."),
    ("Accesibilidad", "Ley 1618 de 2013 y WCAG 2.1 AA: voz, narración, contraste, escala tipográfica."),
])
footer(s)

OUT = "recursos/presentacion.pptx"
prs.save(OUT)
print(f"OK → {OUT} ({len(prs.slides.__iter__.__self__._sldIdLst)} diapositivas)")
