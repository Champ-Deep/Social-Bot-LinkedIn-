"""
Warm-up runner tests: does the programme actually *do* anything, and does it
stay inside its own rules while doing it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.infrastructure.transports.base import TransportChallenge, TransportResult
from src.outreach.models import OutreachSuggestion, SuggestionAction, SuggestionStatus
from src.warmup import planner, program, runner
from src.warmup import service as warmup_service
from src.warmup.models import AccountActivity, ActivityStatus


class FeedTransport:
    """A transport that serves a small ICP feed and records engagement."""

    name = "feed"

    def __init__(self, posts=3, fail=False, challenge=False):
        self.calls = []
        self.posts = posts
        self.fail = fail
        self.challenge = challenge

    async def fetch_activity(self, account, member_urn):
        return TransportResult(
            success=True,
            action="fetch_activity",
            via=self.name,
            detail={
                "posts": [
                    {"urn": f"urn:li:activity:{member_urn}-{i}", "text": f"post {i}"}
                    for i in range(self.posts)
                ]
            },
        )

    async def _act(self, action, subject):
        self.calls.append((action, subject))
        if self.challenge:
            raise TransportChallenge("checkpoint")
        return TransportResult(
            success=not self.fail, action=action, via=self.name,
            error="nope" if self.fail else None,
        )

    async def like(self, account, activity_urn):
        return await self._act("like", activity_urn)

    async def follow(self, account, member_urn):
        return await self._act("follow", member_urn)

    async def comment(self, account, activity_urn, text):
        return await self._act("comment", activity_urn)


async def _targets(db, org, account, icp, count=4):
    from src.targeting.schemas import TargetImportItem
    from src.targeting.service import import_targets

    organization, _ = org
    created, _ = await import_targets(
        db,
        org_id=str(organization.id),
        account_id=str(account.id),
        items=[
            TargetImportItem(
                profile_url=f"https://www.linkedin.com/in/person-{i}",
                full_name=f"Person{i} Example",
                title="Head of Growth",
                company=f"Company{i}",
                industry="SaaS",
                headline="Head of Growth | B2B activation",
            )
            for i in range(count)
        ],
        icp=icp,
    )
    return created


async def _stage(db, account, key, days_ago=1):
    """Put an account in a stage that started ``days_ago`` days back."""
    planner.set_stage(
        account, key, now=datetime.now(timezone.utc) - timedelta(days=days_ago)
    )
    await db.commit()
    await db.refresh(account)


# ----------------------------------------------------------------------
# It performs work
# ----------------------------------------------------------------------


async def test_runner_likes_icp_posts(db, org, account, icp, rate_limiter):
    """The core of warm-up: real engagement with the right people's content."""
    await _targets(db, org, account, icp)
    await _stage(db, account, "observe")

    transport = FeedTransport()
    result = await runner.run_today(
        db,
        account,
        transport=transport,
        rate_limiter=rate_limiter,
        live=object(),
        now=datetime.now(timezone.utc).replace(hour=18, minute=0),
    )

    likes = [c for c in transport.calls if c[0] == "like"]
    assert likes, result
    assert all("activity" in c[1] for c in likes)
    assert result["performed"]


async def test_performed_activity_is_recorded_for_graduation(
    db, org, account, icp, rate_limiter
):
    await _targets(db, org, account, icp)
    await _stage(db, account, "observe")

    await runner.run_today(
        db, account, transport=FeedTransport(), rate_limiter=rate_limiter,
        live=object(), now=datetime.now(timezone.utc).replace(hour=18, minute=0),
    )

    totals = await warmup_service.totals_for(db, account)
    assert totals.get("like", 0) > 0


async def test_the_same_post_is_never_engaged_with_twice(
    db, org, account, icp, rate_limiter
):
    await _targets(db, org, account, icp, count=1)
    await _stage(db, account, "observe")
    evening = datetime.now(timezone.utc).replace(hour=18, minute=0)

    transport = FeedTransport(posts=2)
    await runner.run_today(
        db, account, transport=transport, rate_limiter=rate_limiter,
        live=object(), now=evening,
    )
    first = {c[1] for c in transport.calls if c[0] == "like"}

    transport2 = FeedTransport(posts=2)
    await runner.run_today(
        db, account, transport=transport2, rate_limiter=rate_limiter,
        live=object(), now=evening,
    )
    second = {c[1] for c in transport2.calls if c[0] == "like"}

    assert not (first & second), "re-liked a post it had already liked"


# ----------------------------------------------------------------------
# It stays inside the rules
# ----------------------------------------------------------------------


async def test_runner_never_performs_a_locked_action(
    db, org, account, icp, rate_limiter
):
    """An observing account must not comment, follow, connect or message."""
    await _targets(db, org, account, icp)
    await _stage(db, account, "observe")

    transport = FeedTransport()
    await runner.run_today(
        db, account, transport=transport, rate_limiter=rate_limiter,
        live=object(), now=datetime.now(timezone.utc).replace(hour=18, minute=0),
    )

    performed = {c[0] for c in transport.calls}
    assert performed <= {"like"}, performed


