"""
Scheduler: ``python -m src.jobs.scheduler``. Run EXACTLY one replica.

Every SCHEDULER_TICK_SECONDS, for each ACTIVE account: run due outreach
suggestions, then today's warm-up (both documented safe to call repeatedly).
A Redis lock guards against an accidental second replica.
"""

from __future__ import annotations

import asyncio
import logging
import os

from sqlalchemy import select

from src.accounts.models import AccountStatus, ConnectedAccount
from src.database.models import import_all_models
from src.infrastructure.rate_policy import AccountRateLimiter
from src.jobs import streams
from src.outreach.execute import run_due
from src.warmup.runner import run_today

log = logging.getLogger("scheduler")
TICK = int(os.getenv("SCHEDULER_TICK_SECONDS", "300"))


async def tick(r, session_factory) -> int:
    """One pass. Returns accounts processed; 0 when the lock is held elsewhere."""
    if not await r.set(streams.SCHEDULER_LOCK, "1", nx=True, ex=600):
        log.warning("lock held by another scheduler; skipping tick")
        return 0
    try:
        await r.set(streams.SCHEDULER_HB, "1", ex=120)
        limiter = AccountRateLimiter(r)
        async with session_factory() as db:
            accounts = (
                await db.execute(
                    select(ConnectedAccount).where(
                        ConnectedAccount.status == AccountStatus.ACTIVE,
                        ConnectedAccount.deleted_at.is_(None),
                    )
                )
            ).scalars().all()
        for account in accounts:
            try:  # one account failing must not stop the loop
                async with session_factory() as db:
                    await run_due(db, account, rate_limiter=limiter, limit=10)
                    await run_today(db, account, rate_limiter=limiter)
            except Exception:
                log.exception("tick failed for account %s", account.id)
        return len(accounts)
    finally:
        await r.delete(streams.SCHEDULER_LOCK)


async def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    from src.database.session import AsyncSessionLocal

    import_all_models()
    r = await streams.connect_required()
    stop = streams.stop_on_signal()
    log.info("scheduler ready, tick=%ss", TICK)
    try:
        while not stop.is_set():
            try:
                log.info("tick processed %d accounts", await tick(r, AsyncSessionLocal))
            except Exception:  # Redis/DB blip: try again next tick
                log.exception("tick error")
            try:
                await asyncio.wait_for(stop.wait(), timeout=TICK)
            except asyncio.TimeoutError:
                pass
    finally:
        await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())
