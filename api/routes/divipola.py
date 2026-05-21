"""GET /api/v1/divipola — departamentos y municipios canónicos del DANE.

Fuente: `ai_engine.geo_resolver_data.MUNICIPIOS_DIVIPOLA` que se extrae del
dataset oficial `gdxc-w37w` con `scripts/extract_divipola.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from ai_engine.geo_resolver_data import MUNICIPIOS_DIVIPOLA
from api.models.schemas import DivipolaItem, DivipolaResponse

router = APIRouter()


# Departamentos canónicos: derivados del catálogo (deduplicados por cod_dpto).
# Nombre del departamento se infiere del nombre canónico del municipio capital
# cuando hay un mapeo conocido; si no, queda solo el código + sufijo.

_DEPT_NAMES: dict[str, str] = {
    "05": "Antioquia",
    "08": "Atlántico",
    "11": "Bogotá D.C.",
    "13": "Bolívar",
    "15": "Boyacá",
    "17": "Caldas",
    "18": "Caquetá",
    "19": "Cauca",
    "20": "Cesar",
    "23": "Córdoba",
    "25": "Cundinamarca",
    "27": "Chocó",
    "41": "Huila",
    "44": "La Guajira",
    "47": "Magdalena",
    "50": "Meta",
    "52": "Nariño",
    "54": "Norte de Santander",
    "63": "Quindío",
    "66": "Risaralda",
    "68": "Santander",
    "70": "Sucre",
    "73": "Tolima",
    "76": "Valle del Cauca",
    "81": "Arauca",
    "85": "Casanare",
    "86": "Putumayo",
    "88": "San Andrés y Providencia",
    "91": "Amazonas",
    "94": "Guainía",
    "95": "Guaviare",
    "97": "Vaupés",
    "99": "Vichada",
}


def _all_departments() -> list[DivipolaItem]:
    seen: set[str] = set()
    for _, _, dpto_code in MUNICIPIOS_DIVIPOLA:
        seen.add(dpto_code)
    items = [
        DivipolaItem(code=code, name=_DEPT_NAMES.get(code, f"Departamento {code}"))
        for code in sorted(seen)
    ]
    return items


def _municipios_of(dpto_code: str) -> list[DivipolaItem]:
    out: list[DivipolaItem] = []
    for name, mpio_code, dpto in MUNICIPIOS_DIVIPOLA:
        if dpto == dpto_code:
            out.append(DivipolaItem(code=mpio_code, name=name, dpto_code=dpto))
    return out


@router.get("/divipola", response_model=DivipolaResponse)
async def divipola(
    dpto: str | None = Query(default=None, description="Código DIVIPOLA del departamento (2 dígitos)"),
) -> DivipolaResponse:
    if dpto is None:
        return DivipolaResponse(departments=_all_departments())
    munis = _municipios_of(dpto)
    return DivipolaResponse(municipios=munis)
