# Seguimiento — 50 preguntas ciudadanas

> Documento de trabajo. Último ciclo corrido: **ciclo3**. Regenerar la columna 'entregado' con `python eval/ciudadano/correr_ciclo.py <n>` y este archivo con `generar_seguimiento.py` (los veredictos manuales se pierden: mantenerlos en la sección de abajo).

## c01 — ¿Cuántas camas de UCI hay disponibles en mi ciudad?

**Esperado:** Una cifra grande y clara (KPI) con la ciudad visible, la fecha del dato al lado (es un dato que cambia a diario) y de dónde sale. Ideal: un desglose corto por hospital debajo. NO quiero: el total nacional cuando pregunté por mi ciudad, ni un número sin fecha.

**Entregado ciclo1:** dataset: sdmr-tfmf · MEDICAMENTOS VITALES NO DISPONIBLES
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 10507}`

**Entregado ciclo2:** dataset: s3n2-sqjp · ESTABLECIMIENTOS IMPORTADORES CERTIFICADOS EN CCAA DE DISPOSITIVOS MÉDICOS Y EQU
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 1714}`

**Entregado ciclo3:** dataset: s3n2-sqjp · ESTABLECIMIENTOS IMPORTADORES CERTIFICADOS EN CCAA DE DISPOSITIVOS MÉDICOS Y EQU
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 1714}`

## c02 — ¿Qué hospitales públicos hay cerca de donde vivo?

**Esperado:** Una lista con nombre, dirección y nivel de atención, idealmente sobre un mapa con puntos. Si no puede saber "cerca", que me pida el municipio con un selector, no que adivine. NO: un conteo seco ("hay 5.000 hospitales").

**Entregado ciclo1:** dataset: ctct-gh6w · LISTADO DE VACUNAS CON REGISTRO SANITARIO VIGENTE CON CORTE AL ÚLTIMO DÍA HÁBIL 
  → barras por región (fallback: regiones por nombre, sin códigos) · 32 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': 'PENNSYLVANIA -  USA', 'n': '4'}`

**Entregado ciclo2:** dataset: 54i9-zshx · DIRECTORIO E.S.E HOSPITALES DEPARTAMENTO DE  SANTANDER
  → barras por región (fallback: regiones por nombre, sin códigos) · 32 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': 'BUCARAMANGA', 'n': '27'}`

**Entregado ciclo3:** dataset: 54i9-zshx · DIRECTORIO E.S.E HOSPITALES DEPARTAMENTO DE  SANTANDER
  → barras por región (fallback: regiones por nombre, sin códigos) · 32 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': 'BUCARAMANGA', 'n': '27'}`

## c03 — ¿Cuántos casos de dengue van este año en el país?

**Esperado:** KPI del año en curso + una línea de tendencia mensual para ver si sube o baja, con los años anteriores en gris para comparar. Fuente y fecha visibles. NO: el acumulado histórico de todos los años como si fuera el del año actual.

**Entregado ciclo1:** dataset: tm62-e28n · Casos de dengue en la ciudad de Pereira
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 5528}`

**Entregado ciclo2:** dataset: qzc7-jbg3 · 13. Dengue, Dengue grave y mortalidad por dengue municipio de Bucaramanga
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 28626}`

**Entregado ciclo3:** dataset: qzc7-jbg3 · 13. Dengue, Dengue grave y mortalidad por dengue municipio de Bucaramanga
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 28626}`

## c04 — ¿Qué porcentaje de niños tiene el esquema de vacunación completo?

**Esperado:** Un porcentaje grande con su año de referencia, y una barra por departamento para ver dónde está peor. Si el dato tiene 2 años de atraso, que lo diga en grande. NO: un conteo de filas de un dataset de vacunas que no responde el porcentaje.

**Entregado ciclo1:** dataset: 8cw5-iyp3 · Puestos de vacunación de Risaralda - Puntos de vacunación y horarios de atención
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 60}`

**Entregado ciclo2:** dataset: 8cw5-iyp3 · Puestos de vacunación de Risaralda - Puntos de vacunación y horarios de atención
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 60}`

**Entregado ciclo3:** dataset: 8cw5-iyp3 · Puestos de vacunación de Risaralda - Puntos de vacunación y horarios de atención
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 60}`

## c05 — ¿Cuánto se demora en promedio una cita con especialista en la EPS?

**Esperado:** Un promedio en días con el nombre de la EPS, comparado contra el promedio nacional (dos barras). Si el Estado no mide esto, que me lo diga honestamente y me sugiera dónde reclamar (Supersalud). NO: un dataset cualquiera de salud que no habla de tiempos.

**Entregado ciclo1:** dataset: 8cw5-iyp3 · Puestos de vacunación de Risaralda - Puntos de vacunación y horarios de atención
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 60}`

**Entregado ciclo2:** dataset: k5bd-cym5 · OPORTUNIDAD EN ASIGNACIÓN DE CITAS DE MEDICINA ESPECIALIZADA DE LA E.S.E HUS
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': '236023'}`

**Entregado ciclo3:** dataset: k5bd-cym5 · OPORTUNIDAD EN ASIGNACIÓN DE CITAS DE MEDICINA ESPECIALIZADA DE LA E.S.E HUS
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': '236023'}`

## c06 — ¿Cuántos cupos escolares hay en los colegios públicos de mi municipio?

