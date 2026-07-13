# Ciclo ciudadano — análisis esperado vs. entregado

> Metodología (2026-07-12): 50 preguntas escritas COMO CIUDADANO, sin pensar en
> qué datasets existen, cada una con su respuesta esperada detallada (forma,
> gráficas, qué no ver) ANTES de correr nada — [preguntas_50.yaml](preguntas_50.yaml).
> Luego se corren una a una contra producción y se registra la respuesta
> entregada ([entregado_ciclo1.yaml](entregado_ciclo1.yaml), [ciclo2](entregado_ciclo2.yaml)).
> Reproducible: `python eval/ciudadano/correr_ciclo.py <n>` + `comparar_ciclos.py`.

## Ciclo 1 → patrones detectados (transversales, no por pregunta)

| # | Patrón | Evidencia | Mejora aplicada |
|---|--------|-----------|-----------------|
| P1 | **Pertinencia es LA brecha**: el score popularidad+palabras del refinador elige el dataset más popular del tema cuando ninguna palabra matchea | "¿parques nacionales?" → Lotería de Santander; "¿deuda pública?" → Tarjetas de crédito; ~25/50 no pertinentes | **Re-ranking semántico** del top-50 del subset con el índice e5/ChromaDB existente: el chip filtra, el embedding ordena |
| P2 | Preguntas nacionales caen en datasets municipales | "homicidios en Colombia" → Cali (43 filas como cifra nacional) | Boost +0.3 a `jurisdiccion_nivel='nacional'` cuando territorio=nacional (simétrico al departamental) |
| P3 | "cuánto" singular pide un MONTO, no un conteo; forzar Cuántos daba conteos irrelevantes como "cifra verificada" | "¿cuánto vale la deuda?" → contó filas de Tarjetas de crédito | Cuántos exige plural; "cuánto ha subido" → Tendencia; "en qué gasta" → Comparar |
| P4 | "mi ciudad / donde vivo" no es adivinable y el sistema respondía con OTRO municipio | c01 camas UCI → dato de otro lado sin decirlo | `hint` del mapper + aviso visible en /buscar pidiendo marcar el Territorio |
| P5 | Categorías-basura como barras | Ranking ICFES con barra "NR: 19" | Filtro NR/N.A/Sin dato/vacío en ambos motores (SoQL solo en columnas de texto) |
| P6 | Temas enteros invisibles: /chips ofrecía 12 de 26 categorías — el mapper NO PODÍA elegir Agricultura ni Seguridad | "producción agrícola" → Comercio | LIMIT 12→30 (vocabulario ya consolidado a 26 canónicas) |

## Resultado ciclo 2 (mismas 50 preguntas)

- **39/50 cambiaron de dataset elegido; la gran mayoría hacia pertinencia real.**
  Ejemplos: cita con especialista → *Oportunidad en Asignación de Citas de
  Medicina Especializada*; calidad del aire → *Calidad del Aire en Colombia*;
  elecciones → *Divipole Electoral georreferenciado*; adultos mayores → *BDUA
  régimen subsidiado*; robo de celulares → *Hurto por Modalidades Policía
  Nacional*; Saber Pro → *Resultados Saber Pro*.
- 47/50 con artefacto y datos (46 en ciclo 1); los "sin respuesta" restantes
  son honestos (datos que el Estado no publica como tabla consultable).
- Forma: "cuánto ha subido la tarifa" ya entrega LÍNEA de 19 años; los temas
  nuevos (Trabajo, Hacienda, Gastos Gubernamentales) ya se mapean.

## Brechas restantes (honestas — para el roadmap)

1. **TIPO "Valor/Total"**: preguntas de monto ("cuánto vale la deuda") aún
   caen en conteo de filas. Necesita un TIPO que sume la métrica principal
   (diseño ya explorado: métrica sumable opcional, Fase B).
2. **Dimensión de alta cardinalidad**: Comparar/Ranking puede agrupar por una
   columna tipo ID (Saber Pro → códigos de estudiante). El curador de columnas
   debería marcar cardinalidad y el template evitarlas.
3. **Preguntas cuyo dato no existe como dataset limpio** (tasa de desempleo
   consolidada DANE, funcionarios+costo de nómina, plata recuperada de
   corrupción): la respuesta correcta es la honestidad + enlace al canal
   oficial — hoy el sistema responde el dataset semánticamente más cercano,
   con su nombre visible (transparente pero mejorable con un umbral de
   "suficientemente cercano").
4. **Respuestas compuestas** (KPI + tendencia + desglose en una vista, tasas
   por 100k hab., % además del absoluto): son la visión del producto — exigen
   ejecutar más de una plantilla por pregunta y cruzar con población.
