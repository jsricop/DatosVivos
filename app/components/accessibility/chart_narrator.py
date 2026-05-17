"""Genera alt-text descriptivo para un gráfico/tabla de resultados.

El alt-text resume el DataFrame en lenguaje natural (español) para lectores de
pantalla y como `aria-label` del componente Plotly. NO usa LLM: una descripción
estadística determinista es preferible porque siempre está disponible, es
reproducible y no añade latencia.

El LLM puede tomar el alt-text como insumo para una narración más elaborada en
TTS si el usuario activa esa funcionalidad — esa pieza vive en `speech_output`.
"""

from __future__ import annotations

import pandas as pd


def narrate_chart(df: pd.DataFrame) -> str:
    """Devuelve un texto descriptivo del DataFrame para uso como alt-text.

    Siempre devuelve al menos 20 chars (suficiente para que un screen reader
    diga algo útil); para DataFrames vacíos devuelve una nota explícita.
    """
    if df is None or len(df) == 0:
        return "Gráfico vacío: no hay datos para mostrar en este momento."

    rows, cols = df.shape
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cat_cols = [
        c
        for c in df.columns
        if not pd.api.types.is_numeric_dtype(df[c])
        and not pd.api.types.is_datetime64_any_dtype(df[c])
    ]

    parts: list[str] = [f"Gráfico con {rows} filas y {cols} columnas."]

    if numeric_cols:
        first_num = numeric_cols[0]
        serie = df[first_num].dropna()
        if not serie.empty:
            parts.append(
                f"La columna numérica «{first_num}» varía entre "
                f"{serie.min():.2f} y {serie.max():.2f}, con promedio "
                f"{serie.mean():.2f}."
            )

    if cat_cols:
        first_cat = cat_cols[0]
        n_unique = df[first_cat].nunique(dropna=True)
        parts.append(
            f"La columna categórica «{first_cat}» tiene {n_unique} valores distintos."
        )

    return " ".join(parts)
