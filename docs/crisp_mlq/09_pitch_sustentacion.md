# 09 — Guion de pitch para sustentación

> Documento operativo para grabación de video / presentación en vivo ante el jurado MinTIC (Jul 14-17 / Final presencial 1ra semana de agosto). **Duración objetivo: 5 minutos.** Pensado para grabar con la app real corriendo en pantalla.

## Estructura (5 min, ±30 s)

| Min | Sección | Mensaje clave |
|---|---|---|
| 0:00–0:30 | Apertura | El problema concreto que resolvemos |
| 0:30–1:30 | Demo 1: chat ciudadano | Pregunta natural → respuesta verificable |
| 1:30–2:30 | Demo 2: cruce de datasets | Combinar 2 entidades sin descargar nada |
| 2:30–3:15 | Demo 3: modo accesible | Entrada por voz y respuesta narrada |
| 3:15–4:15 | Demo 4: MCP en Claude Desktop | El agente es interoperable, no aislado |
| 4:15–5:00 | Cierre | Soberanía, reproducibilidad, cómo verificar |

---

## Apertura (30 s)

> *"En Colombia tenemos más de 8 000 datasets públicos en datos.gov.co. Pero para consultarlos hay que saber qué entidad publica qué, conocer un lenguaje técnico llamado SoQL, y no ofrecen accesibilidad para personas con discapacidad visual.*
>
> *DatosVivos cambia eso. Le habla cualquier persona, en su idioma, y ejecuta la consulta real contra el portal del Estado. Sin inventar números."*

**En pantalla:** logo + URL del repo.

---

## Demo 1 — chat ciudadano (1 min)

**Acción:** abrir Streamlit, página Chat. Escribir:

> *"¿Cuántos municipios tiene Antioquia?"*

**Mostrar:** respuesta del agente con:
- El número (125).
- El dataset citado (`gdxc-w37w`, DIVIPOLA del DANE).
- El permalink al dataset original en `datos.gov.co`.

**Hablar mientras pasa:**

> *"El agente clasificó la pregunta como un conteo, eligió el dataset correcto del DANE — sin que yo mencionara al DANE — y formuló una consulta en SoQL que ejecutó en tiempo real contra el portal. La respuesta cita la fuente y se puede verificar abriendo el dataset original."*

---

## Demo 2 — cruce de datasets (1 min)

**Acción:** segunda pregunta:

> *"Cruza DIVIPOLA con los datos de gobernadores actuales por departamento."*

**Mostrar:** tabla resultado con `cod_dpto`, nombre del departamento, y gobernador.

**Hablar:**

> *"Aquí el agente entendió que necesitaba dos datasets distintos publicados por dos entidades distintas. Hizo un join por código DIVIPOLA — el estándar oficial del DANE — y devolvió la tabla cruzada. No descargué archivos, no escribí pandas, no salí de la app."*

> *"Si los dos datasets no compartieran la clave, el agente diría 'no son cruzables', no inventaría falsos positivos."*

---

## Demo 3 — modo accesible (45 s)

**Acción:** activar toggle de accesibilidad en sidebar. Click en el botón "🎤 Hablar". Decir en voz alta:

> *"Búscame datos sobre vacunación."*

**Mostrar:** el texto se transcribe en el chat. La respuesta del agente se lee en voz alta automáticamente.

**Hablar:**

> *"DatosVivos cumple Ley 1618 de 2013 y WCAG 2.1 AA. Una persona con discapacidad visual puede usar el agente con su voz, escuchar la respuesta, y cada gráfico tiene texto alternativo auto-generado para lectores de pantalla."*

---

## Demo 4 — MCP en Claude Desktop (1 min)

**Acción:** cerrar Streamlit. Abrir Claude Desktop. Mostrar que DatosVivos aparece en el menú de herramientas. Pedir:

> *"Usa DatosVivos para mostrarme los 5 departamentos con más municipios."*

**Mostrar:** Claude llama a `query_data` por debajo, recibe los datos, los muestra ordenados con un mini-gráfico.

**Hablar:**

> *"Esto es lo más diferencial: DatosVivos no es solo una app — es una herramienta interoperable. Publicamos las 4 funciones del agente como un MCP server, el protocolo abierto que adoptaron Anthropic, Google, OpenAI y la comunidad.*
>
> *Cualquier asistente de IA — Claude, Gemini, Cursor, o uno propio de una entidad — puede consumir DatosVivos sin que nadie escriba un conector específico. Una entidad puede ofrecer datos abiertos en su propio asistente corporativo en 5 minutos. Eso es multiplicador real de impacto."*

---

## Cierre (45 s)

**Hablar (con texto en pantalla):**

> *"Tres ideas para llevarse:*
>
> *1. Soberanía: el modelo de IA corre localmente, no enviamos consultas ciudadanas a servidores extranjeros.*
> *2. Verificabilidad: cada respuesta cita la fuente y se puede reproducir; el código es abierto y tiene más de 80 tests automatizados.*
> *3. Interoperabilidad: somos un MCP server estándar, así que multiplicamos impacto sin atar a una sola interfaz.*
>
> *El código está en github.com/jsricop/DatosVivos bajo licencia MIT. La documentación CRISP-ML(Q) completa, el checklist de criterios MinTIC con evidencia, y las guías de integración están en `docs/crisp_mlq/`.*
>
> *Gracias."*

---

## Checklist técnico antes de grabar

- [ ] Ollama corriendo con `qwen2.5-coder:3b` (o 7B si hay hardware).
- [ ] Índice vectorial construido (`python -m scripts.build_index`).
- [ ] Streamlit funcionando en `:8501` con dark theme activo.
- [ ] Claude Desktop configurado con el MCP server (ver `docs/crisp_mlq/07_mcp_integrations.md`).
- [ ] Audio del micrófono OK para la demo de voz (probar `es-CO`).
- [ ] Las preguntas funcionan en seco: 125 municipios de Antioquia, cruce DIVIPOLA + gobernadores, vacunación.
- [ ] Tema dark de Streamlit visible (alto contraste).

## Notas para preguntas del jurado

| Pregunta probable | Respuesta corta |
|---|---|
| *"¿Cómo evitan alucinaciones?"* | El LLM no produce datos, solo formula SoQL. Las respuestas vienen siempre de la API real de Socrata. Si la búsqueda falla, decimos "no encontré" en vez de inventar. |
| *"¿Por qué Qwen 3B y no 7B / GPT-4?"* | Default 3B por hardware del Estado modesto. Upgrade a 7B documentado por `OLLAMA_MODEL`. Backend cloud (Claude, Gemini) configurable con `LLM_BACKEND=anthropic|google`. |
| *"¿Datos personales?"* | No recolectamos PII. No requiere login. El schema PostgreSQL existe como referencia pero no está activado en el MVP. |
| *"¿Y si datos.gov.co cambia?"* | Reindexamos con `python -m scripts.build_index`. El índice es regenerable; los datos siempre son frescos porque consultamos en vivo. |
| *"¿Tests reales o sintéticos?"* | Reales: los tests corren contra `datos.gov.co` y Ollama, no contra mocks. 82 verdes en la suite no-integration. |
| *"¿Open source?"* | MIT en `LICENSE`. Repo público en GitHub. |
| *"¿Una entidad pequeña podría usarlo?"* | Sí: una VM Ubuntu 8 vCPU/16 GB RAM corre el stack completo. Sin licencias pagas si se queda con Ollama local. |
