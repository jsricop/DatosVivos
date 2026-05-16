"""Entrada por voz vía Web Speech API (`SpeechRecognition`).

Embebida con `streamlit.components.v1.html`. Idioma: `es-CO`.

Fallback: cuando el navegador NO soporta `webkitSpeechRecognition` (Firefox
desktop, Safari iOS sin permisos, etc.), el componente se oculta y la página
debe seguir mostrando `st.chat_input` como entrada principal. Las páginas de
chat usan `st.chat_input` como entrada canónica y este componente como ayuda
opcional (no reemplazo).
"""

from __future__ import annotations


_HTML_TEMPLATE = """
<div id="dv-speech-wrapper" style="display:flex;align-items:center;gap:8px;">
  <button id="dv-speech-btn" type="button"
          style="background:#3b82f6;color:#fff;border:none;border-radius:6px;
                 padding:8px 14px;cursor:pointer;font-size:14px;"
          aria-label="Activar entrada por voz">
    🎤 Hablar
  </button>
  <span id="dv-speech-status" style="color:#94a3b8;font-size:13px;" aria-live="polite">
    Listo
  </span>
</div>
<script>
(function () {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const btn = document.getElementById("dv-speech-btn");
  const status = document.getElementById("dv-speech-status");

  if (!SR) {
    // Fallback: navegador no soporta Web Speech API.
    // La página de chat ya muestra st.chat_input como entrada canónica,
    // así que aquí solo deshabilitamos el botón con un aria-label informativo.
    btn.disabled = true;
    btn.style.opacity = "0.5";
    btn.style.cursor = "not-allowed";
    btn.setAttribute("aria-label",
      "Entrada por voz no disponible en este navegador. Usa el campo de texto.");
    status.textContent = "No disponible (usa el campo de texto como fallback)";
    return;
  }

  const recognition = new SR();
  recognition.lang = "es-CO";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  btn.addEventListener("click", () => {
    status.textContent = "Escuchando…";
    recognition.start();
  });

  recognition.onresult = (e) => {
    const text = e.results[0][0].transcript;
    status.textContent = "Texto: " + text;
    // Comunica al script Streamlit padre vía postMessage.
    // El padre puede leerlo con window.addEventListener("message").
    window.parent.postMessage(
      { type: "datosvivos-speech", transcript: text },
      "*"
    );
  };

  recognition.onerror = (e) => {
    status.textContent = "Error: " + e.error + " (usa el campo de texto)";
  };

  recognition.onend = () => {
    if (status.textContent === "Escuchando…") {
      status.textContent = "Listo";
    }
  };
})();
</script>
"""


def render_speech_input() -> str:
    """Devuelve el HTML del componente de entrada por voz.

    La página Streamlit lo embebe con `streamlit.components.v1.html(html, height=60)`.
    """
    return _HTML_TEMPLATE