**Esperado:** Cifra de cupos o matrícula del municipio con el año lectivo, y la lista de colegios con su matrícula debajo (tabla corta ordenada). NO: el dato de otro municipio ni la matrícula nacional.

**Entregado ciclo1:** dataset: y64w-f2gm · Colegios privados de la ciudad de Pereira
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 145}`

**Entregado ciclo2:** dataset: a3jg-j674 · Estudiantes Matriculados y Graduados CEFIT
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 13461}`

**Entregado ciclo3:** dataset: w5z3-vb4d · Directorio de los colegios oficiales
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 71}`

## c07 — ¿Qué universidades públicas tienen los mejores resultados en las pruebas Saber Pro?

**Esperado:** Un ranking de barras (top 10) con el puntaje promedio y el año de la prueba. Que distinga públicas de privadas si mezcla. NO: un listado de universidades sin puntaje.

**Entregado ciclo1:** dataset: hk5x-635y · Pruebas ICFES
  → barras horizontales (categoria × valor) · 5 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'categoria': 'NR', 'n': 19}`

**Entregado ciclo2:** dataset: 6kwm-9788 · Resultados Saber Pro Competencias Especificas 2019-2
  → barras horizontales (categoria × valor) · 10 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'categoria': 'EK201950234799', 'n': '3'}`

**Entregado ciclo3:** dataset: 6kwm-9788 · Resultados Saber Pro Competencias Especificas 2019-2
  → barras horizontales (categoria × valor) · 10 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'categoria': '1003', 'n': '71307'}`

## c08 — ¿Cuántos estudiantes desertaron del colegio el año pasado?

**Esperado:** KPI del año con la tasa (%) además del número absoluto, y una tendencia de 5 años para contexto. NO: solo el número absoluto sin tasa (no sé si es mucho o poco).

**Entregado ciclo1:** dataset: c4qb-ek68 · INDICADORES EDUCATIVOS DEL DEPARTAMENTO DEL MAGDALENA POR MUNICIPIOS 2018 - 2024
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 214}`

**Entregado ciclo2:** dataset: 3iew-7wpx · DESERCION ACADEMICA PREGRADO Y POSGRADO
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 3372}`

**Entregado ciclo3:** dataset: 3iew-7wpx · DESERCION ACADEMICA PREGRADO Y POSGRADO
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 3372}`

## c09 — ¿Cuánto cuesta el programa de alimentación escolar y a cuántos niños llega?

**Esperado:** Dos KPIs lado a lado: presupuesto/gasto y beneficiarios, mismo año. Un costo por niño calculado sería ideal. NO: uno de los dos números sin el otro.

**Entregado ciclo1:** dataset: 7y7n-8wu6 · Estudiantes Beneficiados con el Programa de Alimentación Escolar PAE en el Munic
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 16722}`

**Entregado ciclo2:** dataset: qpf2-j35h · REPORTE DE ESTUDIANTES BENEFICIADOS POR EL PROGRAMA DE ALIMENTACIÓN ESCOLAR
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 2208}`

**Entregado ciclo3:** dataset: qpf2-j35h · REPORTE DE ESTUDIANTES BENEFICIADOS POR EL PROGRAMA DE ALIMENTACIÓN ESCOLAR
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 2208}`

## c10 — ¿Cuántas becas o créditos del Icetex se entregaron este año?

**Esperado:** KPI del año + barras por tipo (beca, crédito condonable, etc.). Fecha y fuente. NO: el histórico completo sumado como si fuera el año.

**Entregado ciclo1:** dataset: 26bn-e42j · Créditos Otorgados.
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 109139}`

**Entregado ciclo2:** dataset: f673-3gn8 · Nuevos beneficiarios propios.
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 29187}`

**Entregado ciclo3:** dataset: f673-3gn8 · Nuevos beneficiarios propios.
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 29187}`

## c11 — ¿Está subiendo o bajando el robo de celulares en mi ciudad?

**Esperado:** Una línea mensual de 2-3 años de hurtos en mi ciudad con una lectura en una frase ("bajó 12 % frente al año pasado"). NO: el total nacional ni una cifra sin serie de tiempo — la pregunta ES la tendencia.

**Entregado ciclo1:** dataset: i7cb-raxc · CÓDIGO ÚNICO DE MEDICAMENTOS VIGENTES
  → línea (periodo × n) · 60 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'periodo': '1989-07-01 00:00:00', 'n': 2}`

**Entregado ciclo2:** dataset: 9vha-vh9n · Reporte Hurto por Modalidades Policía Nacional
  → línea (periodo × n) · 60 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'periodo': '2010-01-01 00:00:00', 'n': 1916}`

**Entregado ciclo3:** dataset: 9vha-vh9n · Reporte Hurto por Modalidades Policía Nacional
  → línea (periodo × n) · 60 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'periodo': '2010-01-01 00:00:00', 'n': 1916}`

## c12 — ¿Cuáles son los barrios más peligrosos de Bogotá?

**Esperado:** Ranking de barras por localidad/barrio con el tipo de delito seleccionable, y un mapa de calor si se puede. Advertencia de que son denuncias (subregistro). NO: datos de otra ciudad.

