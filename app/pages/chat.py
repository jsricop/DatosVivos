"""Página de chat conversacional para consultas en lenguaje natural."""

from __future__ import annotations

import streamlit as st

from app.agent_client import AgentClient
from app.components.accessibility import a11y_toggle
from app.components.accessibility.speech_output import render_speech_output

st.title("💬 Chat con DatosVivos")
st.caption("Pregunta en lenguaje natural sobre los datos abiertos de Colombia.")

a11y_state = a11y_toggle.render_a11y_toggle()


@st.cache_resource
def _get_client() -> AgentClient:
    return AgentClient()


client = _get_client()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("datasets"):
            st.caption("Datasets consultados: " + ", ".join(msg["datasets"]))

question = st.chat_input("Escribe tu pregunta sobre datos.gov.co…")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Analizando…"):
            result = client.ask(question)
        st.markdown(result.narrative or "_(sin respuesta)_")
        if result.datasets_used:
            st.caption("Datasets consultados: " + ", ".join(result.datasets_used))

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result.narrative,
            "datasets": result.datasets_used,
        }
    )

    if a11y_state.get("tts_enabled") and result.narrative:
        import streamlit.components.v1 as components

        components.html(render_speech_output(result.narrative), height=0)
