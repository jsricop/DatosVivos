"""Tool MCP: cross_datasets — cruza N datasets (1 a 5) por columnas compartidas.

Diferenciador del proyecto (MAIN.md §8.4). Permite combinar datasets publicados
por entidades distintas usando claves canónicas (DIVIPOLA, código DANE, NIT,
departamento, municipio).

Algoritmo:
1. Validar N (1 ≤ N ≤ MAX_DATASETS) y forma de `join_keys`.
2. Descargar el primer dataset.
3. Para cada dataset adicional:
   a. Descargar (cap por dataset).
   b. Verificar que la `join_key` correspondiente existe en ambos lados.
   c. Ejecutar `pandas.merge` (inner). Short-circuit si queda vacío.
4. Aplicar filtro de columnas (`select_columns`) si se entrega.
5. Cap final sobre el resultado merged.

Decisiones de diseño anti-falsos-positivos:
- NO auto-detectamos columnas comunes. La key DEBE ser explícita; dos datasets
  pueden compartir nombre `id` con significados distintos.
- Verificación previa al merge: si la key falta, error que identifica qué
  dataset rompió la cadena (en vez de un merge silencioso vacío o ruidoso).
- Cap N=5 datasets para evitar joins runaway.
- Cap per-dataset (default 5.000) + cap final (5.000) — defensa en profundidad.

Decisiones de diseño anti-runaway:
- Short-circuit: si A⨝B = []`, no descargamos C/D/E. Ahorra red y memoria.
- Cap intermedio entre merges (5.000 filas) para evitar explosión cartesiana.

Cardinalidades:
- N=0  → ToolError ("lista vacía")
- N=1  → devuelve filas del único dataset, sin merge. `join_keys` ignorado.
- N=2  → comportamiento pairwise canónico.
- N>=3 → cadena de merges, cada uno verificado.
- N>5  → ToolError ("máximo 5 datasets").
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from ..socrata.soda_client import SodaClient
from ._errors import call_socrata

DEFAULT_PER_DATASET_CAP = 5000
DEFAULT_RESULT_CAP = 5000
MAX_DATASETS = 5


def _normalize_join_keys(join_keys: str | list[str] | None, n_datasets: int) -> list[str]:
    """Devuelve N-1 keys (una por cada paso de merge) o lista vacía si N≤1.

    Reglas:
    - N<=1: keys irrelevantes, devuelve []
    - join_keys string: se replica N-1 veces (mismo nombre en todos los pares)
    - join_keys lista: debe tener exactamente N-1 elementos
    - join_keys None y N>=2: ToolError
    """
    if n_datasets <= 1:
        return []
    if join_keys is None:
        raise ToolError(
            "cross_datasets: con 2 o más datasets se requiere `join_keys`. "
            "Pasa un string (misma columna en todos) o lista de N-1 strings."
        )
    if isinstance(join_keys, str):
        return [join_keys] * (n_datasets - 1)
    if isinstance(join_keys, list):
        if len(join_keys) != n_datasets - 1:
            raise ToolError(
                f"cross_datasets: `join_keys` debe tener {n_datasets - 1} elementos "
                f"para {n_datasets} datasets, vi {len(join_keys)}."
            )
        return list(join_keys)
    raise ToolError(
        f"cross_datasets: `join_keys` debe ser string o lista de strings, vi {type(join_keys).__name__}."
    )


def _check_column_in_df(df: pd.DataFrame, column: str, dataset_id: str, role: str) -> None:
    """Lanza ToolError con mensaje útil si `column` no está en el DataFrame."""
    if column not in df.columns:
        cols_preview = sorted(df.columns.tolist())[:15]
        raise ToolError(
            f"cross_datasets: el dataset {dataset_id!r} ({role}) NO tiene la columna "
            f"{column!r} requerida para el merge. Columnas disponibles: {cols_preview}"
        )


def _apply_select(df: pd.DataFrame, select_columns: list[str] | None) -> pd.DataFrame:
    if not select_columns:
        return df
    available = [c for c in select_columns if c in df.columns]
    if not available:
        raise ToolError(
            f"cross_datasets: ninguna de las columnas en select_columns "
            f"{select_columns!r} existe en el resultado. Disponibles: "
            f"{sorted(df.columns.tolist())[:15]}"
        )
    return df[available]


def _to_records(df: pd.DataFrame, cap: int) -> list[dict[str, Any]]:
    if df.empty:
        return []
    if len(df) > cap:
        df = df.head(cap)
    return df.where(pd.notna(df), None).to_dict(orient="records")


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def cross_datasets(
        dataset_ids: list[str],
        join_keys: str | list[str] | None = None,
        select_columns: list[str] | None = None,
        per_dataset_limit: int = DEFAULT_PER_DATASET_CAP,
    ) -> list[dict[str, Any]]:
        """Cruza de 1 a 5 datasets de datos.gov.co por claves compartidas.

        El gran diferenciador del proyecto: permite combinar datasets de entidades
        distintas usando claves territoriales canónicas (DIVIPOLA, código DANE, NIT,
        departamento, municipio). Verifica explícitamente que cada `join_key` exista
        antes del merge para evitar falsos positivos.

        Args:
            dataset_ids: lista de 1 a 5 IDs de datasets (4x4 chars cada uno).
            join_keys: nombre de columna común. Puede ser:
                - string: misma columna en todos los pares (caso común con DIVIPOLA).
                - lista de N-1 strings: una key por cada paso de merge.
                - None: solo válido si N=1.
                NO se auto-detecta para evitar joins espurios.
            select_columns: si se entrega, filtra el resultado a estas columnas.
            per_dataset_limit: máximo de filas a descargar por cada dataset
                (default 5.000, evita cargar a memoria datasets enormes).

        Returns:
            Lista de filas resultantes. Inner join encadenado. Capeada a 5.000 filas.

        Casos especiales:
            - N=1: devuelve las filas del dataset sin merge.
            - Si algún merge intermedio queda vacío, retorna [] inmediatamente
              (short-circuit, no descarga datasets posteriores).
        """
        # Validación de cardinalidad
        if not dataset_ids:
            raise ToolError("cross_datasets: la lista `dataset_ids` está vacía.")
        if len(dataset_ids) > MAX_DATASETS:
            raise ToolError(
                f"cross_datasets: máximo {MAX_DATASETS} datasets por llamada "
                f"(recibí {len(dataset_ids)}). Para joins más grandes considera "
                f"romper la consulta en pasos."
            )

        keys = _normalize_join_keys(join_keys, len(dataset_ids))
        client = SodaClient()

        # Caso N=1: devolver filas sin merge
        if len(dataset_ids) == 1:
            rows = await call_socrata(
                client.query(dataset_id=dataset_ids[0], limit=per_dataset_limit),
                context=f"cross_datasets(single={dataset_ids[0]!r})",
            )
            if not rows:
                return []
            df = pd.DataFrame(rows)
            df = _apply_select(df, select_columns)
            return _to_records(df, DEFAULT_RESULT_CAP)

        # Caso N>=2: cadena de merges con verificación previa
        first_id = dataset_ids[0]
        first_rows = await call_socrata(
            client.query(dataset_id=first_id, limit=per_dataset_limit),
            context=f"cross_datasets(first={first_id!r})",
        )
        if not first_rows:
            return []
        merged = pd.DataFrame(first_rows)
        # Verificar key en el primer dataset (necesaria para el primer merge)
        _check_column_in_df(merged, keys[0], first_id, role="primer dataset de la cadena")

        for i in range(1, len(dataset_ids)):
            next_id = dataset_ids[i]
            step_key = keys[i - 1]

            next_rows = await call_socrata(
                client.query(dataset_id=next_id, limit=per_dataset_limit),
                context=f"cross_datasets(step{i}={next_id!r})",
            )
            if not next_rows:
                return []
            next_df = pd.DataFrame(next_rows)

            # Verificar key en el lado nuevo. El lado izquierdo ya fue verificado
            # en el paso anterior (o al inicio).
            _check_column_in_df(next_df, step_key, next_id, role=f"dataset {i + 1}")

            # Sufijos para columnas con el mismo nombre (excepto la join_key)
            merged = merged.merge(
                next_df,
                on=step_key,
                how="inner",
                suffixes=(f"_{i}", f"_{i + 1}"),
            )

            if merged.empty:
                # Short-circuit: no descargar datasets posteriores
                return []

            # Cap intermedio para evitar explosión cartesiana
            if len(merged) > DEFAULT_RESULT_CAP:
                merged = merged.head(DEFAULT_RESULT_CAP)

        merged = _apply_select(merged, select_columns)
        return _to_records(merged, DEFAULT_RESULT_CAP)