**Entregado ciclo1:** dataset: 4fxt-zv8v · Encuesta de percepción Acoso Callejero a mujeres Línea base Ciudades Seguras Ken
  → ERROR HONESTO: No pudimos leer el CSV federado: 'utf-8' codec can't decode byte 0xe5 in position 10056: invalid continuation byte

**Entregado ciclo2:** dataset: u8vy-4dkb · Subsidios de Vivienda de la Caja Promotora de Vivienda Militar y de Policía
  → ERROR HONESTO: Ranking requiere ≥1 columna de tipo `dimension`

**Entregado ciclo3:** dataset: u8vy-4dkb · Subsidios de Vivienda de la Caja Promotora de Vivienda Militar y de Policía
  → ERROR HONESTO: Ranking requiere ≥1 columna de tipo `dimension`

## c13 — ¿Cuántos homicidios hubo en Colombia el año pasado?

**Esperado:** KPI del año cerrado + tendencia de 10 años para ver el contexto (¿mejor o peor que antes?). Tasa por 100.000 habitantes al lado del absoluto. NO: mezclar años ni darme un subconjunto (una sola ciudad) sin decirlo.

**Entregado ciclo1:** dataset: kn94-44f3 · Homicidios comunes en la ciudad de Santiago de Cali según comuna del hecho desde
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 43}`

**Entregado ciclo2:** dataset: u8eq-92tb · MASACRES
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 420}`

**Entregado ciclo3:** dataset: u8eq-92tb · MASACRES
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 420}`

## c14 — ¿Qué tan seguro es el barrio al que me quiero mudar?

**Esperado:** Que me pida el barrio/localidad (selector) y me muestre los delitos de los últimos 12 meses por tipo (barras) comparados con el promedio de la ciudad. NO: una respuesta genérica de seguridad nacional.

**Entregado ciclo1:** dataset: t4ks-awg9 · Propiedades Horizontales Municipio de Fusagasugá
  → barras por región (fallback: regiones por nombre, sin códigos) · 32 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': '4,349038964', 'n': '6'}`

**Entregado ciclo2:** dataset: 59m2-qank · Histórico Actuaciones Policivas San Pedro
  → barras por región (fallback: regiones por nombre, sin códigos) · 2 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': 'Urbana', 'n': '240'}`

**Entregado ciclo3:** dataset: 59m2-qank · Histórico Actuaciones Policivas San Pedro
  → barras por región (fallback: regiones por nombre, sin códigos) · 2 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': 'Urbana', 'n': '240'}`

## c15 — ¿Cuántos policías hay por habitante en mi departamento?

**Esperado:** Una razón (policías por 10.000 hab.) comparada con el promedio nacional, dos barras. Si el dato de pie de fuerza no es público, decirlo claro. NO: el número de estaciones como si fuera el de policías.

**Entregado ciclo1:** dataset: fs36-azrv · Registro de Sanciones Contadores
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 85}`

**Entregado ciclo2:** dataset: meew-mguv · Amenazas Policía Nacional de Colombia
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 650347}`

**Entregado ciclo3:** dataset: meew-mguv · Amenazas Policía Nacional de Colombia
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 650347}`

## c16 — ¿Cuál es la tasa de desempleo actual y cómo ha cambiado?

**Esperado:** KPI del último mes disponible + línea de 5 años. Que diga el mes de referencia (el desempleo es mensual). NO: un promedio histórico sin fecha.

**Entregado ciclo1:** dataset: —
  → SIN RESPUESTA EJECUTADA — mensaje del sistema: Estos datasets solo son consultables en su portal de origen (no exponen tabla de datos). Abre la fuente para verlos.

**Entregado ciclo2:** dataset: u4ze-bi7k · DESERCION DE LA FORMACIÓN PROFESIONAL INTEGRAL
  → línea (periodo × n) · 60 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'periodo': '"01/02/2022"', 'n': '30'}`

**Entregado ciclo3:** dataset: u4ze-bi7k · DESERCION DE LA FORMACIÓN PROFESIONAL INTEGRAL
  → línea (periodo × n) · 60 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'periodo': '"01/02/2022"', 'n': '30'}`

## c17 — ¿Cuánto gana en promedio un colombiano?

**Esperado:** Salario promedio y mediano (los dos, son muy distintos) con el año, y barras por departamento o sector. NO: solo el promedio, que engaña.

**Entregado ciclo1:** dataset: w9zh-vetq · Tasas de interés activas por tipo de crédito – Histórico
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': '87615631'}`

**Entregado ciclo2:** dataset: hf6d-emrx · Disparidad Salarial Hombres Mujeres
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 325}`

**Entregado ciclo3:** dataset: w9zh-vetq · Tasas de interés activas por tipo de crédito – Histórico
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': '87615631'}`

## c18 — ¿Cuántas empresas nuevas se crearon en mi ciudad este año?

**Esperado:** KPI del año en curso con comparación contra el año pasado (flecha arriba/abajo), y barras por sector económico. NO: el stock total de empresas como si fueran las nuevas.

**Entregado ciclo1:** dataset: gwqv-sqvs · BASE DE DATOS DE EMPRESAS Y/O ENTIDADES ACTIVAS - JURISDICCIÓN CÁMARA DE COMERCI
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': '91090'}`

**Entregado ciclo2:** dataset: nkze-evrk · EMPRESAS RENOVADAS BUGA 2025
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 4598}`

**Entregado ciclo3:** dataset: nkze-evrk · EMPRESAS RENOVADAS BUGA 2025
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 4598}`

