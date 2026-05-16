"""Explorador de datasets del catálogo de datos.gov.co."""

from __future__ import annotations

import asyncio

import pandas as pd
import streamlit as st

from app.components.accessibility import a11y_toggle
from app.components.chart_renderer import render_chart
from app.components.map_renderer import render_map
from mcp_server.socrata.discovery_client import DiscoveryClient
from mcp_server.socrata.metadata_client import MetadataClient
from mcp_server.socrata.soda_client import SodaClient

st.title("🔍 Explorador de datasets")
st.caption("Busca y previsualiza datasets del catálogo de datos.gov.co.")

a11y_toggle.render_a11y_toggle()


@st.cache_resource
def _clients() -> tuple[DiscoveryClient, MetadataClient, SodaClient]:
    return DiscoveryClient(), MetadataClient(), SodaClient()


discovery, metadata, soda = _clients()

query = st.text_input("Palabra clave", placeholder="ej. divipola, salud, transporte…")
limit = st.slider("Resultados máximos", min_value=5, max_value=25, value=10)

if query:
    with st.spinner("Buscando en datos.gov.co…"):
        results = asyncio.run(discovery.search(query=query, limit=limit))
    if not results:
        st.warning("No se encontraron datasets.")
    else:
        rows = [
            {
                "id": r.get("resource", {}).get("id"),
                "nombre": r.get("resource", {}).get("name"),
                "entidad": r.get("resource", {}).get("attribution"),
            }
            for r in results
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

        chosen = st.selectbox("Ver detalle de:", [r["id"] for r in rows])
        if chosen:
            with st.spinner("Cargando metadatos…"):
                meta = asyncio.run(metadata.fetch(chosen))
            st.subheader(meta.get("name", chosen))
            st.write(meta.get("description") or "_(sin descripción)_")

            if st.checkbox("Previsualizar primeras 50 filas"):
                with st.spinner("Consultando filas…"):
                    preview = asyncio.run(soda.query(chosen, soql_query="SELECT * LIMIT 50"))
                df = pd.DataFrame(preview)
                st.dataframe(df, use_container_width=True)

                col1, col2 = st.columns(2)
                with col1:
                    fig = render_chart(df)
                    if fig is not None:
                        st.plotly_chart(fig, use_container_width=True)
                with col2:
                    from streamlit_folium import st_folium

                    st_folium(render_map(df), width=None, height=400)
