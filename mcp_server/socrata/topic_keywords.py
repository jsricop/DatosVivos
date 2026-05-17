"""Topic keywords + fallback iterativo (Tier 2 del flujo de búsqueda — ADR-007).

Cuando `expand_query` (Tier 1, acrónimos) no aporta y Socrata devuelve `[]`,
este módulo ranquea entidades por overlap de palabras-clave temáticas con la
query, agrupa de a 2, e intenta búsquedas sucesivas hasta encontrar resultados
o agotar las opciones.

Datos: `topic_keywords_data.KEYWORDS_BY_CANONICAL` — generado por
`scripts/extract_topic_keywords.py` desde el catálogo real de datos.gov.co.

Diseño anti-inundación de query:
- Cap de 2 entidades por grupo: 5+ canonicals en una sola query genera ruido
  excesivo en el matching de Socrata.
- Iteración: si grupo 1 falla, prueba grupo 2; luego grupo 3; etc.
- Determinista: misma query → mismo orden de grupos.

NO se ejecuta cuando Tier 1 (acrónimos) ya expandió la query; la lógica de
fallback vive en el caller (`DiscoveryClient.search`).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from .topic_keywords_data import KEYWORDS_BY_CANONICAL

if TYPE_CHECKING:
    from .discovery_client import DiscoveryClient

GROUP_SIZE = 2


def _tokenize(text: str) -> set[str]:
    """Tokens en minúscula. Soporta acentos. Útil para overlap."""
    return set(re.findall(r"[a-záéíóúüñ]+", text.lower()))


def topic_match_ranked(query: str) -> list[list[str]]:
    """Devuelve grupos de entidades ordenadas por overlap de keywords.

    Cada grupo tiene a lo más `GROUP_SIZE` (=2) canonicals. La lista exterior
    está ordenada por relevancia descendente.

    Args:
        query: pregunta en lenguaje natural del usuario.

    Returns:
        list[list[str]] donde cada inner list contiene 1-2 canonicals.
        Lista vacía si ninguna entidad matchea ningún keyword.
    """
    if not query or not query.strip():
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    # Score = cantidad de keywords de la entidad que aparecen en la query
    scored: list[tuple[str, int]] = []
    for canonical, keywords in KEYWORDS_BY_CANONICAL.items():
        kw_tokens = {kw.lower() for kw in keywords}
        overlap = len(query_tokens & kw_tokens)
        if overlap > 0:
            scored.append((canonical, overlap))

    if not scored:
        return []

    # Orden estable: score desc, luego canonical alfabético para reproducibilidad
    scored.sort(key=lambda x: (-x[1], x[0]))

    # Agrupar de a GROUP_SIZE
    groups: list[list[str]] = []
    current: list[str] = []
    for canonical, _ in scored:
        current.append(canonical)
        if len(current) >= GROUP_SIZE:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


async def expand_with_topics_iterative(
    client: DiscoveryClient,
    query: str,
    limit: int = 10,
    max_groups: int | None = None,
) -> list[dict[str, Any]]:
    """Búsqueda con fallback iterativo por grupos de topic keywords.

    Algoritmo:
        1. Buscar con `query` tal cual (sin expandir). Si hay resultados, retornar.
        2. Calcular grupos rankeados de canonicals con `topic_match_ranked`.
        3. Para cada grupo (en orden de rank):
           a. Construir query expandida: `query + " " + canonical_1 + " " + canonical_2`
           b. Buscar contra Socrata.
           c. Si devuelve resultados, retornar (short-circuit).
        4. Si todos los grupos fallan, retornar `[]`.

    Args:
        client: instancia de `DiscoveryClient` (ya instanciada, no creamos otra).
        query: texto NL del usuario (asumimos que Tier 1 acrónimos ya falló).
        limit: límite Socrata por intento.
        max_groups: tope de grupos a probar (default: todos).

    Returns:
        Lista de resultados Socrata del primer grupo que devolvió no-vacío,
        o `[]` si se agotaron todos los grupos.
    """
    # Intento 0: query base
    base_results = await client.search(query=query, limit=limit)
    if base_results:
        return base_results

    groups = topic_match_ranked(query)
    if not groups:
        return []
    if max_groups is not None:
        groups = groups[:max_groups]

    for group in groups:
        if not group:
            continue
        expanded = query + " " + " ".join(group)
        results = await client.search(query=expanded, limit=limit)
        if results:
            return results

    return []
