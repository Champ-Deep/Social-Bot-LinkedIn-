"""
Shared test fixtures.

Everything here exists so the whole product can be tested with no browser, no
LinkedIn, no Redis server, no Clerk and no OpenRouter key: an in-memory SQLite
database, a fakeredis-backed rate limiter, and a transport that records what
would have been sent instead of sending it.
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio

# Must be set before src.database.session is imported anywhere.
os.environ.setdefault("USE_SQLITE", "true")
os.environ.setdefault("ALLOW_INSECURE_DEV_ENCRYPTION", "true")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from src.infrastructure.transports.base import TransportResult  # noqa: E402


@pytest_asyncio.fixture
async def db():
    """A fresh in-memory database with the full schema, per test."""
    from src.database.models import Base, import_all_models

    import_all_models()

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def redis_client():
    """An in-process Redis stand-in."""
    import fakeredis.aioredis

    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def rate_limiter(redis_client):
    from src.infrastructure.rate_policy import AccountRateLimiter

    return AccountRateLimiter(redis_client)


class RecordingTransport:
    """
    A transport that records calls instead of making them.

    ``fail_with`` makes every action fail, and ``raise_with`` makes it raise —
    which is how the failure and challenge paths get exercised without a live
    account.
    """

    name = "recording"

    def __init__(self, fail_with: str | None = None, raise_with: Exception | None = None):
        self.calls: list[tuple] = []
        self.fail_with = fail_with
        self.raise_with = raise_with

    async def _record(self, action: str, *args) -> TransportResult:
        self.calls.append((action, *args))
        if self.raise_with is not None:
            raise self.raise_with
        if self.fail_with is not None:
            return TransportResult(
                success=False, action=action, via=self.name, error=self.fail_with
            )
        return TransportResult(
            success=True, action=action, via=self.name, detail={"recorded": True}
        )

    async def connect(self, account, member_urn, note=None):
        return await self._record("connect", member_urn, note)

    async def send_message(self, account, member_urn, text):
        return await self._record("message", member_urn, text)

    async def comment(self, account, activity_urn, text):
        return await self._record("comment", activity_urn, text)

    async def like(self, account, activity_urn):
        return await self._record("like", activity_urn)

    async def follow(self, account, member_urn):
        return await self._record("follow", member_urn)

    async def create_post(self, account, body, media=None):
        return await self._record("post", body)

    async def fetch_activity(self, account, member_urn):
        return await self._record("fetch_activity", member_urn)

    async def fetch_inbox(self, account, since=None):
        return await self._record("fetch_inbox", since)

    async def fetch_profile(self, account, public_id):
        return await self._record("fetch_profile", public_id)

    async def whoami(self, account):
        self.calls.append(("whoami",))
        if self.raise_with is not None:
            raise self.raise_with
        return TransportResult(
            success=not self.fail_with,
            action="whoami",
            via=self.name,
            detail={
                "member_urn": "urn:li:fs_profile:ACoAAATEST",
                "public_id": "test-user",
                "display_name": "Test User",
                "headline": "Founder at Testco",
                "profile_url": "https://www.linkedin.com/in/test-user",
            },
            error=self.fail_with,
        )


@pytest.fixture
def transport():
    return RecordingTransport()


@pytest_asyncio.fixture
async def org(db):
    """A persisted organization + user to hang everything else off."""
    from src.tenancy.models import Organization, User, UserRole

    organization = Organization(id=uuid.uuid4(), clerk_org_id=None, name="Test Org")
    db.add(organization)
    await db.flush()

    user = User(
        id=uuid.uuid4(),
        clerk_user_id="user_test",
        org_id=organization.id,
        email="test@example.com",
        role=UserRole.OWNER,
    )
    db.add(user)
    await db.commit()
    return organization, user


@pytest_asyncio.fixture
async def account(db, org, transport):
    """A connected, verified account ready to act."""
    from src.accounts.schemas import AccountConnect
    from src.accounts.service import connect_account

    organization, user = org
    return await connect_account(
        db,
        org_id=str(organization.id),
        user_id=str(user.id),
        payload=AccountConnect(
            li_at="a" * 40,
            jsessionid="ajax:1234567890",
            label="Test User",
            mode="outreach",
        ),
        transport=transport,
    )


@pytest_asyncio.fixture
async def icp(db, org):
    """An ICP targeting growth leaders at SaaS companies."""
    from src.targeting.schemas import ICPCreate
    from src.targeting.service import create_icp

    organization, _ = org
    return await create_icp(
        db,
        str(organization.id),
        ICPCreate(
            name="SaaS growth leaders",
            titles=["head of growth", "vp of growth", "growth lead"],
            industries=["saas", "software"],
            keywords=["b2b", "activation", "retention"],
            excluded_keywords=["recruiter", "student"],
            value_proposition="I help B2B SaaS teams fix activation drop-off.",
            relevance_floor=60,
        ),
    )
