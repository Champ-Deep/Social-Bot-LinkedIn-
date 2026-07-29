"""
FastAPI application entrypoint.

Serves the REST API (mounted under ``/api/v1``) and, in later phases, the
WebSocket fan-out and the Redis-backed task bridge between the API and the
agent runtime. This module exposes the ``app`` object that
``tests/test_campaigns_api.py`` and ``uvicorn src.api.main:app`` import.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import campaigns

API_V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan.

    Redis pool, the campaign<->agent task bridge (MessageOrchestrator), and the
    ``events:*`` result consumer are attached to ``app.state`` here in later
    Phase 0 tasks. Kept intentionally minimal for now so the app boots with no
    external services during tests.
    """
    yield


app = FastAPI(
    title="Social Bot LinkedIn API",
    description="Multi-tenant LinkedIn engagement automation API.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: the frontend (Vite dev server / hosted SPA) calls this API cross-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tightened to the configured frontend origin in Phase 1
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers under the versioned API prefix.
app.include_router(campaigns.router, prefix=API_V1_PREFIX)


@app.get("/healthz", tags=["system"])
async def healthz() -> dict:
    """Liveness probe."""
    return {"status": "ok"}
