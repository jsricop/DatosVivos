"""Tool MCP: cross_datasets — cruza dos datasets por una clave territorial común.

Diferenciador del proyecto (MAIN.md §8.4). Permite combinar datasets publicados
por entidades distintas usando claves canónicas (DIVIPOLA, código DANE, NIT,
departamento, municipio).

Algoritmo:
1. Descarga ambos datasets vía SODA API (cap configurable por lado).
2. Verifica que `join_key` esté presente en ambos esquemas.
3. Ejecuta `pandas.merge` (inner join) por la clave.
4. Aplica filtro de columnas (`select_columns`) si se entrega.
5. Cap final sobre el resultado merged.

Decisiones de diseño:
- Cap por dataset (default 5.000 filas/lado) — protege contra datasets enormes
  que se cargan en memoria. Suficiente para joins por DIVIPOLA municipal (1.122
  municipios totales) o departamental (32 dptos).
- Cap final (5.000 filas) — protege la respuesta MCP de blowups por joins
  cartesianos en caso de keys mal calibradas.
- Inner join — sólo filas con match en ambos lados. Para outer/left, agregar
  parámetro `how` en iteración futura.
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


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def cross_datasets(
        dataset_a_id: str,
        dataset_b_id: str,
        join_key: str,
        select_columns: list[str] | None = None,
        per_dataset_limit: int = DEFAULT_PER_DATASET_CAP,
    ) -> list[dict[str, Any]]:
        """Cruza dos datasets de datos.gov.co por una columna común.

        Útil cuando dos entidades del Estado publican datos del mismo
        territorio (municipios, departamentos) en datasets separados. Por
        ejemplo: presupuesto educativo (MinEducación) cruzado con pobreza
        multidimensional (DANE) por código DIVIPOLA.

        Args:
            dataset_a_id: 4x4 ID del primer dataset.
            dataset_b_id: 4x4 ID del segundo dataset.
            join_key: nombre de columna que existe en ambos datasets
                (ej: 'cod_dpto', 'cod_mpio', 'nit').
            select_columns: si se entrega, filtra el resultado a estas
                columnas (debe incluir `join_key` para que tenga sentido).
            per_dataset_limit: máximo de filas a descargar por lado
                (default 5000, evita descargar datasets enormes a memoria).

        Returns:
            Lista de filas merged (inner join). Capeada a 5000 filas totales.
        """
        client = SodaClient()
        rows_a = await call_socrata(
            client.query(dataset_id=dataset_a_id, limit=per_dataset_limit),
            context=f"cross_datasets(a={dataset_a_id!r})",
        )
        rows_b = await call_socrata(
            client.query(dataset_id=dataset_b_id, limit=per_dataset_limit),
            context=f"cross_datasets(b={dataset_b_id!r})",
        )

        if not rows_a or not rows_b:
            return []

        df_a = pd.DataFrame(rows_a)
        df_b = pd.DataFrame(rows_b)

        if join_key not in df_a.columns:
            raise ToolError(
                f"cross_datasets: la columna {join_key!r} no existe en {dataset_a_id!r}. "
                f"Columnas disponibles: {sorted(df_a.columns.tolist())[:15]}"
            )
        if join_key not in df_b.columns:
            raise ToolError(
                f"cross_datasets: la columna {join_key!r} no existe en {dataset_b_id!r}. "
                f"Columnas disponibles: {sorted(df_b.columns.tolist())[:15]}"
            )

        # Sufijos para columnas con el mismo nombre en ambos lados (excepto join_key)
        merged = df_a.merge(df_b, on=join_key, how="inner", suffixes=("_a", "_b"))

        if merged.empty:
            return []

        if select_columns:
            # Filtra a las columnas pedidas que realmente existen en el merge
            available = [c for c in select_columns if c in merged.columns]
            if not available:
                raise ToolError(
                    f"cross_datasets: ninguna de las columnas en select_columns "
                    f"{select_columns!r} existe en el resultado. Disponibles: "
                    f"{sorted(merged.columns.tolist())[:15]}"
                )
            merged = merged[available]

        if len(merged) > DEFAULT_RESULT_CAP:
            merged = merged.head(DEFAULT_RESULT_CAP)

        # NaN no es JSON-serializable → convertir a None
        return merged.where(pd.notna(merged), None).to_dict(orient="records")
