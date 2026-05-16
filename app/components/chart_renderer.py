"""Renderiza gráficos Plotly a partir de resultados de consulta.

Auto-detección por tipo de columna del DataFrame:
- Si hay columna datetime + numérica → serie temporal (line chart).
- Si hay columna categórica + numérica → barras agrupadas.
- Si hay dos columnas numéricas → scatter.
- Fallback: None (el caller debe mostrar tabla).
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def render_chart(df: pd.DataFrame) -> go.Figure | None:
    """Devuelve una figura Plotly elegida automáticamente, o None si no aplica."""
    if df is None or df.empty:
        return None

    datetime_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    categorical_cols = [
        c
        for c in df.columns
        if not pd.api.types.is_numeric_dtype(df[c])
        and not pd.api.types.is_datetime64_any_dtype(df[c])
    ]

    if datetime_cols and numeric_cols:
        return px.line(df, x=datetime_cols[0], y=numeric_cols[0])

    if categorical_cols and numeric_cols:
        return px.bar(df, x=categorical_cols[0], y=numeric_cols[0])

    if len(numeric_cols) >= 2:
        return px.scatter(df, x=numeric_cols[0], y=numeric_cols[1])

    return None
