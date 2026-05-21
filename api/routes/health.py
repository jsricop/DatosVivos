"""GET /api/v1/health — liveness y backend en uso."""

from __future__ import annotations

import os

from fastapi import APIRouter

from api.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    backend = os.getenv("LLM_BACKEND", "ollama")
    return HealthResponse(status="ok", backend=backend, detail=None)
