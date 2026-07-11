# Planteamiento del problema

> **Concurso Datos al Ecosistema 2026: IA para Colombia** · Reto de Innovación y
> Tecnología (Reto 7, id 102) · Equipo 93 · Nivel Avanzado.
> Las cifras de este documento son el corte del **2026-07-10**; el catálogo se
> actualiza automáticamente a diario, por lo que los valores varían.

## El dolor: nadie tiene el panorama

Colombia publica más de **25.000 datasets abiertos** a través de datos.gov.co y de
portales territoriales y sectoriales que federan o publican por su cuenta (IGAC,
Bogotá, Cali, Medellín, Valle del Cauca). Sin embargo, en la práctica:

- **Una entidad no sabe cuántos datasets tiene publicados** ni cuántos están
  actualizados. La respuesta exige recorrer manualmente el portal, dataset por dataset.
- **Un gerente o cabeza de sector con N entidades adscritas no puede hacer control**:
  no existe una vista consolidada que diga qué publica su sector, con qué frescura y
  con qué calidad.
- **El propio MinTIC carece de un panorama consolidado**: los portales federados viven
  separados, con estándares de metadata distintos (Socrata, CKAN, DCAT), y nadie los
  integra en un solo catálogo comparable.
- **El ciudadano que quiere una cifra concreta** necesita saber qué es una API, qué es
  SoQL o cómo descargar y procesar un CSV. La barrera técnica convierte el dato público
  en un dato inaccesible.

La consecuencia es medible con los propios datos del catálogo: al corte del
2026-07-10, **el 71 % de los datasets está "en rojo"** — desactualizado frente a la
frecuencia de actualización que su propia entidad declaró. Ese incumplimiento no es
visible para quien debería corregirlo, porque no existe la herramienta que lo muestre.

## La tesis

**Si no conocemos, no podemos medir. Y si no medimos, no podemos mejorar.**

El dato bien gobernado es infraestructura — tan estratégica como las vías. Pero la
gobernanza empieza por la visibilidad: un tomador de decisiones necesita ver el estado
de los datos abiertos de su entidad, su sector y su territorio de forma rápida y
sencilla, sin intermediar solicitudes técnicas.

## Pregunta problema

¿Cómo dar a los tomadores de decisiones —y a la ciudadanía— una vista consolidada,
siempre actualizada y verificable del ecosistema de datos abiertos de Colombia, que
permita (a) medir la salud del catálogo por entidad, sector y territorio, y
(b) consultar los datos en lenguaje natural sin conocimientos técnicos?

## Alcance de la solución (Reto 7 · Nivel Avanzado)

DatosVivos responde con una **arquitectura de información de tres niveles**:

1. **Panorama nacional** (`datosvivos.co`) — cifras en vivo del catálogo integrado:
   cuántos datasets hay, quién publica, qué tan frescos están, cómo se accede.
2. **Tablero del decisor** (`/tablero`, Power BI) — el detalle explorable con filtros
   por sector, entidad, tipo de acceso y territorio.
3. **Buscador ciudadano** (`/buscar`) — consultas en lenguaje natural resueltas con un
   motor **NL2SQL (Text-to-SQL) con verificación determinista**: cada cifra sale de las
   filas reales del dataset citado, nunca se estima.

El nivel avanzado se materializa en: integración de múltiples fuentes heterogéneas
(6 portales, 3 protocolos), agente de IA para servicios públicos, IA generativa con
verificación, y despliegue funcional en producción.

## Documentos relacionados

- [Marco metodológico](marco_metodologico.md) — CRISP-ML adaptado.
- [Fuentes de datos](fuentes_datos.md) — los 6 portales integrados.
- [Arquitectura](architecture.md) — el sistema completo.
- [Conclusiones](conclusiones.md) — resultados, interpretación e impacto.