## c19 — ¿En qué gasta la plata mi alcaldía?

**Esperado:** Barras del presupuesto por sector (educación, salud, vías...) del año vigente, con ejecutado vs. presupuestado. Que me pida el municipio. NO: el presupuesto nacional cuando pregunté por mi alcaldía.

**Entregado ciclo1:** dataset: ngcz-3x7a · Ejecución del Presupuesto de Gastos
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 231}`

**Entregado ciclo2:** dataset: 22ah-ddsj · OVCF - CUIPO - Programación de Ingresos
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 2775714}`

**Entregado ciclo3:** dataset: cuh8-kzv2 · Presupuesto Inicial Aprobado Municipio de Roldanillo 2020- corte Agosto
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 400}`

## c20 — ¿Cuánto vale la deuda pública de Colombia?

**Esperado:** KPI en billones con el % del PIB al lado (el número solo no dice nada) y una línea de 10 años. NO: una cifra sin unidad clara ni fecha.

**Entregado ciclo1:** dataset: h2jg-r3zg · Tarjetas de crédito y débito
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 180202}`

**Entregado ciclo2:** dataset: d8pq-kxa7 · DEUDA PUBLICA MUNICIPIO DE PEREIRA.
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 53}`

**Entregado ciclo3:** dataset: d8pq-kxa7 · DEUDA PUBLICA MUNICIPIO DE PEREIRA.
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 53}`

## c21 — ¿Cuántos accidentes de tránsito con muertos hubo este año?

**Esperado:** KPI del año + tendencia mensual, con desglose por tipo de actor (peatón, moto, carro) en barras. NO: todos los accidentes mezclados si pregunté por los fatales.

**Entregado ciclo1:** dataset: 6jmc-vaxk · VEHICULOS INVOLUCRADOS EN UN ACCIDENTE DE TRANSITO LEY 2251-2022
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 406540}`

**Entregado ciclo2:** dataset: yu3i-jau4 · Accidentes Viales
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 660}`

**Entregado ciclo3:** dataset: yu3i-jau4 · Accidentes Viales
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 660}`

## c22 — ¿Cuál es el estado de las vías para viajar este puente?

**Esperado:** Un mapa o lista de vías con estado (cerrada, paso restringido) y la fuente (Invías) con hora de actualización. Si el sistema no tiene datos en tiempo real, que lo diga y me lleve al canal oficial. NO: datos de hace un año presentados como actuales.

**Entregado ciclo1:** dataset: 7i66-rps2 · Estado de Vías
  → barras por región (fallback: regiones por nombre, sin códigos) · 26 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': 'Cundinamarca', 'n': '60'}`

**Entregado ciclo2:** dataset: 7i66-rps2 · Estado de Vías
  → barras por región (fallback: regiones por nombre, sin códigos) · 26 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': 'Cundinamarca', 'n': '60'}`

**Entregado ciclo3:** dataset: 7i66-rps2 · Estado de Vías
  → barras por región (fallback: regiones por nombre, sin códigos) · 26 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': 'Cundinamarca', 'n': '60'}`

## c23 — ¿Cuántos vehículos hay matriculados en Colombia?

**Esperado:** KPI total + barras por clase (carros, motos, camiones). Motos vs carros es el dato interesante. NO: solo el total.

**Entregado ciclo1:** dataset: u3vn-bdcy · CRECIMIENTO DEL PARQUE AUTOMOTOR RUNT2.0
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': '190588'}`

**Entregado ciclo2:** dataset: u3vn-bdcy · CRECIMIENTO DEL PARQUE AUTOMOTOR RUNT2.0
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': '190588'}`

**Entregado ciclo3:** dataset: u3vn-bdcy · CRECIMIENTO DEL PARQUE AUTOMOTOR RUNT2.0
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': '190588'}`

## c24 — ¿Cuánto se demora el SITP/TransMilenio en horas pico?

**Esperado:** Si hay datos de operación: tiempos o frecuencias por troncal. Si no los hay, honestidad y enlace al portal de Bogotá. NO: inventar un promedio.

**Entregado ciclo1:** dataset: du92-6y56 · Flota Vinculada del SITP
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 145}`

**Entregado ciclo2:** dataset: du92-6y56 · Flota Vinculada del SITP
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 145}`

**Entregado ciclo3:** dataset: du92-6y56 · Flota Vinculada del SITP
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 145}`

## c25 — ¿Cuántas multas de tránsito se pusieron el año pasado y por qué?

**Esperado:** KPI del año + ranking de las 10 infracciones más comunes (barras con el código y su descripción legible). NO: códigos de infracción crudos sin explicación (C29 no me dice nada).

**Entregado ciclo1:** dataset: epfm-5fhb · ACTORES RUNT POR MUNICIPIO Y DEPARTAMENTO RUNT2.0
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 104582}`

**Entregado ciclo2:** dataset: bx9v-nvfz · Comparendos de tránsito en el Municipio de Acacías
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 47647}`

**Entregado ciclo3:** dataset: bx9v-nvfz · Comparendos de tránsito en el Municipio de Acacías
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 47647}`

## c26 — ¿Cuántos subsidios de vivienda se han entregado y de qué tipo?

