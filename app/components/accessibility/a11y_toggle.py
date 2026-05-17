"""Toggle global del modo accesible en el sidebar de Streamlit.

Expone tres flags via `st.session_state`:
- `a11y_enabled`: si está activado, las páginas habilitan STT/TTS y alt-text expandido.
- `tts_enabled`: leer respuestas en voz alta.
- `stt_enabled`: ofrecer botón de entrada por voz.

Diseño: el toggle vive en el sidebar (siempre visible) para que un usuario
con lector de pantalla pueda encontrarlo en cualquier página.
"""

from __future__ import annotations

import streamlit as st


def render_a11y_toggle() -> dict[str, bool]:
    """Renderiza el bloque de accesibilidad en el sidebar y devuelve el estado actual."""
    with st.sidebar:
        st.markdown("### ♿ Accesibilidad")
        a11y = st.checkbox(
            "Activar modo accesible",
            value=st.session_state.get("a11y_enabled", False),
            key="a11y_enabled",
            help="Habilita lectura en voz alta (TTS) y entrada por voz (STT).",
        )
        tts = st.checkbox(
            "Leer respuestas en voz alta (TTS)",
            value=st.session_state.get("tts_enabled", False),
            key="tts_enabled",
            disabled=not a11y,
        )
        stt = st.checkbox(
            "Habilitar entrada por voz (STT)",
            value=st.session_state.get("stt_enabled", False),
            key="stt_enabled",
            disabled=not a11y,
        )
    return {"a11y_enabled": a11y, "tts_enabled": tts, "stt_enabled": stt}
