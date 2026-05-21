"""Validación geográfica de rows — anti-atribución incorrecta de cifras.

PROD_IMPROV.md mejora #5. Detecta el caso (P1 del journey 2026-05-18):

- Usuario pregunta "¿Cuántos municipios tiene Antioquia?"
- Retrieval trae dataset incorrecto (víctimas, no DIVIPOLA).
- SoQL ejecutado contra ese dataset cuenta víctimas en Antioquia (940.451).
- La cifra está en whitelist (pandas la calculó del row real).
- El validador de cifras la deja pasar.
- El LLM podría decir "Antioquia tiene 940.451 municipios" — **atribución
  silenciosamente incorrecta**.

Este módulo verifica que los rows realmente incluyan al menos una fila
correspondiente al territorio resuelto por GeoResolver. Si no, dispara
warning que se inyecta en el bloque de "Datos verificados" para que el
ciudadano vea la advertencia.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any

from ai_engine.geo_resolver import GeoContext


@dataclass(frozen=True)
class AttributionResult:
    """Resultado de la validación.

    Si `matches=True`, los rows incluyen al menos una fila correspondiente
    al territorio del contexto. Si `matches=False`, `warning` contiene un
    mensaje listo para mostrar al ciudadano.
    """

    matches: bool
    warning: str = ""


# Patrones de columna territorial (mismos que en build_comparison_soql, pero
# repetidos acá para no introducir dependencia circular).
_DPTO_CODE_COLS = (
    "cod_dpto",
    "codigo_dpto",
    "codigo_departamento",
    "codigo_dane_departamento",
)
_DPTO_NAME_COLS = (
    "departamento",
    "depa_nombre",
    "depto",
    "nom_dpto",
    "departamento_hecho",
    "departamento_del_hecho_dane",
    "departamento_del_hecho",
)
_MPIO_CODE_COLS = (
    "cod_mpio",
    "codigo_mpio",
    "codigo_municipio",
    "codigo_dane_municipio",
)
_MPIO_NAME_COLS = (
    "municipio",
    "nom_mpio",
    "mpio_nombre",
    "municipio_hecho",
    "municipio_del_hecho_dane",
    "municipio_del_hecho",
    "nombremunicipio",
)


def _normalize(s: str) -> str:
    """lowercase + sin tildes para comparación robusta."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower())
        if unicodedata.category(c) != "Mn"
    )


def _row_matches_dpto(row: dict, code: str, name: str) -> bool:
    """¿Esta fila pertenece al departamento (code, name)?"""
    code_norm = code.lstrip("0") or "0"
    name_norm = _normalize(name)
    for col in _DPTO_CODE_COLS:
        if col in row and row[col]:
            val = str(row[col]).strip().lstrip("0") or "0"
            if val == code_norm:
                return True
    for col in _DPTO_NAME_COLS:
        if col in row and row[col]:
            if _normalize(str(row[col])) == name_norm:
                return True
    return False


def _row_matches_mpio(row: dict, code: str, name: str) -> bool:
    """¿Esta fila pertenece al municipio (code, name)?"""
    name_norm = _normalize(name)
    for col in _MPIO_CODE_COLS:
        if col in row and row[col]:
            val = str(row[col]).strip()
            if val == code:
                return True
    for col in _MPIO_NAME_COLS:
        if col in row and row[col]:
            if _normalize(str(row[col])) == name_norm:
                return True
    return False


def validate_geographic_attribution(
    rows: list[dict[str, Any]],
    ctx: GeoContext | None,
) -> AttributionResult:
    """Verifica que `rows` incluyan al menos una fila del territorio en `ctx`.

    Reglas:
    - Sin `ctx` o sin targets subnacionales: passes neutral (matches=True).
    - Rows vacíos: passes neutral (no hay nada que validar).
    - Scope='national' (sin dpto/mpio explícitos): no validamos territorio.
    - Si hay target dpto o mpio, busca en columnas territoriales típicas.
    - Si NINGUNA fila matchea, devuelve warning con texto listo para usuario.
    """
    if ctx is None or not rows:
        return AttributionResult(matches=True)

    # Si scope es nacional sin subnacionales, no validamos territorio
    if ctx.scope == "national" and not any(t.level in ("dpto", "mpio") for t in ctx.targets):
        return AttributionResult(matches=True)

    # Localizar primer target subnacional para validar
    mpio_target = next((t for t in ctx.targets if t.level == "mpio"), None)
    dpto_target = next((t for t in ctx.targets if t.level == "dpto"), None)

    if not mpio_target and not dpto_target:
        # Solo groupby sin target — no validamos
        return AttributionResult(matches=True)

    # Verificar contra rows
    for row in rows:
        if mpio_target and mpio_target.code and _row_matches_mpio(row, mpio_target.code, mpio_target.name):
            return AttributionResult(matches=True)
        if dpto_target and dpto_target.code and _row_matches_dpto(row, dpto_target.code, dpto_target.name):
            return AttributionResult(matches=True)

    # Ninguna fila matchea — construir warning
    territory = (
        mpio_target.name if mpio_target
        else (dpto_target.name if dpto_target else "el territorio consultado")
    )
    warning = (
        f"⚠️ Advertencia: los datos devueltos podrían no corresponder "
        f"específicamente a {territory}. Verifica el dataset original "
        f"para confirmar la atribución."
    )
    return AttributionResult(matches=False, warning=warning)
