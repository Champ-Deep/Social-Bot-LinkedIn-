"""
FastAPI application entrypoint.

Serves the REST API (mounted under ``/api/v1``) and, in later phases, the
WebSocket fan-out and the Redis-backed task bridge between the API and the
agent runtime. This module exposes the ``app`` object that
``tests/test_campaigns_api.py`` and ``uvicorn src.api.main:app`` import.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import campaigns, me

API_V1_PREFIX = "/api/v1"

logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan.

    Connects Redis and attaches the campaign<->agent task bridge
    (``MessageOrchestrator``) to ``app.state`` so campaign starts hand work to
    the interaction agents. If Redis is unreachable the app still boots with the
    bridge unset, and campaign starts degrade to the "orchestrator not
    configured" path rather than failing. (The httpx test transport does not run
    lifespan, so tests always take the degraded path.)
    """
    app.state.redis = None
    app.state.task_orchestrator = None

    # Bootstrap schema creation for first deploys (Postgres or SQLite). For
    # production migrations use Alembic; this is a convenience for greenfield
    # environments and is off unless explicitly enabled.
    if os.getenv("AUTO_CREATE_TABLES", "").lower() == "true":
        try:
            from src.database.models import Base, import_all_models
            from src.database.session import engine

            import_all_models()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("AUTO_CREATE_TABLES: schema ensured")
        except Exception as exc:  # pragma: no cover - depends on runtime DB
            logger.warning("AUTO_CREATE_TABLES failed: %s", exc)

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        from redis import asyncio as aioredis

        from src.infrastructure.task_bridge import MessageOrchestrator

        client = aioredis.from_url(redis_url, decode_responses=True)
        await client.ping()
        app.state.redis = client
        app.state.task_orchestrator = MessageOrchestrator(client)
        logger.info("Connected to Redis; task bridge active")
    except Exception as exc:  # pragma: no cover - depends on runtime env
        logger.warning("Redis unavailable (%s); campaign execution degraded", exc)

    try:
        yield
    finally:
        if app.state.redis is not None:
            await app.state.redis.aclose()


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
app.include_router(me.router, prefix=API_V1_PREFIX)


@app.get("/healthz", tags=["system"])
async def healthz() -> dict:
    """Liveness probe."""
    return {"status": "ok"}
