# Accesibilidad — Modo Inclusivo

DatosVivos incluye un **modo de accesibilidad** activable por toggle en la interfaz, diseñado para personas con discapacidad visual. Cuando está activo, el sistema permite dictar la consulta por voz y escuchar la respuesta completa narrada, incluyendo una descripción hablada de los gráficos generados.

**Alcance para el concurso:** demostración funcional en navegador de escritorio (Chrome/Edge). No es un lector de pantalla completo — es un modo de interacción por voz integrado al flujo de DatosVivos.

## Flujo con accesibilidad activa

```
Usuario activa toggle ♿ "Modo Accesible"
         │
         ▼
┌─────────────────────────────┐
│  1. ENTRADA POR VOZ         │
│  Web Speech API              │
│  (SpeechRecognition)         │
│  Navegador captura audio     │
│  → convierte a texto         │
│  → texto entra al pipeline   │
│    normal de DatosVivos      │
└──────────────┬──────────────┘
               │
               ▼
      [ Motor de IA — mismo flujo que consulta escrita ]
               │
               ▼
┌─────────────────────────────┐
│  2. RESPUESTA NARRADA       │
│  Web Speech API              │
│  (SpeechSynthesis)           │
│  Texto del análisis          │
│  → narrado automáticamente   │
│  Velocidad/volumen ajustable │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  3. DESCRIPCIÓN DE GRÁFICOS │
│  Ollama genera narrativa:    │
│  "Este gráfico muestra que   │
│   Boyacá tiene 12 datasets   │
│   de educación, el doble     │
│   que Chocó con 6"           │
│  → narrado vía TTS           │
└─────────────────────────────┘
```

## Implementación técnica

### Speech-to-Text (entrada por voz)

- API: `window.SpeechRecognition` (Web Speech API del navegador)
- Idioma: `lang = 'es-CO'` (español Colombia)
- Integración con Streamlit: componente HTML custom embebido vía `st.components.v1.html()`
- El texto reconocido se inyecta en el campo de chat de Streamlit vía JavaScript → Python callback
- No requiere modelo adicional, no consume RAM del servidor

### Text-to-Speech (salida por voz)

- API: `window.speechSynthesis` (Web Speech API del navegador)
- Voz: se selecciona automáticamente la voz en español disponible en el SO del usuario
- Parámetros ajustables: `rate` (velocidad), `volume`, `pitch`
- Se ejecuta sobre el texto del análisis generado por Ollama
- Control: botones de play/pausa/stop en la interfaz

### Descripción narrativa de gráficos

- Cuando se genera un gráfico (Plotly), se extrae el data summary (ejes, valores clave, tendencia)
- Se envía a Ollama con un prompt específico: *"Describe este gráfico en lenguaje natural para una persona que no puede verlo"*
- El resultado se muestra como texto debajo del gráfico Y se narra vía TTS
- Prompt template: [`ai_engine/prompts/chart_description.txt`](../ai_engine/prompts/chart_description.txt)

### UI del modo accesible

- Toggle en sidebar: "♿ Modo Accesible"
- Cuando activo: aparece botón de micrófono 🎤 junto al campo de chat
- Cuando activo: cada respuesta se narra automáticamente (con opción de silenciar)
- Cuando activo: gráficos incluyen descripción narrativa debajo
- Alto contraste opcional (toggle separado)
- Fuente ampliable (controles +/- en sidebar)

## Compatibilidad

| Navegador | STT | TTS | Notas |
|-----------|-----|-----|-------|
| Chrome (escritorio) | ✅ | ✅ | Mejor soporte, recomendado para demo |
| Edge (escritorio) | ✅ | ✅ | Funciona bien, voces de buena calidad |
| Firefox (escritorio) | ⚠️ | ✅ | STT limitado, TTS funciona |
| Safari | ❌ | ✅ | STT no soportado |
| Móvil | ⚠️ | ⚠️ | Variable — fuera de alcance del concurso |

**Para la demo ante el jurado:** usar Chrome en escritorio.

## Marco normativo

- **Ley 1618 de 2013 (Colombia):** garantiza el derecho de las personas con discapacidad al acceso a las TIC
- **WCAG 2.1 nivel AA:** estándar internacional de accesibilidad web — DatosVivos apunta a cumplimiento parcial (contraste, navegación por teclado, alternativas textuales)
- **Política de Gobierno Digital (MinTIC):** promueve la accesibilidad en servicios digitales del Estado

## Lo que NO está en alcance (para el concurso)

- Navegación completa por teclado de todos los componentes de Streamlit
- Compatibilidad completa con lectores de pantalla (JAWS, NVDA)
- Soporte móvil
- Traducción a lengua de señas
- Certificación formal WCAG 2.1

Estos son posibles en una versión de producción futura, pero exceden el alcance del concurso.
