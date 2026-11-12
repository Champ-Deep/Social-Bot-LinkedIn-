"""
Tests for the campaign<->agent Redis bridge (MessageOrchestrator).

Uses fakeredis streams to assert that submitting a task enqueues one
entry per account, stores the task->campaign mapping, and that
result events parse back into task updates.
"""

import json

import pytest
import fakeredis.aioredis

from src.infrastructure.task_bridge import MessageOrchestrator
from src.jobs.streams import STREAM

pytestmark = pytest.mark.asyncio


@pytest.fixture
def redis_client():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


async def test_submit_enqueues_one_stream_entry_per_account(redis_client):
    bridge = MessageOrchestrator(redis_client)
    task_id = await bridge.submit_linkedin_automation_task(
        url="https://linkedin.com/posts/abc",
        account_ids=["acct-1", "acct-2"],
        like=True,
        comment=True,
        priority=2,
        source="campaign:xyz",
    )

    entries = [f for _, f in await redis_client.xrange(STREAM)]
    assert len(entries) == 2
    assert {e["account_id"] for e in entries} == {"acct-1", "acct-2"}
    for e in entries:
        assert e["task_id"] == task_id
        assert e["url"] == "https://linkedin.com/posts/abc"
        assert (e["like"], e["comment"], e["attempt"]) == ("1", "1", "0")
        assert e["priority"] == "2"


async def test_submit_stores_task_metadata(redis_client):
    bridge = MessageOrchestrator(redis_client)
    task_id = await bridge.submit_linkedin_automation_task(
        url="https://linkedin.com/in/someone",
        account_ids=["acct-1"],
    )
    meta = await bridge.get_task(task_id)
    assert meta is not None
    assert meta["url"] == "https://linkedin.com/in/someone"
    assert meta["accounts"] == ["acct-1"]
    assert meta["status"] == "submitted"


async def test_parse_result_event_completed():
    r = MessageOrchestrator.parse_result_event(
        json.dumps({"task_id": "t1", "status": "completed", "result": {"liked": True}})
    )
    assert r is not None
    assert r.task_id == "t1"
    assert r.status == "completed"
    assert r.result == {"liked": True}


async def test_parse_result_event_infers_failed_on_error():
    r = MessageOrchestrator.parse_result_event(json.dumps({"task_id": "t2", "error": "boom"}))
    assert r.status == "failed"


async def test_parse_result_event_rejects_malformed():
    assert MessageOrchestrator.parse_result_event("not json") is None
    assert MessageOrchestrator.parse_result_event(json.dumps({"no": "task_id"})) is None
