# Lecciones aprendidas — DatosVivos

Bugs no obvios, gotchas de librerías, y decisiones empíricas que ya pillamos en el camino. **Capturadas para que el próximo desarrollador (humano o IA) no repita la pesquisa.**

Ordenadas por sprint y fecha.

---

## Sprint 1 (May 2026)

### 🐛 Comentarios inline en `.env` rompen pydantic-settings

**Síntoma:** `Settings.socrata_app_token` cargaba el string `"# Opcional: mayor rate limit"` como valor — no `None`. Resultado: el header `X-App-Token` se enviaba con un comentario y Socrata respondía `permission_denied`.

**Causa:** pydantic-settings (vía python-dotenv) lee `KEY=value # comment` como `value=" value # comment"`, no como `value=""` con un comentario separado.

**Solución:**
1. `.env.example` reescrito con comentarios solo en líneas propias (nunca al lado de un valor).
2. Validator defensivo en `mcp_server/settings.py` que convierte strings que empiezan con `#` a `None`.

**Aplicabilidad:** Cualquier campo `Optional[str]` que se carga desde `.env`. Si veo un valor `str | None` cuyo default es `None` y llega con un `#`, hay que sanitizarlo.

---

### 🐛 User-Agent `python-httpx/*` está bloqueado por Socrata

**Síntoma:** httpx defaultea su UA a `python-httpx/0.28.1`. Socrata responde 403 `Forbidden` a requests con este UA en SODA API. Las APIs Discovery y Metadata sí lo aceptan.

**Causa:** Socrata tiene reglas anti-bot que bloquean UAs conocidos de scrapers.

**Solución:** Todos los clientes Socrata (`SodaClient`, `DiscoveryClient`, `MetadataClient`) envían UA propio:
```
User-Agent: DatosVivos/0.1 (+https://github.com/jsricop/DatosVivos)
```

**Aplicabilidad:** Cualquier cliente HTTP nuevo contra Socrata debe poner UA propio. Verificable con `curl -A "python-httpx/..." https://...` vs UA personalizado.

---

### 🐛 `FastMCP("name")` ignora `MCP_PORT` del entorno

**Síntoma:** Server arrancado con `MCP_PORT=3000` se bindeaba a `127.0.0.1:8000`.

**Causa:** `FastMCP("name")` sin `host`/`port` usa los defaults del SDK (8000, 127.0.0.1). No lee env vars propias del usuario.

**Solución:** Instanciar como:
```python
FastMCP("datosvivos", host=settings.mcp_host, port=settings.mcp_port)
```

**Aplicabilidad:** Cualquier nueva instancia de FastMCP debe pasar host/port explícitos. El default es ENGAÑOSO porque parece que `MCP_PORT` "debería funcionar" pero no aplica.

---

### 🐛 FastMCP serializa `list[dict]` como N TextContent blocks

**Síntoma:** Al consumir `call_tool` desde un cliente MCP externo (SSE o stdio), una tool que retorna `list[dict]` no devuelve un solo bloque con la lista — devuelve **N bloques TextContent**, uno por item.

**Implicación:** Si tu cliente solo lee `result.content[0].text`, ve solo el primer item, no la lista.

**Solución:** Iterar sobre todos los `content` blocks y deserializar cada `text`:
```python
items = [json.loads(b.text) for b in result.content if getattr(b, "text", None)]
```

**Aplicabilidad:** Tests de integración SSE/stdio, helpers de cliente, y cualquier consumidor que llame tools que devuelven listas.

---

### 💡 Los mensajes de error de Socrata son oro para el LLM