**Esperado:** KPI total + barras por programa con el valor entregado, y la tendencia anual. NO: programas duplicados con nombres distintos en la misma gráfica.

**Entregado ciclo1:** dataset: h2yr-zfb2 · Subsidios De Vivienda Asignados
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 86603}`

**Entregado ciclo2:** dataset: h2yr-zfb2 · Subsidios De Vivienda Asignados
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 86603}`

**Entregado ciclo3:** dataset: h2yr-zfb2 · Subsidios De Vivienda Asignados
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 86603}`

## c27 — ¿Qué barrios de mi ciudad no tienen acueducto?

**Esperado:** Mapa o lista por barrio/comuna con % de cobertura, ordenado del peor al mejor. NO: la cobertura nacional (99 %...) que esconde los huecos.

**Entregado ciclo1:** dataset: cuit-be64 · HISTORICO CONSUMO POR ESTRATO
  → barras por región (fallback: regiones por nombre, sin códigos) · 24 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': 'AGUADAS', 'n': '180'}`

**Entregado ciclo2:** dataset: d4t4-daja · Tarifas de acueducto
  → mapa choropleth por departamento · 1 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': '11', 'n': '1628'}`

**Entregado ciclo3:** dataset: d4t4-daja · Tarifas de acueducto
  → mapa choropleth por departamento · 1 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': '11', 'n': '1628'}`

## c28 — ¿Cuánto ha subido la tarifa de la energía en los últimos años?

**Esperado:** Línea de la tarifa kWh por estrato en 5 años, con mi ciudad/empresa seleccionable. NO: una tarifa de otra empresa sin decir cuál es.

**Entregado ciclo1:** dataset: ekup-y869 · Tarifas de gas natural para hogares - EPM
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 624}`

**Entregado ciclo2:** dataset: c698-wqig · Información Costo unitario de tarifas de energía CHEC
  → línea (periodo × n) · 19 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'periodo': 2008, 'n': 2251}`

**Entregado ciclo3:** dataset: c698-wqig · Información Costo unitario de tarifas de energía CHEC
  → línea (periodo × n) · 19 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'periodo': 2008, 'n': 2251}`

## c29 — ¿Cuántas familias viven en arriendo vs casa propia?

**Esperado:** Torta o barras (arriendo / propia / familiar) con el año del censo o encuesta. NO: un dato de hace 15 años sin advertirlo.

**Entregado ciclo1:** dataset: h2yr-zfb2 · Subsidios De Vivienda Asignados
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 86603}`

**Entregado ciclo2:** dataset: h2yr-zfb2 · Subsidios De Vivienda Asignados
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 86603}`

**Entregado ciclo3:** dataset: h2yr-zfb2 · Subsidios De Vivienda Asignados
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 86603}`

## c30 — ¿Dónde hay proyectos de vivienda de interés social activos?

**Esperado:** Lista/mapa por municipio con nombre del proyecto y estado. Que me deje filtrar por mi departamento. NO: proyectos ya cerrados como si estuvieran activos.

**Entregado ciclo1:** dataset: 49da-69ff · Viviendas Construidas En Macroproyectos
  → barras por región (fallback: regiones por nombre, sin códigos) · 12 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': 'CALI', 'n': '2'}`

**Entregado ciclo2:** dataset: 49da-69ff · Viviendas Construidas En Macroproyectos
  → barras por región (fallback: regiones por nombre, sin códigos) · 12 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': 'CALI', 'n': '2'}`

**Entregado ciclo3:** dataset: 49da-69ff · Viviendas Construidas En Macroproyectos
  → barras por región (fallback: regiones por nombre, sin códigos) · 12 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': 'CALI', 'n': '2'}`

## c31 — ¿Qué tan contaminado está el aire hoy en mi ciudad?

**Esperado:** Un semáforo o índice (bueno/regular/malo) con la hora de medición y la estación más cercana. Si no hay tiempo real, el último dato con su fecha en grande. NO: un promedio anual como si fuera el aire de hoy.

**Entregado ciclo1:** dataset: sbwg-7ju4 · Temperatura Ambiente del Aire
  → barras por región (fallback: regiones por nombre, sin códigos) · 32 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': 'BOGOTA D.C.', 'n': '10098643'}`

**Entregado ciclo2:** dataset: g4t8-zkc3 · Calidad del Aire en Colombia
  → mapa choropleth por departamento · 20 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': '11', 'n': '8011058'}`

**Entregado ciclo3:** dataset: g4t8-zkc3 · Calidad del Aire en Colombia
  → mapa choropleth por departamento · 20 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': '11', 'n': '8011058'}`

## c32 — ¿Cuántas hectáreas de bosque perdió Colombia el último año?

**Esperado:** KPI anual + tendencia de 10 años + mapa por departamento (Amazonía). NO: cifras de años distintos mezcladas.

**Entregado ciclo1:** dataset: hp9r-jxuu · Catálogo Nacional de Estaciones del IDEAM
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 19147}`

**Entregado ciclo2:** dataset: t7t3-vijg · Trámites de árbol aislado en la jurisdicción de Corantioquia
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 7206}`

