"""
Redis Streams contract shared by the API (enqueue), the worker (consume) and
/healthz (stats). Names are final; see docs/RAILWAY_SERVICES.md.

All functions expect a ``redis.asyncio`` client created with
``decode_responses=True``.
"""

from __future__ import annotations

import json
import time

STREAM = "campaign:tasks"
GROUP = "campaign-workers"
DEAD = "campaign:dead"
DELAYED = "campaign:delayed"  # ZSET: score = unix due time, member = JSON fields
WORKER_HB_PREFIX = "worker:hb:"
SCHEDULER_HB = "scheduler:hb"
SCHEDULER_LOCK = "scheduler:lock"
MAXLEN = 100_000


async def ensure_group(r) -> None:
    """Create the consumer group (and stream). Idempotent.

    Id "0" so entries added before the group existed are not skipped.
    """
    try:
        await r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except Exception as exc:  # redis.ResponseError, not importable cleanly across versions
        if "BUSYGROUP" not in str(exc):
            raise


async def enqueue(r, fields: dict) -> str:
    return await r.xadd(STREAM, {k: str(v) for k, v in fields.items()}, maxlen=MAXLEN, approximate=True)


async def defer(r, fields: dict, delay_seconds: float) -> None:
    await r.zadd(DELAYED, {json.dumps(fields): time.time() + max(0, delay_seconds)})


async def promote_due(r) -> int:
    """Move due delayed entries back to the stream. ZREM decides the winner across workers."""
    promoted = 0
    for member in await r.zrangebyscore(DELAYED, "-inf", time.time()):
        if await r.zrem(DELAYED, member):
            await enqueue(r, json.loads(member))
            promoted += 1
    return promoted


async def stats(r) -> dict:
    """Queue health summary. The only function /healthz calls."""
    pending = await r.xpending(STREAM, GROUP)
    oldest_ms = 0
    if pending["pending"]:
        oldest = await r.xpending_range(STREAM, GROUP, min="-", max="+", count=1)
        oldest_ms = oldest[0]["time_since_delivered"] if oldest else 0
    workers = 0
    async for _ in r.scan_iter(match=f"{WORKER_HB_PREFIX}*"):
        workers += 1
    return {
        "length": await r.xlen(STREAM),
        "pending": pending["pending"],
        "oldest_pending_ms": oldest_ms,
        "delayed": await r.zcard(DELAYED),
        "dead": await r.xlen(DEAD),
        "workers_alive": workers,
    }


async def connect(url: str):
    """Redis client with timeouts + keepalive pings so a dead socket fails fast and heals.

    Raises if the server is unreachable; callers decide whether that is fatal.
    """
    from redis import asyncio as aioredis

    client = aioredis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=15,  # must exceed the worker's 5s XREADGROUP block
        health_check_interval=30,
        retry_on_timeout=True,
    )
    await client.ping()
    await ensure_group(client)
    return client


async def connect_required(attempts: int = 5, delay: float = 3.0):
    """Entry for worker/scheduler: REDIS_URL is mandatory; retry briefly, then exit 1.

    Railway restarts the service, so a Redis that is still booting heals itself.
    Unlike the API, there is no degraded mode here.
    """
    import asyncio
    import logging
    import os
    import sys

    log = logging.getLogger("jobs")
    url = os.getenv("REDIS_URL")
    if not url:
        log.error("REDIS_URL is not set; refusing to start")
        sys.exit(1)
    for i in range(1, attempts + 1):
        try:
            return await connect(url)
        except Exception as exc:
            log.error("redis connect failed (%d/%d): %s", i, attempts, exc)
            await asyncio.sleep(delay)
    sys.exit(1)


def stop_on_signal():
    """asyncio.Event set by SIGTERM/SIGINT so loops finish the current unit and exit 0."""
    import asyncio
    import signal

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    return stop
