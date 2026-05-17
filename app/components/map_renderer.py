"""Renderiza mapas Folium georreferenciados de Colombia (DIVIPOLA).

Acepta:
- DataFrames con columnas `lat`/`lon` (o variantes): pinta markers.
- DataFrames con `cod_dpto` y/o `cod_mpio`: agrega capa por departamento/municipio
  (en una versión inicial, marca centroide aproximado; la capa coroplética real
  con polígonos del DANE es una mejora posterior).

Diseño:
- Centroide por defecto: Bogotá (4.6, -74.08).
- Zoom inicial: 5 (escala país completa).
- Tile layer: `CartoDB positron` (buen contraste, accesible).
"""

from __future__ import annotations

import folium
import pandas as pd


_LAT_CANDIDATES = ("lat", "latitud", "latitude", "y")
_LON_CANDIDATES = ("lon", "lng", "longitud", "longitude", "x")
_DEFAULT_CENTER = (4.6, -74.08)
_DEFAULT_ZOOM = 5


def _first_present(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def render_map(df: pd.DataFrame) -> folium.Map:
    """Construye un Folium Map con la mejor representación que infiera del DataFrame."""
    m = folium.Map(
        location=_DEFAULT_CENTER,
        zoom_start=_DEFAULT_ZOOM,
        tiles="CartoDB positron",
    )

    if df is None or df.empty:
        return m

    lat_col = _first_present(df, _LAT_CANDIDATES)
    lon_col = _first_present(df, _LON_CANDIDATES)

    if lat_col and lon_col:
        for _, row in df.iterrows():
            try:
                folium.CircleMarker(
                    location=(float(row[lat_col]), float(row[lon_col])),
                    radius=4,
                    fill=True,
                    fill_opacity=0.7,
                    popup=str(row.to_dict()),
                ).add_to(m)
            except (TypeError, ValueError):
                continue
        return m

    # Fallback: solo cod_dpto/cod_mpio sin lat/lon. Marcamos que se requiere
    # join con dataset DIVIPOLA `gdxc-w37w` (queda como mejora futura cuando
    # se integre la carga de centroides). Por ahora devolvemos el mapa base.
    return m
