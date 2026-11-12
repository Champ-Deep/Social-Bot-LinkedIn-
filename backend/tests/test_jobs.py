"""Queue + worker + scheduler tests (fakeredis, in-memory SQLite, recording transport)."""

import json
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.accounts.models import AccountStatus
from src.campaigns.models import Campaign, CampaignStatusEnum, CampaignTask
from src.campaigns.repository import CampaignRepository, CampaignTaskRepository
from src.campaigns.schemas import CampaignCreate
from src.campaigns.service import CampaignService, QueueUnavailableError
from src.infrastructure.task_bridge import MessageOrchestrator
from src.infrastructure.transports.base import TransportChallenge, TransportError
from src.jobs import scheduler, streams, worker

from conftest import RecordingTransport

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------- streams


async def test_ensure_group_is_idempotent(redis_client):
    await streams.ensure_group(redis_client)
    await streams.ensure_group(redis_client)  # BUSYGROUP swallowed
    assert (await streams.stats(redis_client))["length"] == 0


async def test_enqueue_read_ack(redis_client):
    await streams.ensure_group(redis_client)
    await streams.enqueue(redis_client, {"task_id": "t1", "attempt": 0})
    got = await redis_client.xreadgroup(streams.GROUP, "c1", {streams.STREAM: ">"}, count=5)
    entry_id, fields = got[0][1][0]
    assert fields["task_id"] == "t1"
    assert (await streams.stats(redis_client))["pending"] == 1
    await redis_client.xack(streams.STREAM, streams.GROUP, entry_id)
    assert (await streams.stats(redis_client))["pending"] == 0


async def test_defer_then_promote_due(redis_client):
    await streams.ensure_group(redis_client)
    await streams.defer(redis_client, {"task_id": "late"}, 3600)
    await streams.defer(redis_client, {"task_id": "now"}, 0)
    assert await streams.promote_due(redis_client) == 1
    assert [f["task_id"] for _, f in await redis_client.xrange(streams.STREAM)] == ["now"]
    assert (await streams.stats(redis_client))["delayed"] == 1


async def test_stats_counts_live_workers(redis_client):
    await streams.ensure_group(redis_client)
    assert (await streams.stats(redis_client))["workers_alive"] == 0
    await redis_client.set(f"{streams.WORKER_HB_PREFIX}w1", 1, ex=60)
    assert (await streams.stats(redis_client))["workers_alive"] == 1


# ---------------------------------------------------------------- worker


@pytest_asyncio.fixture
async def running(db, warm_account, redis_client):
    """A RUNNING campaign with one pending task for the warm account."""
    await streams.ensure_group(redis_client)
    campaign = await CampaignRepository(db).create(
        CampaignCreate(
            name="c",
            target_urls=["https://www.linkedin.com/posts/x-activity-123-abc"],
            account_ids=[str(warm_account.id)],
        )
    )
    await CampaignRepository(db).update_status(campaign.id, CampaignStatusEnum.RUNNING)
    orch = MessageOrchestrator(redis_client)
    task_id = await orch.submit_linkedin_automation_task(
        url="https://www.linkedin.com/posts/x-activity-123-abc",
        account_ids=[str(warm_account.id)],
    )
    await CampaignTaskRepository(db).create_bulk(
        campaign.id, [(task_id, "https://www.linkedin.com/posts/x-activity-123-abc")]
    )
    entry = (await redis_client.xrange(streams.STREAM))[0][1]
    return campaign, task_id, entry


def _factory(db):
    # Same session as the test so its writes are visible; close is a no-op for the worker.
    class _Ctx:
        async def __aenter__(self_inner):
            return db

        async def __aexit__(self_inner, *a):
            return False

    return _Ctx


async def _handle(redis_client, db, entry, transport):
    return await worker.handle(
        redis_client, entry, session_factory=_factory(db), transport_for=lambda live: transport
    )


async def test_success_finalizes_task_and_campaign(db, redis_client, running, transport):
    campaign, task_id, entry = running
    assert await _handle(redis_client, db, entry, transport) == "done"
    assert [c for c in transport.calls if c[0] == "like"] == [("like", entry["url"])]
    row = (await db.execute(select(CampaignTask).where(CampaignTask.orchestrator_task_id == task_id))).scalar_one()
    await db.refresh(row)
    assert row.status == "completed"
    await db.refresh(campaign)
    assert campaign.status == CampaignStatusEnum.COMPLETED.value


async def test_challenge_fails_without_retry_and_flags_account(db, redis_client, running, warm_account):
    campaign, task_id, entry = running
    t = RecordingTransport(raise_with=TransportChallenge("captcha"))
    assert await _handle(redis_client, db, entry, t) == "failed"
    await db.refresh(warm_account)
    assert warm_account.status == AccountStatus.RATE_LIMITED
    assert (await streams.stats(redis_client))["delayed"] == 0


async def test_transport_error_retries_then_dead_letters(db, redis_client, running):
    campaign, task_id, entry = running
    t = RecordingTransport(raise_with=TransportError("boom"))
    out = []
    for a in range(worker.MAX_ATTEMPTS):
        for k in await redis_client.keys("rl:*"):  # each try would otherwise hit the like cooldown
            await redis_client.delete(k)
        out.append(await _handle(redis_client, db, {**entry, "attempt": str(a)}, t))
    assert out == ["deferred"] * (worker.MAX_ATTEMPTS - 1) + ["failed"]
    assert (await streams.stats(redis_client))["dead"] == 1


