"""
End to end: campaign create -> start -> Redis Stream -> worker -> transport.

Regression guard for the Railway incident: campaigns were published on a
pub/sub channel nobody consumed, and any agent that did listen logged
``KeyError: 'message_type'`` once per message. Here a campaign must reach the
(recording) transport, the campaign must close, and nothing may log an error.
"""

import asyncio
import json
import logging
import uuid

import pytest

from src.campaigns.models import CampaignStatusEnum
from src.campaigns.schemas import CampaignActions, CampaignCreate
from src.campaigns.service import CampaignService, QueueUnavailableError
from src.infrastructure.task_bridge import INTERACTION_CHANNEL, MessageOrchestrator
from src.jobs import streams, worker

pytestmark = pytest.mark.asyncio

URL = "https://www.linkedin.com/feed/update/urn:li:activity:7000000000000000001"


@pytest.fixture
def org_id(warm_account):
    return uuid.UUID(str(warm_account.org_id))


@pytest.fixture(autouse=True)
def yield_each_loop(monkeypatch):
    """fakeredis never blocks, so XREADGROUP BLOCK would spin the loop and starve the test."""
    real = streams.promote_due

    async def promote_then_yield(r):
        await asyncio.sleep(0.01)
        return await real(r)

    monkeypatch.setattr(streams, "promote_due", promote_then_yield)


def _likes(transport):
    return [c[1] for c in transport.calls if c[0] == "like"]  # ignore fixture whoami


class _SharedSession:
    """session_factory stand-in: hands out the test session without closing it."""

    def __init__(self, db):
        self.db = db

    def __call__(self):
        return self

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, *exc):
        return False


async def _make_campaign(db, account, urls):
    svc = CampaignService(db, uuid.UUID(str(account.org_id)))
    return await svc.create_campaign(
        CampaignCreate(
            name="e2e",
            target_urls=urls,
            account_ids=[str(account.id)],
            actions=CampaignActions(like=True),
        )
    )


async def _run_worker_until(db, r, transport, campaign_id, org_id, seconds=10):
    """Run the real worker loop until the campaign closes (or time runs out)."""
    stop = asyncio.Event()
    task = asyncio.create_task(
        worker.run(r, stop, session_factory=_SharedSession(db), transport_for=lambda _a: transport)
    )
    c = None
    try:
        for _ in range(int(seconds * 20)):
            await asyncio.sleep(0.05)
            await db.rollback()  # see rows committed through the same session
            c = await CampaignService(db, org_id).get_campaign(campaign_id)
            if c.status == CampaignStatusEnum.COMPLETED.value:
                return c
        return c
    finally:
        stop.set()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_campaign_reaches_transport_and_closes(db, warm_account, transport, redis_client, caplog, org_id):
    caplog.set_level(logging.INFO)
    await streams.ensure_group(redis_client)
    campaign = await _make_campaign(db, warm_account, [URL])

    resp = await CampaignService(db, org_id, orchestrator=MessageOrchestrator(redis_client)).start_campaign(campaign.id)
    assert resp.tasks_created == 1
    assert await redis_client.xlen(streams.STREAM) == 1  # enqueued, waiting for a consumer

    done = await _run_worker_until(db, redis_client, transport, campaign.id, org_id)

    assert done.status == CampaignStatusEnum.COMPLETED.value
    assert _likes(transport) == [URL]  # reached the "server"
    st = await streams.stats(redis_client)
    assert st["pending"] == 0 and st["dead"] == 0 and st["delayed"] == 0
    bad = [r for r in caplog.records if r.levelno >= logging.ERROR or "message_type" in r.getMessage()]
    assert bad == []  # the repeated traceback must not come back


async def test_work_enqueued_before_worker_exists_is_not_lost(db, warm_account, transport, redis_client, org_id):
    """Pub/sub dropped this; a stream keeps it until a worker shows up."""
    campaign = await _make_campaign(db, warm_account, [URL])
    await CampaignService(db, org_id, orchestrator=MessageOrchestrator(redis_client)).start_campaign(campaign.id)
    await asyncio.sleep(0.2)  # nobody consuming yet
    assert await redis_client.xlen(streams.STREAM) == 1

    await streams.ensure_group(redis_client)  # group created AFTER the entry (id "0")
    done = await _run_worker_until(db, redis_client, transport, campaign.id, org_id)
    assert done.status == CampaignStatusEnum.COMPLETED.value
    assert _likes(transport) == [URL]


async def test_start_without_queue_is_refused_not_faked(db, warm_account, org_id):
    campaign = await _make_campaign(db, warm_account, [URL])
    with pytest.raises(QueueUnavailableError):
        await CampaignService(db, org_id).start_campaign(campaign.id)
    fresh = await CampaignService(db, org_id).get_campaign(campaign.id)
    assert fresh.status != CampaignStatusEnum.RUNNING.value


async def test_nothing_published_to_legacy_agent_channel(redis_client):
    """The legacy agents choke on the bridge payload; no one may publish to them."""
    ps = redis_client.pubsub()
    await ps.subscribe(INTERACTION_CHANNEL)
    await ps.get_message(timeout=0.5)
    await MessageOrchestrator(redis_client).submit_linkedin_automation_task(
        url=URL, account_ids=["a1", "a2"], like=True
    )
    assert await ps.get_message(ignore_subscribe_messages=True, timeout=0.3) is None


async def test_poison_entry_is_acked_and_does_not_loop(db, redis_client, transport, caplog):
    """A malformed entry (no task_id) must be dead-lettered once, not retried forever."""
    await streams.ensure_group(redis_client)
    await redis_client.xadd(streams.STREAM, {"url": URL})  # no task_id, no account_id
    stop = asyncio.Event()
    t = asyncio.create_task(
        worker.run(redis_client, stop, session_factory=_SharedSession(db), transport_for=lambda _a: transport)
    )
    await asyncio.sleep(1.5)
    stop.set()
    t.cancel()
    await asyncio.gather(t, return_exceptions=True)

    st = await streams.stats(redis_client)
    assert st["pending"] == 0, "poison entry left unacked: it would be re-claimed and re-crash forever"
    assert st["dead"] == 1
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errors) <= 1  # one logged failure, not a flood
