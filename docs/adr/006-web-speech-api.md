# ADR-006: Web Speech API del navegador para accesibilidad

**Estado:** Aceptada
**Fecha:** Sprint 4

## Decisión

Usar las **APIs nativas del navegador** (`SpeechRecognition` + `SpeechSynthesis`) para entrada/salida por voz, en vez de modelos locales (Whisper + Piper TTS).

## Razón

- **Cero infraestructura adicional.** No hay que servir Whisper ni cargar otro modelo en memoria.
- **Cero RAM adicional** en la VM del Estado (la RAM disponible se reserva para Qwen + embeddings).
- **Funciona en cualquier navegador moderno de escritorio** (Chrome, Edge, Firefox). Permite demostrar el modo accesible sin agregar complejidad al stack.
- **Estándar abierto** (W3C Web Speech API).

## Trade-off

- **Dependencia del navegador.** Safari iOS y algunos móviles tienen soporte limitado o inexistente. Solo garantizado para escritorio.
- **Calidad de voz variable** según el sistema operativo del usuario (la SO provee la voz TTS).
- **Fallback obligatorio.** El componente `speech_input.py` detecta cuando `SpeechRecognition` no existe y se deshabilita con `aria-label` informativo; la página mantiene `st.chat_input` como entrada canónica.

## Migración futura

Para producción seria, Whisper local + Piper TTS daría mejor calidad y portabilidad — pero a costo de ~2 GB de RAM adicional. Evaluable cuando el hardware lo permita.

## Estándares de referencia

- WCAG 2.1 nivel AA
- Ley 1618 de 2013 (Colombia, accesibilidad de TIC)

## Referencias

- `app/components/accessibility/speech_input.py`
- `app/components/accessibility/speech_output.py`
- [`docs/accessibility.md`](../accessibility.md)
