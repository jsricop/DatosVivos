"""Punto de entrada FastAPI para DatosVivos Beta-2 (rebrand civil).

Decisión: ADR-013 — exponer el motor IA por HTTP REST + SSE bajo /api/v1 para
que el frontend Next.js (web/) y otros clientes HTTP puedan consumirlo sin
hablar MCP. El MCP server (mcp_server/) sigue dedicado a clientes MCP.

Cómo correr en local:
    LLM_BACKEND=mock uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

Variables de entorno relevantes:
    LLM_BACKEND       ollama (default) | mock | anthropic
    OLLAMA_HOST       http://localhost:11434
    OLLAMA_MODEL      qwen2.5-coder:3b
    CORS_ORIGINS      origenes permitidos, separados por coma (default: localhost:3001)
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import datasets, divipola, health, popular, query, suggest


def _build_app() -> FastAPI:
    app = FastAPI(
        title="DatosVivos API",
        version="2.0.0-beta",
        description=(
            "API HTTP del motor IA de DatosVivos sobre datos.gov.co. "
            "Consumida por el frontend Next.js (web/). "
            "MCP server vive aparte en mcp_server/."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
    )

    cors_origins = (
        os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001",
        )
        .split(",")
    )
    cors_origins = [o.strip() for o in cors_origins if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Elapsed-Ms"],
    )

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(suggest.router, prefix="/api/v1", tags=["suggest"])
    app.include_router(popular.router, prefix="/api/v1", tags=["popular"])
    app.include_router(divipola.router, prefix="/api/v1", tags=["divipola"])
    app.include_router(datasets.router, prefix="/api/v1", tags=["datasets"])
    app.include_router(query.router, prefix="/api/v1", tags=["query"])

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"name": "DatosVivos API", "version": "2.0.0-beta", "docs": "/docs"}

    return app


app = _build_app()
