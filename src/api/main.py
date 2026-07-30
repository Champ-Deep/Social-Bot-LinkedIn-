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

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import (
    accounts,
    agents,
    campaigns,
    me,
    outreach,
    targeting,
    warmup,
)

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
app.include_router(agents.router, prefix=API_V1_PREFIX)
app.include_router(accounts.router, prefix=API_V1_PREFIX)
app.include_router(targeting.router, prefix=API_V1_PREFIX)
app.include_router(outreach.router, prefix=API_V1_PREFIX)
app.include_router(warmup.router, prefix=API_V1_PREFIX)


@app.get("/healthz", tags=["system"])
async def healthz(request: Request) -> dict:
    """
    Liveness probe plus a readiness summary of the optional components.

    Always 200 so the platform healthcheck reflects "the process is up", while
    ``components`` tells an operator what the app can actually *do* right now.
    The distinction matters here: without Redis the per-account caps cannot be
    enforced globally, so sending is refused — and that is a very different
    state from "broken", which is why it needs to be visible rather than
    inferred from behavior.
    """
    components: dict = {"api": "ok"}

    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        components["redis"] = "not configured"
    else:
        try:
            await redis.ping()
            components["redis"] = "ok"
        except Exception as exc:  # pragma: no cover - depends on runtime env
            components["redis"] = f"error: {exc}"

    try:
        from src.database.session import engine

        async with engine.connect():
            components["database"] = "ok"
    except Exception as exc:  # pragma: no cover - depends on runtime env
        components["database"] = f"error: {exc}"

    components["credentials_encryption"] = (
        "ok" if os.getenv("ENCRYPTION_KEY") else "no ENCRYPTION_KEY (cannot connect accounts)"
    )
    components["llm"] = (
        "openrouter" if os.getenv("OPENROUTER_API_KEY") else "templates (no OPENROUTER_API_KEY)"
    )
    components["sending"] = (
        "enabled"
        if components["redis"] == "ok" or os.getenv("ALLOW_UNCAPPED_SENDING", "").lower() == "true"
        else "disabled (caps cannot be enforced without Redis)"
    )

    return {"status": "ok", "components": components}


def _mount_frontend() -> None:
    """
    Serve the built React SPA (frontend/dist) so the whole product is one URL.

    Mounted last so it never shadows /api or /healthz. Unknown non-API paths
    fall through to index.html for client-side routing. No-ops if the build is
    absent (e.g. running the API alone in tests).
    """
    import os

    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
    dist = os.path.abspath(dist)
    index_file = os.path.join(dist, "index.html")
    if not os.path.isdir(dist) or not os.path.isfile(index_file):
        logger.info("Frontend build not found at %s; serving API only", dist)
        return

    assets_dir = os.path.join(dist, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    async def _spa_root() -> FileResponse:
        return FileResponse(index_file)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_catch_all(full_path: str) -> FileResponse:
        # API/system routes are matched earlier; everything else is the SPA.
        return FileResponse(index_file)

    logger.info("Serving frontend SPA from %s", dist)


_mount_frontend()
