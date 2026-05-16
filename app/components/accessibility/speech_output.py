"""Salida por voz vía Web Speech API (`SpeechSynthesis`).

Recibe el texto a narrar (alt-text del gráfico o narrativa del agente) y lo
embebe en un `<script>` que llama a `window.speechSynthesis.speak()` con
idioma `es-CO`. Si el navegador no soporta `speechSynthesis`, el componente
no hace nada (el texto sigue disponible visualmente).
"""

from __future__ import annotations

import json


def render_speech_output(text: str) -> str:
    """HTML que reproduce `text` por TTS al cargarse el componente."""
    safe = json.dumps(text)
    return f"""
    <script>
    (function () {{
      if (!window.speechSynthesis) return;
      const utter = new SpeechSynthesisUtterance({safe});
      utter.lang = "es-CO";
      utter.rate = 1.0;
      utter.pitch = 1.0;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utter);
    }})();
    </script>
    """
