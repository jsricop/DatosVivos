"""GET /api/v1/suggest — [DEPRECATED 2026-05-23] reemplazado por /api/v1/chips.

**Estado**: DEPRECADO. Sunset planeado: 2026-07-01.

**Motivo**: este endpoint devolvía slugs (`count`, `seguridad`, `cundinamarca`) que
NO coinciden con el formato esperado por `POST /api/v1/query/chips` (labels
literales como `Cuántos`, `category` real de Socrata como `Seguridad y Defensa`,
códigos DIVIPOLA como `25`).

**Reemplazo**: `GET /api/v1/chips` (router `api/routes/chips.py`). Frontend
migrado en PR #35.

**Por qué no eliminarlo todavía**: posibles clientes externos (MCP, integraciones
de terceros, scripts batch). Los tests `test_rebrand_acceptance.py` también
verifican el contrato — mantenerlo permite que esos tests sigan corriendo como
"contract tests" durante el período de gracia.

Cuando llegue 2026-07-01 sin uso registrado en logs → eliminar este archivo +
quitar router de `api/main.py`.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request, Response

from api.models.schemas import SuggestOption, SuggestResponse

router = APIRouter()
log = logging.getLogger(__name__)

_SUNSET_DATE = "2026-07-01"
_REPLACEMENT_LINK = '</api/v1/chips>; rel="successor-version"'


_TEMA: list[SuggestOption] = [
    SuggestOption(value="salud", label="Salud"),
    SuggestOption(value="educacion", label="Educación"),
    SuggestOption(value="seguridad", label="Seguridad"),
    SuggestOption(value="movilidad", label="Movilidad"),
    SuggestOption(value="justicia", label="Justicia"),
    SuggestOption(value="economia", label="Economía"),
    SuggestOption(value="medio-ambiente", label="Medio Ambiente"),
    SuggestOption(value="vivienda", label="Vivienda"),
    SuggestOption(value="trabajo", label="Trabajo"),
    SuggestOption(value="infraestructura", label="Infraestructura"),
]

_TIPO: list[SuggestOption] = [
    SuggestOption(value="count", label="Cuántos", kicker="Conteo"),
    SuggestOption(value="compare", label="Comparar", kicker="Vs"),
    SuggestOption(value="ranking", label="Ranking", kicker="Top N"),
    SuggestOption(value="trend", label="Tendencia", kicker="Serie temporal"),
    SuggestOption(value="map", label="Mapa", kicker="Territorial"),
]

_TERRITORIO: list[SuggestOption] = [
    SuggestOption(value="nacional", label="Nacional"),
    SuggestOption(value="antioquia", label="Antioquia", kicker="05"),
    SuggestOption(value="bogota", label="Bogotá D.C.", kicker="11"),
    SuggestOption(value="cundinamarca", label="Cundinamarca", kicker="25"),
    SuggestOption(value="valle", label="Valle del Cauca", kicker="76"),
    SuggestOption(value="atlantico", label="Atlántico", kicker="08"),
    SuggestOption(value="santander", label="Santander", kicker="68"),
    SuggestOption(value="boyaca", label="Boyacá", kicker="15"),
    SuggestOption(value="caribe", label="Caribe", kicker="región"),
    SuggestOption(value="pacifico", label="Pacífico", kicker="región"),
]

_ENTIDAD: list[SuggestOption] = [
    SuggestOption(value="minsalud", label="Ministerio de Salud"),
    SuggestOption(value="mineducacion", label="Ministerio de Educación"),
    SuggestOption(value="minjusticia", label="Ministerio de Justicia"),
    SuggestOption(value="policia", label="Policía Nacional"),
    SuggestOption(value="dane", label="DANE"),
    SuggestOption(value="dnp", label="DNP"),
    SuggestOption(value="ani", label="ANI"),
    SuggestOption(value="ica", label="ICA"),
    SuggestOption(value="invias", label="INVÍAS"),
    SuggestOption(value="ideam", label="IDEAM"),
]


_CATALOG: dict[str, list[SuggestOption]] = {
    "tema": _TEMA,
    "tipo": _TIPO,
    "territorio": _TERRITORIO,
    "entidad": _ENTIDAD,
}


@router.get("/suggest", response_model=SuggestResponse, deprecated=True)
async def suggest(
    request: Request,
    response: Response,
    axis: str = Query(..., description="[DEPRECADO] Eje del chip. Usar GET /chips."),
) -> SuggestResponse:
    """[DEPRECADO] Devuelve slugs legacy incompatibles con `POST /query/chips`.

    Usar `GET /chips` que devuelve los `value` en el formato correcto.
    """
    client = request.client.host if request.client else "?"
    log.warning(
        "DEPRECATED endpoint /api/v1/suggest llamado (axis=%s, client=%s). "
        "Migrar a /api/v1/chips antes de %s.",
        axis, client, _SUNSET_DATE,
    )
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = _SUNSET_DATE
    response.headers["Link"] = _REPLACEMENT_LINK

    options = _CATALOG.get(axis)
    if options is None:
        raise HTTPException(
            status_code=422,
            detail=f"Eje desconocido: {axis!r}. Valores válidos: {list(_CATALOG)}",
        )
    return SuggestResponse(axis=axis, options=options)  # type: ignore[arg-type]
