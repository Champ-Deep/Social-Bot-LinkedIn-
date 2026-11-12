"""
The Harbinger handoff API: a message approved elsewhere enters this agent's own
paced, capped, gated send path. Nothing here ever sends on the request itself.

Fixtures use example names and the example profile URL only (public repo).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.outreach import execute as executor
from src.outreach import pacing
from src.outreach.models import OutreachSuggestion
from src.targeting.models import OutreachTarget, TargetStatus
from src.warmup import planner, program
from tests.conftest import RecordingTransport

TOKEN = "test-service-token-not-a-secret"
URL = "https://www.linkedin.com/in/example-test-profile"
GOOD_TEXT = "Hi Example, saw the Testco rollout this quarter. Worth comparing notes on how you handle onboarding?"
PATH = "/api/outreach/external-suggestions"


@pytest_asyncio.fixture
async def env(monkeypatch):
    """The real app on an in-memory DB, one org, one warmed-up account, service env set."""
    from httpx import ASGITransport, AsyncClient

    from src.accounts.schemas import AccountConnect
    from src.accounts.service import connect_account
    from src.api.main import app
    from src.database.models import Base, import_all_models
    from src.database.session import get_db
    from src.tenancy.models import Organization, User, UserRole
    import uuid

    import_all_models()
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db

    async with Session() as db:
        org = Organization(id=uuid.uuid4(), clerk_org_id=None, name="Test Org")
        db.add(org)
        await db.flush()
        user = User(
            id=uuid.uuid4(), clerk_user_id="user_test", org_id=org.id,
            email="test@example.com", role=UserRole.OWNER,
        )
        db.add(user)
        await db.commit()
        account = await connect_account(
            db, org_id=str(org.id), user_id=str(user.id),
            payload=AccountConnect(
                li_at="a" * 40, jsessionid="ajax:1234567890", label="Test User", mode="outreach"
            ),
            transport=RecordingTransport(),
        )
        planner.set_stage(account, program.FINAL_STAGE)
        await db.commit()
        account_id, org_id = str(account.id), str(org.id)

    def _no_real_transport(live):
        raise AssertionError("a test reached the real transport")

    monkeypatch.setattr(executor, "_default_transport", _no_real_transport)
    monkeypatch.setenv("SOCIAL_AGENT_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("SOCIAL_AGENT_SERVICE_ORG_ID", org_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield {"client": client, "Session": Session, "account_id": account_id, "org_id": org_id}

    app.dependency_overrides.clear()
    await engine.dispose()


def _body(env, ref="msg-1", kind="message", text=GOOD_TEXT, **over):
    body = {
        "account_id": env["account_id"],
        "external_ref": ref,
        "kind": kind,
        "target": {"profile_url": URL, "full_name": "Example Person", "company": "Testco"},
        "text": text,
        "approved_by": "approver@example.com",
        "approved_at": "2026-11-13T10:00:00+00:00",
    }
    body.update(over)
    return body


def _auth(token=TOKEN, ref=None):
    headers = {"Authorization": f"Bearer {token}"}
    if ref:
        headers["Idempotency-Key"] = ref
    return headers


async def _post(env, ref="msg-1", **over):
    return await env["client"].post(PATH, json=_body(env, ref, **over), headers=_auth(ref=ref))


async def _get(env, suggestion_id):
    return await env["client"].get(f"{PATH}/{suggestion_id}", headers=_auth())


async def _run_due(env, transport, rate_limiter, make_due=True):
    """What the agent's paced runner does on a tick, with the clock inside active hours."""
    async with env["Session"]() as db:
        if make_due:
            for row in (await db.execute(select(OutreachSuggestion))).scalars():
                row.scheduled_for = datetime.now(timezone.utc) - timedelta(minutes=1)
            await db.commit()
        from src.accounts.service import get_account_record

        account = await get_account_record(db, env["account_id"])
        return await executor.run_due(db, account, transport=transport, rate_limiter=rate_limiter)