async def test_runner_respects_the_pause_switch(db, org, account, icp, rate_limiter):
    await _targets(db, org, account, icp)
    await _stage(db, account, "observe")
    planner.set_paused(account, True, "manual")
    await db.commit()

    transport = FeedTransport()
    result = await runner.run_today(
        db, account, transport=transport, rate_limiter=rate_limiter, live=object()
    )

    assert result["performed"] == []
    assert not [c for c in transport.calls if c[0] in ("like", "follow")]


async def test_runner_refuses_to_act_without_a_rate_limiter(
    db, org, account, icp, monkeypatch
):
    """No limiter means caps can't be proven, so nothing happens."""
    monkeypatch.delenv("ALLOW_UNCAPPED_SENDING", raising=False)
    await _targets(db, org, account, icp)
    await _stage(db, account, "observe")

    transport = FeedTransport()
    await runner.run_today(
        db, account, transport=transport, rate_limiter=None, live=object(),
        now=datetime.now(timezone.utc).replace(hour=18, minute=0),
    )

    assert not [c for c in transport.calls if c[0] == "like"]


async def test_only_actions_that_are_due_are_performed(
    db, org, account, icp, rate_limiter
):
    """Calling the runner early must not pull the whole day forward."""
    await _targets(db, org, account, icp)
    await _stage(db, account, "react")

    transport = FeedTransport()
    # 06:00 is before the 08:00 activity window, so nothing is due.
    result = await runner.run_today(
        db, account, transport=transport, rate_limiter=rate_limiter, live=object(),
        now=datetime.now(timezone.utc).replace(hour=6, minute=0),
    )

    assert result["performed"] == []
    assert "paced" in result["message"] or result["skipped"]


async def test_a_challenge_during_warmup_pauses_the_account(
    db, org, account, icp, rate_limiter
):
    await _targets(db, org, account, icp)
    await _stage(db, account, "observe")

    await runner.run_today(
        db, account, transport=FeedTransport(challenge=True),
        rate_limiter=rate_limiter, live=object(),
        now=datetime.now(timezone.utc).replace(hour=18, minute=0),
    )

    assert account.status == "rate_limited"


async def test_failures_are_recorded_rather_than_silently_dropped(
    db, org, account, icp, rate_limiter
):
    from sqlalchemy import select

    await _targets(db, org, account, icp)
    await _stage(db, account, "observe")

    await runner.run_today(
        db, account, transport=FeedTransport(fail=True), rate_limiter=rate_limiter,
        live=object(), now=datetime.now(timezone.utc).replace(hour=18, minute=0),
    )

    rows = list(
        (
            await db.execute(
                select(AccountActivity).where(
                    AccountActivity.account_id == account.id,
                    AccountActivity.status == ActivityStatus.FAILED,
                )
            )
        )
        .scalars()
        .all()
    )
    assert rows
    # A failed action must not count toward graduation.
    totals = await warmup_service.totals_for(db, account)
    assert totals.get("like", 0) == 0


# ----------------------------------------------------------------------
# Comments go through approval
# ----------------------------------------------------------------------


async def test_comments_are_queued_for_approval_not_posted(
    db, org, account, icp, rate_limiter
):
    """Comments are published under the user's name, so a human sees them first."""
    from sqlalchemy import select

    await _targets(db, org, account, icp)
    await _stage(db, account, "converse", days_ago=1)

    transport = FeedTransport()
    result = await runner.run_today(
        db, account, transport=transport, rate_limiter=rate_limiter, live=object(),
        now=datetime.now(timezone.utc).replace(hour=18, minute=0),
    )

    # Nothing was actually commented on LinkedIn.
    assert not [c for c in transport.calls if c[0] == "comment"]

    queued = list(
        (
            await db.execute(
                select(OutreachSuggestion).where(
                    OutreachSuggestion.account_id == account.id,
                    OutreachSuggestion.action == SuggestionAction.COMMENT,
                )
            )
        )
        .scalars()
        .all()
    )
    assert queued, result
    assert queued[0].status in (SuggestionStatus.PENDING, SuggestionStatus.BLOCKED)
    assert queued[0].step == "warmup_comment"
    assert queued[0].subject_urn


async def test_queued_comment_references_the_post_it_replies_to(
    db, org, account, icp, rate_limiter
):
    from sqlalchemy import select

    await _targets(db, org, account, icp)
    await _stage(db, account, "converse", days_ago=1)

    await runner.run_today(
        db, account, transport=FeedTransport(), rate_limiter=rate_limiter,
        live=object(), now=datetime.now(timezone.utc).replace(hour=18, minute=0),
    )

    queued = (
        await db.execute(
            select(OutreachSuggestion).where(
                OutreachSuggestion.action == SuggestionAction.COMMENT
            )
        )
    ).scalars().first()

    assert queued is not None
    assert queued.draft_text
    assert queued.rationale and "post" in queued.rationale.lower()
