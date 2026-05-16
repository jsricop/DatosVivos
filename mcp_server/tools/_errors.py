"""Helper compartido: traduce errores HTTP de Socrata a mensajes útiles para el LLM."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TypeVar

import httpx
from mcp.server.fastmcp.exceptions import ToolError

T = TypeVar("T")


async def call_socrata(awaitable: Awaitable[T], *, context: str) -> T:
    """Ejecuta una corutina contra Socrata y reescribe errores HTTP a `ToolError`.

    Extrae el campo `message` del JSON de error de Socrata cuando está disponible
    (formato estándar: `{"code": "...", "error": true, "message": "..."}`).
    Esto permite que el LLM consumidor vea el motivo real del fallo y pueda
    corregir (ej. ajustar SoQL o cambiar de dataset_id) en vez de un opaco "HTTP 400".

    Args:
        awaitable: La llamada async a un cliente Socrata.
        context: Frase corta que prefija el error (ej. "get_metadata(gdxc-w37w)").

    Raises:
        ToolError: con mensaje formateado para el LLM.
    """
    try:
        return await awaitable
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        socrata_msg: str | None = None
        try:
            body = e.response.json()
            if isinstance(body, dict):
                socrata_msg = body.get("message")
        except (ValueError, httpx.DecodingError):
            socrata_msg = None
        detail = socrata_msg or e.response.text[:200] or str(e)
        raise ToolError(f"{context}: HTTP {status} — {detail}") from e
    except httpx.TimeoutException as e:
        raise ToolError(f"{context}: timeout consultando Socrata ({e})") from e
    except httpx.RequestError as e:
        raise ToolError(f"{context}: error de red ({type(e).__name__}: {e})") from e