@pytest.fixture
def in_hours(monkeypatch):
    monkeypatch.setattr(pacing, "is_within_active_hours", lambda *a, **k: True)


async def _count(env):
    async with env["Session"]() as db:
        return (await db.execute(select(func.count()).select_from(OutreachSuggestion))).scalar_one()


# ----------------------------------------------------------------------
# Create and idempotency
# ----------------------------------------------------------------------


async def test_create_returns_201_approved_and_sends_nothing(env, transport):
    res = await _post(env)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["external_ref"] == "msg-1"
    assert body["status"] == "approved"
    assert transport.calls == []

    async with env["Session"]() as db:
        row = (await db.execute(select(OutreachSuggestion))).scalar_one()
        assert str(row.id) == body["id"]
        assert row.scheduled_for is not None  # waits for the agent's own paced slot
        assert row.final_text == GOOD_TEXT
        assert row.action == "message"


async def test_repeat_returns_200_same_id_and_one_row(env):
    first = await _post(env)
    second = await _post(env)
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json() == first.json()
    assert await _count(env) == 1


async def test_connect_note_maps_to_a_connect_action(env):
    res = await _post(env, kind="connect_note", text="Hi Example, enjoyed your Testco post on onboarding.")
    assert res.status_code == 201, res.text
    async with env["Session"]() as db:
        assert (await db.execute(select(OutreachSuggestion))).scalar_one().action == "connect"


# ----------------------------------------------------------------------
# Auth and validation
# ----------------------------------------------------------------------


async def test_bad_token_is_401(env):
    res = await env["client"].post(PATH, json=_body(env), headers=_auth(token="wrong"))
    assert res.status_code == 401
    assert res.json() == {"detail": "invalid_service_token"}
    assert await _count(env) == 0


async def test_missing_header_is_401(env):
    res = await env["client"].post(PATH, json=_body(env))
    assert res.status_code == 401


async def test_unset_token_is_503_even_for_an_empty_bearer(env, monkeypatch):
    monkeypatch.delenv("SOCIAL_AGENT_SERVICE_TOKEN")
    for headers in ({"Authorization": "Bearer "}, {"Authorization": f"Bearer {TOKEN}"}, {}):
        res = await env["client"].post(PATH, json=_body(env), headers=headers)
        assert res.status_code == 503
        assert res.json() == {"detail": "service_token_unset"}
    assert (await env["client"].get(f"{PATH}/x", headers=_auth())).status_code == 503


async def test_unset_org_is_503(env, monkeypatch):
    monkeypatch.delenv("SOCIAL_AGENT_SERVICE_ORG_ID")
    assert (await _post(env)).status_code == 503


async def test_unknown_account_is_404(env):
    res = await _post(env, account_id="00000000-0000-4000-8000-000000000000")
    assert res.status_code == 404
    assert res.json() == {"detail": "account_not_found"}


@pytest.mark.parametrize("kind,limit", [("connect_note", 300), ("message", 1900)])
async def test_text_over_the_limit_is_422_for_each_kind(env, kind, limit):
    over = await _post(env, kind=kind, text="x" * (limit + 1))
    assert over.status_code == 422
    assert over.json() == {"detail": f"text: too long for {kind} (max {limit})"}
    assert await _count(env) == 0


async def test_text_at_the_limit_is_not_a_length_error(env):
    res = await _post(env, kind="connect_note", text="x" * 300)
    # The quality gate may still refuse it, but the length check does not.
    assert res.status_code == 201


@pytest.mark.parametrize(
    "over,field",
    [
        ({"kind": "post"}, "kind"),
        ({"approved_by": "not-an-email"}, "approved_by"),
        ({"approved_at": "yesterday"}, "approved_at"),
        ({"account_id": "nope"}, "account_id"),
        ({"target": {"profile_url": "https://example.com/x", "full_name": "A"}}, "target.profile_url"),
    ],
)
async def test_bad_fields_are_422_naming_the_field(env, over, field):
    res = await _post(env, **over)
    assert res.status_code == 422
    assert res.json()["detail"].startswith(f"{field}: ")