**Entregado ciclo3:** dataset: iczg-dyt3 · AREAS DEFORESTADAS CHOCO
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 7937}`

## c33 — ¿Qué ríos están más contaminados?

**Esperado:** Ranking con el índice de calidad del agua y el punto de medición. NO: un listado de ríos sin métrica.

**Entregado ciclo1:** dataset: 62tk-nxj5 · Presión Atmosférica
  → barras horizontales (categoria × valor) · 10 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'categoria': 'ALTO MAGDALENA', 'total': '5328630626.4411'}`

**Entregado ciclo2:** dataset: w53e-3c28 · CORPOBOYACA CALIDAD DEL RECURSO HIDRICO POR CUENCA Y TRAMO POR VERTIMIENTOS PUNT
  → barras horizontales (categoria × valor) · 10 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'categoria': '23449', 'n': '2'}`

**Entregado ciclo3:** dataset: w53e-3c28 · CORPOBOYACA CALIDAD DEL RECURSO HIDRICO POR CUENCA Y TRAMO POR VERTIMIENTOS PUNT
  → barras horizontales (categoria × valor) · 10 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'categoria': '23449', 'n': '2'}`

## c34 — ¿Cuántos incendios forestales van este año?

**Esperado:** KPI del año + mapa de dónde, con comparación al año pasado. NO: el histórico sumado.

**Entregado ciclo1:** dataset: hp9r-jxuu · Catálogo Nacional de Estaciones del IDEAM
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 19147}`

**Entregado ciclo2:** dataset: a4bc-a9tq · REPORTE DE EVENTOS POR DESASTRES NATURALES Y ANTRÓPICOS (Histórico)
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 970}`

**Entregado ciclo3:** dataset: a4bc-a9tq · REPORTE DE EVENTOS POR DESASTRES NATURALES Y ANTRÓPICOS (Histórico)
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 970}`

## c35 — ¿Cuánta basura recicla mi ciudad?

**Esperado:** Porcentaje de aprovechamiento con el total de toneladas, comparado con otras ciudades (barras). NO: solo toneladas sin el %.

**Entregado ciclo1:** dataset: weq5-ryjx · 7. Caracterización Estaciones de Clasificación y Aprovechamiento (ECA), Unidades
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 102}`

**Entregado ciclo2:** dataset: weq5-ryjx · 7. Caracterización Estaciones de Clasificación y Aprovechamiento (ECA), Unidades
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 102}`

**Entregado ciclo3:** dataset: weq5-ryjx · 7. Caracterización Estaciones de Clasificación y Aprovechamiento (ECA), Unidades
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 102}`

## c36 — ¿Cuántos contratos a dedo (contratación directa) hizo mi alcaldía?

**Esperado:** KPI de contratos y monto por contratación directa vs licitación (barras), del municipio que yo elija, con enlace a los contratos. NO: el agregado nacional.

**Entregado ciclo1:** dataset: fs36-azrv · Registro de Sanciones Contadores
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 85}`

**Entregado ciclo2:** dataset: 37hf-6yc2 · Contratacion Emserchia E.S.P.
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 146}`

**Entregado ciclo3:** dataset: 37hf-6yc2 · Contratacion Emserchia E.S.P.
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 146}`

## c37 — ¿Qué entidades incumplen más la ley de transparencia?

**Esperado:** Ranking de entidades con su indicador de cumplimiento y qué les falta. NO: nombres sin métrica.

**Entregado ciclo1:** dataset: 2bqm-v6je · Registro de Publicaciones Alcaldía Municipal San Roque
  → barras horizontales (categoria × valor) · 10 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'categoria': '3.5', 'n': '1'}`

**Entregado ciclo2:** dataset: 6umk-ay53 · Esquemas de Publicidad de Información
  → barras horizontales (categoria × valor) · 2 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'categoria': 'Español', 'n': 119}`

**Entregado ciclo3:** dataset: 6umk-ay53 · Esquemas de Publicidad de Información
  → barras horizontales (categoria × valor) · 2 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'categoria': 'Español', 'n': 119}`

## c38 — ¿Cuántos procesos judiciales están atrasados en el país?

**Esperado:** KPI del inventario atrasado con la tasa de congestión, por jurisdicción (barras). NO: el total de procesos como si todos estuvieran atrasados.

**Entregado ciclo1:** dataset: fs36-azrv · Registro de Sanciones Contadores
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 85}`

**Entregado ciclo2:** dataset: fuyf-sb4r · Procesos en Casas de Justicia
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 5196555}`

**Entregado ciclo3:** dataset: fuyf-sb4r · Procesos en Casas de Justicia
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 5196555}`

## c39 — ¿Cuánta plata se ha recuperado de casos de corrupción?

**Esperado:** Cifra recuperada vs. cifra en investigación, con los casos grandes listados. Si el dato no existe consolidado, decirlo. NO: una cifra sin fuente clara.

**Entregado ciclo1:** dataset: i594-3uqz · INTEGRA (Índice Integral de Legalidad)
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 5363}`

**Entregado ciclo2:** dataset: 7p9a-zd9k · Directorio de Centros de Conciliación, Arbitraje, Amigable Composición e Insolve
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 435}`

**Entregado ciclo3:** dataset: 7p9a-zd9k · Directorio de Centros de Conciliación, Arbitraje, Amigable Composición e Insolve
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 435}`

## c40 — ¿Cuántas peticiones (PQRS) responde a tiempo el Estado?

**Esperado:** Porcentaje de respuesta a tiempo por entidad (ranking de mejores y peores). NO: el volumen de PQRS sin la tasa de cumplimiento.

