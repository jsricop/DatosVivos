"""Página de chat conversacional para consultas en lenguaje natural."""

from __future__ import annotations

import time

import streamlit as st

from ai_engine.telemetry import log_query
from app.agent_client import AgentClient
from app.components.accessibility import a11y_toggle
from app.components.accessibility.speech_output import render_speech_output

st.title("💬 Chat con DatosVivos")
st.caption("Pregunta en lenguaje natural sobre los datos abiertos de Colombia.")

st.info(
    "🧪 **Versión beta** · Las respuestas pueden tardar 30-90 s mientras el "
    "modelo local consulta `datos.gov.co`. Las **cifras** siempre aparecen "
    "en el bloque «📊 Datos verificados» — son calculadas determinísticamente "
    "con pandas sobre los rows reales (cero alucinación). Los enlaces a las "
    "fuentes te permiten verificarlo tú mismo."
)

a11y_state = a11y_toggle.render_a11y_toggle()


@st.cache_resource
def _get_client() -> AgentClient:
    return AgentClient()


client = _get_client()

if "messages" not in st.session_state:
    st.session_state.messages = []

def _render_rows_table(rows: list, max_rows: int = 50) -> None:
    """Muestra los rows literales devueltos por Socrata como tabla colapsable.

    PROD_IMPROV #10: el ciudadano puede ver los datos crudos que respaldan
    cada cifra, no solo el resumen pandas. Esto refuerza la trazabilidad y
    es lo que el jurado MinTIC va a auditar caso por caso.
    """
    if not rows:
        return
    import pandas as pd

    df = pd.DataFrame(rows[:max_rows])
    with st.expander(
        f"📋 Ver tabla cruda de Socrata ({len(rows)} fila{'s' if len(rows) != 1 else ''})",
        expanded=False,
    ):
        st.dataframe(df, hide_index=True, use_container_width=True)
        if len(rows) > max_rows:
            st.caption(
                f"Mostrando primeras {max_rows} de {len(rows)} filas. "
                f"Para más: abre la fuente original abajo."
            )


def _render_dataset_references(refs: list) -> None:
    """Muestra los datasets como enlaces verificables a datos.gov.co.

    Cada cita es accionable: el ciudadano puede abrir la fuente, descargar
    los datos y reusarlos. Trazabilidad obligatoria por requisito jurado.
    """
    if not refs:
        return
    st.markdown("**📚 Fuentes consultadas (verifícalo tú mismo):**")
    for r in refs:
        entity = r.get("entity") if isinstance(r, dict) else r.entity
        name = r.get("name") if isinstance(r, dict) else r.name
        url = r.get("url") if isinstance(r, dict) else r.url
        api_url = r.get("api_url") if isinstance(r, dict) else r.api_url
        rid = r.get("id") if isinstance(r, dict) else r.id
        entity_str = f" — *{entity}*" if entity else ""
        st.markdown(
            f"- [{name}]({url}){entity_str}  \n"
            f"  `id: {rid}` · "
            f"[ver dataset]({url}) · "
            f"[API JSON]({api_url})"
        )


def _refs_to_dicts(refs: list) -> list[dict]:
    out: list[dict] = []
    for r in refs:
        if isinstance(r, dict):
            out.append(r)
        else:
            out.append(
                {
                    "id": r.id,
                    "name": r.name,
                    "entity": r.entity,
                    "url": r.url,
                    "api_url": r.api_url,
                }
            )
    return out


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        _render_dataset_references(msg.get("references") or [])

question = st.chat_input("Escribe tu pregunta sobre datos.gov.co…")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Analizando…"):
            t0 = time.time()
            result = client.ask(question)
            elapsed = time.time() - t0
        st.markdown(result.narrative or "_(sin respuesta)_")
        # Tabla cruda de rows (expandible) — auditabilidad para el jurado.
        _render_rows_table(getattr(result, "rows", []) or [])
        refs = getattr(result, "dataset_references", []) or []
        _render_dataset_references(refs)

        # Telemetría: best-effort, no rompe la UI si falla.
        narrative_text = result.narrative or ""
        censored = narrative_text.lower().count(
            "consulta el bloque de datos verificados"
        ) + narrative_text.count("no verificable")
        log_query(
            question=question,
            intent=getattr(result, "intent", ""),
            datasets_used=list(getattr(result, "datasets_used", []) or []),
            soql_executed=getattr(result, "soql_executed", None),
            rows_count=len(getattr(result, "rows", []) or []),
            censored_count=censored,
            elapsed_s=elapsed,
            had_statistics=getattr(result, "statistics", None) is not None,
        )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result.narrative,
            "references": _refs_to_dicts(refs),
        }
    )

    if a11y_state.get("tts_enabled") and result.narrative:
        import streamlit.components.v1 as components

        components.html(render_speech_output(result.narrative), height=0)