async def test_idempotency_key_must_match_external_ref(env):
    res = await env["client"].post(PATH, json=_body(env, "msg-1"), headers=_auth(ref="other"))
    assert res.status_code == 422
    assert res.json()["detail"].startswith("idempotency_key: ")


# ----------------------------------------------------------------------
# Status mapping
# ----------------------------------------------------------------------


async def test_status_sent(env, transport, rate_limiter, in_hours):
    created = (await _post(env)).json()
    assert (await _get(env, created["id"])).json()["status"] == "approved"

    result = await _run_due(env, transport, rate_limiter)
    assert result["sent"] == [created["id"]]
    assert [c[0] for c in transport.calls] == ["message"]

    got = (await _get(env, created["id"])).json()
    assert got["status"] == "sent"
    assert got["sent_at"] is not None
    assert got["reason"] is None
    assert got["external_ref"] == "msg-1"


async def test_status_failed_carries_the_error_text(env, rate_limiter, in_hours):
    created = (await _post(env)).json()
    await _run_due(env, RecordingTransport(fail_with="boom from transport"), rate_limiter)
    got = (await _get(env, created["id"])).json()
    assert got["status"] == "failed"
    assert got["reason"] == "boom from transport"


async def test_status_blocked_by_the_quality_gate(env, transport):
    res = await _post(env, text="Hi {{first_name}}, quick question about Testco.")
    assert res.status_code == 201
    assert res.json()["status"] == "blocked"
    assert res.json()["reason"]
    got = (await _get(env, res.json()["id"])).json()
    assert got["status"] == "blocked"
    assert transport.calls == []


async def test_status_blocked_for_a_suppressed_target(env, transport, rate_limiter, in_hours):
    assert (await _post(env, "first")).json()["status"] == "approved"
    async with env["Session"]() as db:
        target = (await db.execute(select(OutreachTarget))).scalar_one()
        target.status = TargetStatus.SUPPRESSED
        await db.commit()

    # Existing suppression is respected on a new submit (same person, new ref) ...
    res = await _post(env, "second")
    assert res.status_code == 201
    assert res.json()["status"] == "blocked"
    assert "suppressed" in res.json()["reason"]
    # ... and an already queued row stops reading as approved.
    assert (await _get(env, (await _post(env, "first")).json()["id"])).json()["status"] == "blocked"
    await _run_due(env, transport, rate_limiter)
    assert transport.calls == []


async def test_a_connected_target_is_not_walked_backwards(env):
    assert (await _post(env, "first")).status_code == 201
    async with env["Session"]() as db:
        target = (await db.execute(select(OutreachTarget))).scalar_one()
        target.status = TargetStatus.CONNECTED
        await db.commit()
    assert (await _post(env, "second")).status_code == 201
    async with env["Session"]() as db:
        assert (await db.execute(select(OutreachTarget))).scalar_one().status == TargetStatus.CONNECTED


async def test_get_hides_the_agents_own_suggestions_and_unknown_ids(env):
    import uuid

    from src.outreach.models import SuggestionStatus

    async with env["Session"]() as db:
        account_id = uuid.UUID(env["account_id"])
        target = OutreachTarget(
            id=uuid.uuid4(), org_id=uuid.UUID(env["org_id"]), account_id=account_id,
            member_urn="someone-else", status=TargetStatus.SCORED,
        )
        native = OutreachSuggestion(
            id=uuid.uuid4(), org_id=uuid.UUID(env["org_id"]), account_id=account_id,
            target_id=target.id, action="connect", status=SuggestionStatus.PENDING,
        )
        db.add_all([target, native])
        await db.commit()
    assert (await _get(env, str(native.id))).status_code == 404
    assert (await _get(env, "not-a-uuid")).status_code == 404