async def test_cap_denial_defers_without_burning_an_attempt(db, redis_client, running, transport, monkeypatch):
    from types import SimpleNamespace

    from src.infrastructure.rate_policy import AccountRateLimiter

    campaign, task_id, entry = running
    tight = SimpleNamespace(per_hour=1, per_day=10, per_week=0, cooldown_seconds=0)
    monkeypatch.setattr(worker.caps_policy, "caps_for", lambda *a, **k: tight)
    await AccountRateLimiter(redis_client).check_and_consume(entry["account_id"], "like", per_hour=1, per_day=10)

    assert await _handle(redis_client, db, entry, transport) == "deferred"
    assert [c for c in transport.calls if c[0] == "like"] == []
    delayed = await redis_client.zrange(streams.DELAYED, 0, -1)
    assert json.loads(delayed[0])["attempt"] == "0"


async def test_missing_task_row_defers(db, redis_client, transport):
    await streams.ensure_group(redis_client)
    entry = {"task_id": "nope", "account_id": str(uuid.uuid4()), "url": "u", "like": "1", "attempt": "0"}
    assert await _handle(redis_client, db, entry, transport) == "deferred"
    assert (await streams.stats(redis_client))["delayed"] == 1


async def test_paused_campaign_entry_is_dropped(db, redis_client, running, transport):
    campaign, task_id, entry = running
    await CampaignRepository(db).update_status(campaign.id, CampaignStatusEnum.PAUSED)
    assert await _handle(redis_client, db, entry, transport) == "dropped"
    assert [c for c in transport.calls if c[0] == "like"] == []


# ---------------------------------------------------------------- service / API


async def test_start_without_queue_raises_and_leaves_state(db):
    campaign = await CampaignRepository(db).create(
        CampaignCreate(name="c", target_urls=["https://www.linkedin.com/posts/a-activity-1-x"], account_ids=["a"])
    )
    with pytest.raises(QueueUnavailableError):
        await CampaignService(session=db).start_campaign(campaign.id)
    await db.refresh(campaign)
    assert campaign.status == CampaignStatusEnum.DRAFT.value


async def test_resume_reenqueues_pending_rows_only(db, redis_client):
    await streams.ensure_group(redis_client)
    campaign = await CampaignRepository(db).create(
        CampaignCreate(name="c", target_urls=["https://www.linkedin.com/posts/a-activity-1-x", "https://www.linkedin.com/posts/b-activity-2-x"], account_ids=["a"])
    )
    await CampaignTaskRepository(db).create_bulk(campaign.id, [("t-pending", "https://www.linkedin.com/posts/a-activity-1-x"), ("t-done", "https://www.linkedin.com/posts/b-activity-2-x")])
    await CampaignTaskRepository(db).update_status("t-done", "completed")
    await CampaignRepository(db).update_status(campaign.id, CampaignStatusEnum.PAUSED)

    svc = CampaignService(session=db, orchestrator=MessageOrchestrator(redis_client))
    res = await svc.start_campaign(campaign.id)

    assert res.tasks_created == 1
    entries = [f for _, f in await redis_client.xrange(streams.STREAM)]
    assert [e["task_id"] for e in entries] == ["t-pending"]
    rows = (await db.execute(select(CampaignTask).where(CampaignTask.campaign_id == campaign.id))).scalars().all()
    assert len(rows) == 2  # no duplicates


async def test_api_start_without_queue_is_503(monkeypatch):
    from src.api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async def boom(self, *a, **k):
            raise QueueUnavailableError("down")

        monkeypatch.setattr(CampaignService, "start_campaign", boom)
        r = await client.post(
            f"/api/v1/campaigns/{uuid.uuid4()}/start", headers={"X-Idempotency-Key": str(uuid.uuid4())}
        )
    assert r.status_code == 503


async def test_healthz_reports_queue(redis_client):
    from src.api.main import app

    await streams.ensure_group(redis_client)
    app.state.redis = redis_client
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            q = (await client.get("/healthz")).json()["components"]["queue"]
            assert q["workers_alive"] == 0 and q["status"].startswith("no worker alive")
            await redis_client.set(f"{streams.WORKER_HB_PREFIX}w1", 1, ex=60)
            q = (await client.get("/healthz")).json()["components"]["queue"]
            assert q["status"] == "ok"
    finally:
        app.state.redis = None


# ---------------------------------------------------------------- scheduler


async def test_scheduler_skips_when_lock_held(redis_client, db):
    await redis_client.set(streams.SCHEDULER_LOCK, "1", ex=600)
    assert await scheduler.tick(redis_client, _factory(db)) == 0


async def test_scheduler_failing_account_does_not_stop_loop(redis_client, db, warm_account, monkeypatch):
    calls = []

    async def bad_due(db, account, **k):
        calls.append(account.id)
        raise RuntimeError("boom")

    async def ok_today(db, account, **k):
        calls.append("today")

    monkeypatch.setattr(scheduler, "run_due", bad_due)
    monkeypatch.setattr(scheduler, "run_today", ok_today)
    assert await scheduler.tick(redis_client, _factory(db)) == 1
    assert calls == [warm_account.id]  # failed, logged, loop survived
    assert await redis_client.exists(streams.SCHEDULER_HB)
    assert not await redis_client.exists(streams.SCHEDULER_LOCK)  # lock released
