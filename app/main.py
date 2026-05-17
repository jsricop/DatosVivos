"""Punto de entrada de la app Streamlit. Configura router de páginas y sidebar global."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="DatosVivos — Agente de Datos Abiertos",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = [
    st.Page("pages/chat.py", title="Chat", icon="💬", default=True),
    st.Page("pages/explorer.py", title="Explorador", icon="🔍"),
    st.Page("pages/about.py", title="Acerca de", icon="ℹ️"),
]

nav = st.navigation(pages)
nav.run()