# ----------------------------------------------------------------------
# The agent's own gates still apply: nothing sends when it must not
# ----------------------------------------------------------------------


async def test_a_paused_account_never_sends(env, rate_limiter, in_hours):
    created = (await _post(env)).json()
    fake = RecordingTransport()

    async with env["Session"]() as db:
        from src.accounts.service import get_account_record

        planner.set_paused(await get_account_record(db, env["account_id"]), True, "test")
        await db.commit()

    result = await _run_due(env, fake, rate_limiter)
    assert result["sent"] == []
    assert fake.calls == []  # zero send_message calls
    got = (await _get(env, created["id"])).json()
    assert got["status"] == "blocked"
    assert got["reason"] == "account is paused"


async def test_outside_active_hours_never_sends(env, rate_limiter, monkeypatch):
    created = (await _post(env)).json()
    monkeypatch.setattr(pacing, "is_within_active_hours", lambda *a, **k: False)
    fake = RecordingTransport()

    result = await _run_due(env, fake, rate_limiter)
    assert result["sent"] == []
    assert "active hours" in list(result["blocked"].values())[0]
    assert fake.calls == []  # zero send_message calls
    assert (await _get(env, created["id"])).json()["status"] == "approved"  # still wanted, just not now


async def test_a_not_yet_due_row_is_not_sent_by_the_runner(env, rate_limiter, in_hours):
    await _post(env)
    fake = RecordingTransport()
    result = await _run_due(env, fake, rate_limiter, make_due=False)
    assert result["sent"] == []
    assert fake.calls == []


async def test_an_inactive_account_reads_as_blocked(env):
    created = (await _post(env)).json()
    async with env["Session"]() as db:
        from src.accounts.models import AccountStatus
        from src.accounts.service import get_account_record

        (await get_account_record(db, env["account_id"])).status = AccountStatus.AUTH_REQUIRED
        await db.commit()
    got = (await _get(env, created["id"])).json()
    assert got["status"] == "blocked"
    assert "auth_required" in got["reason"]


async def _seed_suppressed(env, member_urn, profile_url):
    async with env["Session"]() as db:
        db.add(
            OutreachTarget(
                id=uuid.uuid4(),
                org_id=uuid.UUID(env["org_id"]),
                account_id=uuid.UUID(env["account_id"]),
                member_urn=member_urn,
                public_id="example-test-profile",
                profile_url=profile_url,
                full_name="Example Person",
                status=TargetStatus.SUPPRESSED,
            )
        )
        await db.commit()


async def _assert_blocked_and_never_sent(env, res, transport, rate_limiter):
    assert res.status_code == 201
    assert res.json()["status"] == "blocked"
    assert "suppressed" in res.json()["reason"]
    async with env["Session"]() as db:
        assert len((await db.execute(select(OutreachTarget))).scalars().all()) == 1
    await _run_due(env, transport, rate_limiter)
    assert transport.calls == []


async def test_suppressed_target_stored_under_a_real_urn_is_not_duplicated(
    env, transport, rate_limiter, in_hours
):
    await _seed_suppressed(env, "urn:li:fsd_profile:ACoAAExampleOnly", URL)
    await _assert_blocked_and_never_sent(env, await _post(env, "probe-1"), transport, rate_limiter)


async def test_suppressed_target_is_found_through_a_case_variant_handle(
    env, transport, rate_limiter, in_hours
):
    await _seed_suppressed(env, "example-test-profile", URL)
    res = await _post(
        env,
        "probe-2",
        target={
            "profile_url": "https://www.linkedin.com/in/Example-Test-Profile",
            "full_name": "Example Person",
            "company": None,
        },
    )
    await _assert_blocked_and_never_sent(env, res, transport, rate_limiter)
