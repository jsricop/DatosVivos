"""GET /api/v1/suggest — pobla los ChipGroup de la home.

Catálogo curado a mano y enriquecido con conteos en cuanto haya telemetría.
Mantenido cerca del producto, no auto-generado, para que los chips reflejen
intención editorial y no ruido del índice.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api.models.schemas import SuggestOption, SuggestResponse

router = APIRouter()


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


@router.get("/suggest", response_model=SuggestResponse)
async def suggest(
    axis: str = Query(..., description="Eje del chip: tema | tipo | territorio | entidad"),
) -> SuggestResponse:
    options = _CATALOG.get(axis)
    if options is None:
        raise HTTPException(
            status_code=422,
            detail=f"Eje desconocido: {axis!r}. Valores válidos: {list(_CATALOG)}",
        )
    return SuggestResponse(axis=axis, options=options)  # type: ignore[arg-type]