**Contexto:** Cuando un SoQL es inválido, Socrata devuelve 400 con un JSON detallado:
```json
{
  "code": "query.compiler.malformed",
  "error": true,
  "message": "Could not parse SoQL query 'SELECT WHERE FROM' at line 1 character 14: Expected an expression, but got `FROM'"
}
```

**Por qué importa:** En Sprint 3, Ollama va a generar SoQL y se va a equivocar. Si recibe solo `HTTP 400`, abandona. Si recibe el mensaje real, puede **corregir su query y reintentar**.

**Solución:** Helper `mcp_server/tools/_errors.py::call_socrata()` extrae el campo `message` del JSON de error y lo expone vía `ToolError`.

**Aplicabilidad:** Toda nueva tool que llame APIs externas debe propagar el detalle del error a `ToolError`, no esconderlo detrás de "request failed".

---

### 💡 Discovery API es federada, NO solo Colombia

**Contexto:** `https://api.us.socrata.com/api/catalog/v1` indexa **todos** los portales Socrata del mundo (NYC, Chicago, CDC, gobiernos australianos, etc.). El parámetro `domains=` filtra por portal específico.

**Implicación para el proyecto:** El MCP Server es trivialmente extensible a otros portales. Cambiar `domains=www.datos.gov.co` por `domains=www.datos.gov.co,data.cityofnewyork.us` permite búsqueda cross-país.

**Limitación:** Solo Discovery es federada. Para queries reales (SODA) y metadata, hay que ir al dominio host del dataset. Generalizar `SodaClient` para recibir el dominio dinámicamente es un cambio de 2-3 líneas.

**Aplicabilidad:** Punto de venta para el criterio "Impacto y escalabilidad" (20 pts del concurso).

---

### 💡 Documentación aspiracional acumula deuda silenciosa

**Contexto:** El scaffolding inicial dejó README, `docker-compose.yml` y un docstring listando funcionalidades que aún no existían (`cross_datasets` en MCP, `docker compose up` con servicios stub). Auditoría posterior detectó las inconsistencias.

**Lección:** Documentar lo que **funciona hoy**, no lo que va a funcionar. Lo aspiracional va en una sección explícita "Lo que NO funciona aún" o con marcador `Sprint X`.

**Solución estructural:** Regla `MAIN.md §14.5` Disciplina de documentación — toda PR debe actualizar la documentación afectada con checklist explícito.

**Aplicabilidad:** Cualquier README/docstring/compose nuevo en el proyecto. Revisar en cada code review.

---

## Sprint 2 (en curso)

### 📋 Adopción de disciplina test-first

**Contexto:** Cerrando Sprint 1, declaré "100% verificado" en PR #2. El stakeholder pidió segunda auditoría y aparecieron 4 huecos reales (transporte stdio no probado, paths de error no testeados, etc.). En PR #3 cerramos los huecos, pero la raíz del problema fue **escribir tests después del código** — los tests medían lo que se construyó, no lo que el sprint prometía.

**Lección:** sin definir criterios de aceptación **antes** de implementar, la verificación final tiende a ser un autoengaño confirmatorio.

**Práctica adoptada para Sprint 2 en adelante (documentada como regla en `MAIN.md §6.6`):**

1. Antes de tocar código de producción, escribir `tests/test_sprintN_acceptance.py` con todos los tests congelados (`@pytest.mark.skip`).
2. Commitear a `develop` como "frozen baseline".
3. Durante el sprint, quitar el `@skip` test por test cuando cada feature está lista.
4. **Si un test falla:** corregir el código, NO el test. Excepción única para errores conceptuales del test (con justificación explícita en commit y MAIN.md).
5. Umbrales obligatoriamente cuantificables (accuracy ≥ 0.85, latencia P50 < 200ms, etc.). Nada de "que funcione razonablemente".

**Por qué importa para el concurso:** el criterio "Análisis y rigor técnico" (15 pts) evalúa metodología. Tener tests congelados antes de implementar es evidencia documental de rigor; tests post-hoc no lo son.

**Aplicabilidad:** todos los Sprints 2-5. Sprint 1 ya cerrado con la deuda (capturada aquí). El archivo `tests/test_sprint2_acceptance.py` es el primer ejemplo de la práctica.

---
