"""Información del proyecto, equipo y referencias."""

from __future__ import annotations

import streamlit as st

from app.components.accessibility import a11y_toggle

st.title("ℹ️ Acerca de DatosVivos")
a11y_toggle.render_a11y_toggle()

st.markdown(
    """
## ¿Qué es DatosVivos?

Un agente de IA que permite a cualquier ciudadano hacer preguntas en lenguaje
natural sobre los datos públicos de Colombia, ejecutando consultas reales sobre
[datos.gov.co](https://www.datos.gov.co), cruzando datasets de múltiples
entidades y entregando análisis verificables con visualizaciones.

## ¿Cómo funciona?

1. **MCP Server** — expone 4 tools sobre las APIs de Socrata de datos.gov.co
   (`search_datasets`, `get_metadata`, `query_data`, `cross_datasets`).
2. **Motor de IA** — clasificador de intención + índice vectorial de metadatos
   + generador local (Ollama / Qwen 2.5 Coder).
3. **Interfaz Streamlit** — chat conversacional, explorador de datasets,
   visualizaciones Plotly/Folium y modo accesible (Web Speech API).

## Accesibilidad

DatosVivos incluye un modo accesible activable desde el sidebar:

- **Entrada por voz** (STT, Web Speech API en `es-CO`).
- **Salida por voz** (TTS opcional para narrar las respuestas).
- **Alt-text** auto-generado por cada gráfico.
- **Tema dark** de alto contraste, navegación por teclado.

Cumple **Ley 1618 de 2013** (estatuto de discapacidad de Colombia) y
**WCAG 2.1 AA**.

## Concurso

Construido para el concurso **"Datos al Ecosistema 2026: IA para Colombia"**
del Ministerio TIC — Reto #07 (Innovación y Tecnología). Equipo: Oficina de
Tecnología de la **ANI** (Agencia Nacional de Infraestructura).
"""
)
