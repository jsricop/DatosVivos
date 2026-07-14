"""Mapper LLM Natural Language → chips (Hito 1 / Fase 2).

Convierte un texto libre del ciudadano en una combinación de chips que el
motor SoQL/DuckDB puede ejecutar directamente. La barra libre queda como
entrada cómoda; el LLM la traduce a vocabulario controlado.

Contrato:
    map_nl_to_chips(query, available) -> dict[str, str | None]

donde:
    query        : texto libre del usuario.
    available    : dict con las listas de chips vivos:
        {
          "tema":       [str, ...],   # DISTINCT datasets.category
          "territorio": [{"value": "11", "label": "Bogotá D.C."}, ...],
          "entidad":    [{"value": "<id>", "label": "<name>"}, ...]
        }
    return       : {tema, tipo, territorio, entidad, refinador} — cada uno
                   puede ser None si el LLM no inferió con confianza.

El LLM solo puede elegir valores PRESENTES en `available`. La validación
post-LLM descarta cualquier opción que no esté en la lista, evitando
URLs inválidas.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from ai_engine.llm_backend import get_backend, model_for_task

log = logging.getLogger(__name__)

ALLOWED_TIPOS = ("Cuántos", "Comparar", "Ranking", "Tendencia", "Mapa")


def _build_prompt(query: str, available: dict[str, Any]) -> str:
    """Few-shot prompt en español. JSON estricto, valores controlados."""
    temas = available.get("tema") or []
    territorios = available.get("territorio") or []
    entidades = available.get("entidad") or []

    # Compactar listas para no inflar el prompt.
    temas_str = " | ".join(temas[:30])
    territorios_str = " | ".join(
        f"{t['label']} ({t['value']})" for t in territorios[:40]
    )
    entidades_str = " | ".join(
        f"{e['label']} ({e['value']})" for e in entidades[:30]
    )

    return f"""Eres un mapper de español natural a chips de búsqueda para datos abiertos colombianos.

Pregunta del ciudadano:
"{query}"

Vocabulario disponible (debes elegir EXACTO):

TEMA (uno o null):
{temas_str}

TIPO (uno o null): Cuántos | Comparar | Ranking | Tendencia | Mapa

TERRITORIO (uno o null, usa el código entre paréntesis):
{territorios_str}

ENTIDAD (uno o null, usa el id entre paréntesis):
{entidades_str}

Reglas:
- Devuelve SOLO un objeto JSON, sin comentarios ni código markdown.
- Si no estás seguro de un campo, usa null. Es preferible null a equivocarse.
- "Cuántos/cuántas/total/número" → TIPO=Cuántos.
- "Compara/comparar" → TIPO=Comparar.
- "Top/ranking/peores/mejores" → TIPO=Ranking.
- "Evolución/tendencia/serie/año a año" → TIPO=Tendencia.
- "Mapa/por departamento/por municipio" → TIPO=Mapa.
- "Bogotá" → TERRITORIO con código 11. "Capital" también.
- Si menciona una palabra clave específica (ej. "matrícula", "homicidios", "subsidios"), inclúyela en `refinador`.
- En `refinador` añade también el término OFICIAL con que los datos abiertos nombran eso, porque los datasets usan lenguaje institucional: "colegios" → añade "establecimientos educativos instituciones educativas"; "públicos" → añade "oficial"; "plata/gastos" → añade "presupuesto ejecución"; "robos" → añade "hurto". Máximo ~8 palabras en total.

Formato JSON exacto:
{{"tema": "<TEMA o null>", "tipo": "<TIPO o null>", "territorio": "<código o null>", "entidad": "<id o null>", "refinador": "<palabras clave y términos oficiales, o null>"}}

JSON:"""


def _parse_json(text: str) -> dict[str, Any] | None:
    """Extrae el primer objeto JSON {...} del texto, robusto a prefijos
    como ```json y comentarios sueltos del modelo."""
    if not text:
        return None
    # Quitar fences markdown si las hubo.
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    # Buscar el primer { ... } balanceado de manera simple.
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _norm(s: Any) -> str | None:
    if s is None:
        return None
    val = str(s).strip()
    if not val or val.lower() in ("null", "none"):
        return None
    return val


async def map_nl_to_chips(
    query: str, available: dict[str, Any]
) -> dict[str, str | None]:
    """Llama al LLM y valida la respuesta contra los chips disponibles.
    Cualquier valor que no esté en `available` se descarta a None.
    """
    base = {"tema": None, "tipo": None, "territorio": None, "entidad": None, "refinador": None}
    if not query or not query.strip():
        return base

    prompt = _build_prompt(query, available)
    backend = get_backend()
    model = model_for_task("fast")

    try:
        raw = await backend.generate(prompt, max_tokens=200, model=model)
    except Exception as exc:  # noqa: BLE001
        log.warning("nl_to_chips LLM falló: %s", exc)
        return base

    parsed = _parse_json(raw)
    if not parsed:
        log.info("nl_to_chips: no se pudo parsear JSON. Raw: %s", raw[:200])
        return base

    out = base.copy()

    # Tema — debe estar exactamente en la lista.
    tema = _norm(parsed.get("tema"))
    if tema and tema in (available.get("tema") or []):
        out["tema"] = tema

    # Tipo — uno de los 5.
    tipo = _norm(parsed.get("tipo"))
    if tipo in ALLOWED_TIPOS:
        out["tipo"] = tipo

    # Territorio — código DIVIPOLA o macro:caribe.
    # Guardrail: el LLM a veces inventa códigos (eligió 08=Atlántico para
    # "por departamento" genérico). Aceptamos solo si el nombre del
    # territorio APARECE en el query original — protege contra
    # alucinaciones sin depender del prompt.
    territorio = _norm(parsed.get("territorio"))
    if territorio:
        terr_options = available.get("territorio") or []
        valid = {t["value"]: t["label"] for t in terr_options}
        if territorio in valid:
            label = valid[territorio].lower()
            qlow = query.lower()
            mentioned = (
                label in qlow
                or any(tok in qlow for tok in label.split() if len(tok) > 3)
                or (territorio == "nacional" and any(
                    w in qlow for w in ("nacional", "nacionales", "colombia", "país", "pais")
                ))
                or territorio.startswith("macro:")
            )
            if mentioned:
                out["territorio"] = territorio

    # Entidad — entity_id como string.
    # Guardrail equivalente: solo aceptamos si el nombre/abbrev aparece en
    # el query. Esto evita falsos positivos cuando el LLM "salta" a una
    # entidad por inferencia temática.
    entidad = _norm(parsed.get("entidad"))
    if entidad:
        ent_options = available.get("entidad") or []
        valid = {str(e["value"]): e["label"] for e in ent_options}
        if entidad in valid:
            label = valid[entidad].lower()
            qlow = query.lower()
            mentioned = (
                label in qlow
                or any(tok in qlow for tok in label.split() if len(tok) > 3)
            )
            if mentioned:
                out["entidad"] = entidad

    # Refinador — texto libre limitado.
    refinador = _norm(parsed.get("refinador"))
    if refinador:
        out["refinador"] = refinador[:80]

    return out
