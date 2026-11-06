"""
Campaign worker: ``python -m src.jobs.worker``.

Consumes the ``campaign:tasks`` Redis Stream and sends LIKEs through the same
transports, caps and rate limiter the API path uses. At-least-once delivery: a
crash between send and XACK can double-like, which LinkedIn treats as idempotent.
Do not extend this to connect/message without a per-entry idempotency key.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import time

from sqlalchemy import select

from src.accounts import caps as caps_policy
from src.accounts.models import AccountStatus
from src.accounts.service import AccountError, get_account_record, load_live_account
from src.campaigns.models import Campaign, CampaignStatusEnum, CampaignTask
from src.campaigns.service import CampaignService
from src.database.models import import_all_models
from src.infrastructure.rate_policy import AccountRateLimiter
from src.infrastructure.transports.base import TransportChallenge, TransportError
from src.jobs import streams

log = logging.getLogger("worker")

BATCH = int(os.getenv("WORKER_BATCH", "5"))
MAX_ATTEMPTS = int(os.getenv("WORKER_MAX_ATTEMPTS", "3"))
CLAIM_IDLE_MS = int(os.getenv("WORKER_CLAIM_IDLE_MS", "300000"))
CONSUMER = os.getenv("HOSTNAME") or socket.gethostname()


async def _retry(r, f: dict, error: str, delay: float, *, count_attempt: bool = True) -> str:
    """Defer with attempt+1, or dead-letter and count a failure once attempts run out."""
    attempt = int(f.get("attempt", 0)) + (1 if count_attempt else 0)
    if attempt < MAX_ATTEMPTS:
        await streams.defer(r, {**f, "attempt": str(attempt)}, delay)
        return "deferred"
    await r.xadd(streams.DEAD, {**f, "error": error[:500]})
    return await _count(r, f, ok=False, error=error)


async def _count(r, f: dict, *, ok: bool, error: str = "") -> str:
    await r.hincrby(f"task:{f['task_id']}", "done" if ok else "failed", 1)
    if error:
        await r.rpush(f"task:{f['task_id']}:errors", error[:300])
    return "done" if ok else "failed"


async def _finalize(r, db, f: dict) -> None:
    key = f"task:{f['task_id']}"
    h = await r.hgetall(key)
    expected = len(json.loads(h.get("accounts", '["_"]')))
    done, failed = int(h.get("done", 0)), int(h.get("failed", 0))
    if done + failed < expected:
        return
    errors = await r.lrange(f"{key}:errors", 0, -1)
    actions = json.loads(h.get("actions", "{}"))
    result = {"accounts": expected, "done": done, "failed": failed, "errors": errors}
    if actions.get("comment"):
        result["skipped"] = "comment: no comment text source in v1"
    await CampaignService(session=db).update_task_status(
        f["task_id"], "completed" if failed == 0 else "failed", result
    )


async def handle(r, f: dict, *, session_factory, transport_for) -> str:
    """Process one stream entry. Returns an outcome label; the caller XACKs."""
    async with session_factory() as db:
        row = (
            await db.execute(select(CampaignTask).where(CampaignTask.orchestrator_task_id == f["task_id"]))
        ).scalar_one_or_none()
        if row is None:  # API enqueued before create_bulk committed
            return await _retry(r, f, "campaign task row missing", 5)
        campaign = await db.get(Campaign, row.campaign_id)
        if row.status != "pending" or campaign is None or campaign.status != CampaignStatusEnum.RUNNING.value:
            return "dropped"  # paused/cancelled/already final; resume re-enqueues

        outcome = await _send_like(r, db, f, transport_for)
        if outcome in ("done", "failed"):
            await _finalize(r, db, f)
        return outcome


async def _send_like(r, db, f, transport_for) -> str:
    record = await get_account_record(db, f["account_id"])
    if record is None or record.status != AccountStatus.ACTIVE:
        return await _count(r, f, ok=False, error=f"account {f['account_id']} not active")
    if f.get("like") != "1":  # comment-only is not sendable in v1
        return await _count(r, f, ok=True)

    caps = caps_policy.caps_for(record, "like")
    decision = await AccountRateLimiter(r).check_and_consume(
        str(record.id), "like", per_hour=caps.per_hour, per_day=caps.per_day,
        per_week=caps.per_week, cooldown_seconds=caps.cooldown_seconds,
    )
    if not decision.allowed:  # not a failure: wait for the window, keep the attempt
        await streams.defer(r, f, decision.retry_after_seconds)
        return "deferred"

    try:
        live = await load_live_account(db, f["account_id"])
        result = await transport_for(live).like(live, f["url"])
    except TransportChallenge as exc:
        record.status = AccountStatus.RATE_LIMITED  # stop using it, do not retry into a restriction
        await db.commit()
        return await _count(r, f, ok=False, error=f"account challenged: {exc}")
    except AccountError as exc:
        return await _count(r, f, ok=False, error=str(exc))
    except TransportError as exc:
        return await _retry(r, f, str(exc), 60 * 2 ** int(f.get("attempt", 0)))
    if result.success:
        return await _count(r, f, ok=True)
    return await _retry(r, f, result.error or "transport reported failure", 60 * 2 ** int(f.get("attempt", 0)))


async def run(r, stop: asyncio.Event, *, session_factory, transport_for) -> None:
    paused = lambda: os.getenv("SENDING_PAUSED", "").lower() == "true"  # noqa: E731 kill switch
    log.info("worker %s ready: %s", CONSUMER, await streams.stats(r))
    while not stop.is_set():
        try:
            await r.set(f"{streams.WORKER_HB_PREFIX}{CONSUMER}", int(time.time()), ex=60)
            await streams.promote_due(r)
            if paused():
                await asyncio.sleep(5)
                continue
            claimed = (await r.xautoclaim(streams.STREAM, streams.GROUP, CONSUMER,
                                          min_idle_time=CLAIM_IDLE_MS, start_id="0-0", count=10))[1]
            fresh = await r.xreadgroup(streams.GROUP, CONSUMER, {streams.STREAM: ">"},
                                       count=BATCH, block=5000)
            entries = list(claimed) + [e for _, batch in fresh for e in batch]
            for entry_id, f in entries:
                if not (f.get("task_id") and f.get("account_id") and f.get("url")):
                    # Malformed: retrying cannot help and _retry/_count need task_id, so
                    # dead-letter and ack now instead of crash-looping on reclaim.
                    log.error("malformed entry %s dead-lettered: %s", entry_id, sorted(f))
                    await r.xadd(streams.DEAD, {**f, "error": "malformed entry"})
                    await r.xack(streams.STREAM, streams.GROUP, entry_id)
                    continue
                try:
                    outcome = await handle(r, f, session_factory=session_factory, transport_for=transport_for)
                except Exception as exc:  # poison entry must not loop forever
                    log.exception("entry %s crashed", entry_id)
                    outcome = await _retry(r, f, f"worker error: {exc}", 60)
                await r.xack(streams.STREAM, streams.GROUP, entry_id)
                log.info("task %s account %s -> %s", f.get("task_id"), f.get("account_id"), outcome)
        except Exception:  # Redis/DB blip: unacked entries are reclaimed after CLAIM_IDLE_MS
            log.exception("loop error; retrying")
            await asyncio.sleep(5)


async def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    from src.database.session import AsyncSessionLocal
    from src.infrastructure.api_client import get_transport

    import_all_models()
    r = await streams.connect_required()
    stop = streams.stop_on_signal()
    try:
        await run(r, stop, session_factory=AsyncSessionLocal, transport_for=get_transport)
    finally:
        await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())