**Entregado ciclo1:** dataset: a8mr-2nwi · Consolidado PQRS
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 15558}`

**Entregado ciclo2:** dataset: 939i-rj4g · PQRS ALCALDIA NEIVA
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 23375}`

**Entregado ciclo3:** dataset: tvp7-sc2i · Informe PQRS
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 120}`

## c41 — ¿Qué eventos culturales gratuitos hay este mes?

**Esperado:** Lista por fecha con lugar y cómo llegar, filtrable por ciudad. Si el sistema no tiene agenda, que lo diga y enlace la secretaría de cultura. NO: eventos pasados.

**Entregado ciclo1:** dataset: —
  → SIN RESPUESTA EJECUTADA — mensaje del sistema: Hay 472 datasets que coinciden. Marca otro chip para verlos más específicos.

**Entregado ciclo2:** dataset: —
  → SIN RESPUESTA EJECUTADA — mensaje del sistema: Hay 397 datasets que coinciden. Marca otro chip para verlos más específicos.

**Entregado ciclo3:** dataset: —
  → SIN RESPUESTA EJECUTADA — mensaje del sistema: Hay 397 datasets que coinciden. Marca otro chip para verlos más específicos.

## c42 — ¿Cuántas bibliotecas públicas hay y dónde están?

**Esperado:** KPI + mapa de puntos por municipio. Lista con horarios si existe. NO: solo el número.

**Entregado ciclo1:** dataset: ry5e-gwqx · Instituciones Educativas Municipio de Sogamoso Boyacá
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 108}`

**Entregado ciclo2:** dataset: xcks-wmvu · Bibliotecas Públicas Urbanas y Rurales del Municipio de Palmira 2021
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 13}`

**Entregado ciclo3:** dataset: xcks-wmvu · Bibliotecas Públicas Urbanas y Rurales del Municipio de Palmira 2021
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 13}`

## c43 — ¿Cuánta gente visita los parques nacionales?

**Esperado:** Ranking de parques por visitantes/año con tendencia (¿se recuperó después de la pandemia?). NO: un total nacional sin desglose.

**Entregado ciclo1:** dataset: 4zwu-ra3f · Resultados por sorteo Loteria Santander
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 2318}`

**Entregado ciclo2:** dataset: thwd-ivmp · Registro Nacional de Turismo - RNT
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': '679548'}`

**Entregado ciclo3:** dataset: thwd-ivmp · Registro Nacional de Turismo - RNT
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': '679548'}`

## c44 — ¿Cuántos adultos mayores reciben subsidio del Estado?

**Esperado:** KPI de beneficiarios + monto, por departamento (mapa o barras), con el programa nombrado (Colombia Mayor). NO: mezclar programas sin decirlo.

**Entregado ciclo1:** dataset: i7cb-raxc · CÓDIGO ÚNICO DE MEDICAMENTOS VIGENTES
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 157146}`

**Entregado ciclo2:** dataset: d7a5-cnra · Población Base de Datos Única de Afiliados BDUA del régimen subsidiado
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 1314469}`

**Entregado ciclo3:** dataset: d7a5-cnra · Población Base de Datos Única de Afiliados BDUA del régimen subsidiado
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 1314469}`

## c45 — ¿Cuánta población migrante hay en el país?

**Esperado:** KPI con fecha de corte + barras por departamento de residencia y la tendencia. NO: cifras viejas sin fecha (esto cambia rápido).

**Entregado ciclo1:** dataset: 9kvn-3qq8 · Informacion centro de atención integral a victimas - Declaraciones - Serie 1 de 
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 9831}`

**Entregado ciclo2:** dataset: 9kvn-3qq8 · Informacion centro de atención integral a victimas - Declaraciones - Serie 1 de 
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 9831}`

**Entregado ciclo3:** dataset: 9kvn-3qq8 · Informacion centro de atención integral a victimas - Declaraciones - Serie 1 de 
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 9831}`

## c46 — ¿Cuántos trámites del Estado puedo hacer 100 % en línea?

**Esperado:** KPI (n de X trámites totales, con %) + buscador o lista de los más usados con su enlace. NO: el número de oficinas físicas.

**Entregado ciclo1:** dataset: cnh8-i5yd · Oficinas de expedición de trámites de Cancillería - Ministerio de Relaciones Ext
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 171}`

**Entregado ciclo2:** dataset: w734-989f · Costos, trámites u otros procedimientos administrativos – OPAs (inscritos en el 
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 47}`

**Entregado ciclo3:** dataset: w734-989f · Costos, trámites u otros procedimientos administrativos – OPAs (inscritos en el 
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 47}`

## c47 — ¿Cómo votó mi municipio en las últimas elecciones?

**Esperado:** Barras por candidato con % y participación, del municipio que elija. NO: el resultado nacional cuando pedí el local.

**Entregado ciclo1:** dataset: rpmr-utcd · SECOP Integrado
  → barras por región (fallback: regiones por nombre, sin códigos) · 32 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'region': 'Antioquia', 'n': '4054208'}`

**Entregado ciclo2:** dataset: mv2e-prx5 · Divipole Elecciones Territoritoriales 2023 con georreferenciación
  → barras por región (fallback: regiones por nombre, sin códigos) · 32 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': '8825'}`

**Entregado ciclo3:** dataset: mv2e-prx5 · Divipole Elecciones Territoritoriales 2023 con georreferenciación
  → barras por región (fallback: regiones por nombre, sin códigos) · 32 fila(s) · consulta en vivo · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': '8825'}`

## c48 — ¿Cuántos funcionarios públicos hay y cuánto cuestan?

**Esperado:** KPI de funcionarios + costo de nómina anual, con tendencia. Por entidad si se puede. NO: uno de los dos datos sin el otro.

**Entregado ciclo1:** dataset: iaeu-rcn6 · Antecedentes de SIRI
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 43224}`

**Entregado ciclo2:** dataset: ri3x-4pu5 · Tarifas Para Servicios De Aseo - Aguas Nacionales EPM
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 2904}`

**Entregado ciclo3:** dataset: ri3x-4pu5 · Tarifas Para Servicios De Aseo - Aguas Nacionales EPM
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 2904}`

## c49 — ¿Qué proyectos de ley se están discutiendo ahora en el Congreso?

**Esperado:** Lista de proyectos activos con tema, estado (debate, sanción) y enlace al texto. Si no hay datos del Congreso, decirlo honesto. NO: leyes ya aprobadas como si estuvieran en discusión.

**Entregado ciclo1:** dataset: —
  → SIN RESPUESTA EJECUTADA — mensaje del sistema: Hay 21919 datasets que coinciden. Marca otro chip para verlos más específicos.

**Entregado ciclo2:** dataset: —
  → SIN RESPUESTA EJECUTADA — mensaje del sistema: Hay 219 datasets que coinciden. Marca otro chip para verlos más específicos.

**Entregado ciclo3:** dataset: —
  → SIN RESPUESTA EJECUTADA — mensaje del sistema: Hay 219 datasets que coinciden. Marca otro chip para verlos más específicos.

## c50 — ¿Cuánta plata le llega a mi municipio del gobierno nacional?

**Esperado:** KPI de transferencias (SGP) del año para mi municipio, con barras por destino (educación, salud, agua) y comparación por habitante contra municipios similares. NO: el total nacional del SGP.

**Entregado ciclo1:** dataset: 32sa-8pi3 · Tasa de Cambio Representativa del Mercado- TRM
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 8305}`

**Entregado ciclo2:** dataset: usa4-yg4a · Transferencias del juego de Lotería Tradicional
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 56327}`

**Entregado ciclo3:** dataset: usa4-yg4a · Transferencias del juego de Lotería Tradicional
  → KPI grande + nota 'cuenta registros, no suma' · 1 fila(s) · bodega Parquet local · con nota 'cifra verificada' + nombre del dataset + toggle SoQL · muestra: `{'n': 56327}`

---

# Balance del ciclo (al 2026-07-13)

## Trayectoria por ciclo

| Ciclo | Con artefacto y datos | Qué cambió |
|---|---|---|
| 1 | 46/50 | Línea base: ~25 preguntas con dataset NO pertinente (popularidad mandaba) |
| 2 | 47/50 | +Re-ranking semántico, boost nacional, temas completos, léxico de tipo: **39/50 cambiaron de dataset**, la gran mayoría a pertinentes |
| 3 | 47/50 | Estable (45/50 iguales) + 5 mejoras más (deforestación, presupuesto municipal, PQRS). Post-ciclo: TIPO **Total** dispara para montos y no suma tasas |

## Veredicto por grupos (ciclo 3)

- **Pertinentes con buen artefacto (~26)**: c02 hospitales, c03 dengue, c05 citas,
  c07 Saber Pro, c09/c10 PAE/Icetex, c11 hurto, c16 tendencia, c18 empresas,
  c19 presupuesto, c21-c23 tránsito, c25-c28 vivienda/servicios, c31 aire,
  c32 deforestación, c33 ríos, c35 reciclaje, c37 transparencia, c40 PQRS,
  c42 bibliotecas, c44 BDUA, c46 trámites, c47 elecciones.
- **Parciales (~13)**: dataset del tema correcto pero alcance municipal para
  pregunta nacional (c13 masacres, c20 deuda de Pereira) o dataset conexo sin
  la métrica exacta (c43 turismo por visitas de parques). El nombre del
  dataset siempre visible = transparente.
- **Honestos sin dato (~4)**: el Estado no publica eso como tabla consultable
  (c22 vías en tiempo real, c24 tiempos TransMilenio, c41 agenda cultural,
  c49 proyectos de ley). Respuesta correcta: decirlo — mejorable con enlace
  al canal oficial.
- **Aún débiles (~7)**: c01 camas UCI (existe el dato pero gana otro de
  Salud), c12 barrios peligrosos Bogotá, c14 seguridad de barrio, c15
  policías per cápita, c36 contratación directa municipal, c48 nómina
  estatal, c50 SGP municipal. Todos requieren o el dato inexistente o
  filtros dentro del dataset (año/municipio) que los chips aún no expresan.

## Qué sigue (en orden de valor)

1. Filtros de AÑO y MUNICIPIO dentro del dataset elegido (los chips filtran
   el catálogo, no las filas) — desbloquea c36, c50 y "este año" en general.
2. Respuestas compuestas (KPI + tendencia + desglose en una vista) y tasas
   per cápita cruzando con población.
3. Enlace al canal oficial cuando el dato no existe como tabla.
