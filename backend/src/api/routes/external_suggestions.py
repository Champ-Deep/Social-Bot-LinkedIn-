"""
External suggestions: a message approved elsewhere (Harbinger) enters the queue.

One approval surface. Harbinger's approval satisfies this agent's own approve
step, so the row is stored approved and the agent's paced runner (``run_due``)
sends it at the next due slot: inside the caps, the active hours, the warm-up
gate and the quality gate. Nothing here sends, and nothing here forces.

Authenticated by a service token (SOCIAL_AGENT_SERVICE_TOKEN), not by Clerk, and
filed under one org (SOCIAL_AGENT_SERVICE_ORG_ID). Either unset: 503, fail closed.
"""

from __future__ import annotations

import hmac
import os
import uuid
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Response
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts import service as accounts_service
from src.accounts.models import AccountStatus
from src.database.session import get_db
from src.outreach import execute as executor
from src.outreach.models import OutreachSuggestion, SuggestionAction, SuggestionStatus
from src.targeting import service as targeting_service
from src.targeting.models import OutreachTarget, TargetStatus
from src.targeting.schemas import TargetImportItem
from src.warmup import planner as warmup_planner

router = APIRouter(prefix="/outreach/external-suggestions", tags=["external-suggestions"])

TEXT_LIMITS = {"connect_note": 300, "message": 1900}
ACTIONS = {"connect_note": SuggestionAction.CONNECT, "message": SuggestionAction.MESSAGE}
REFUSED_TARGETS = executor.REFUSED_TARGETS
# Restored after approve() so a handoff never walks a connected target backwards.
KEEP_TARGET_STATUS = (
    TargetStatus.CONNECTED,
    TargetStatus.REPLIED,
    TargetStatus.INTERESTED,
    TargetStatus.BOOKED,
)


class ExternalTarget(BaseModel):
    profile_url: str = Field(pattern=r"^https://www\.linkedin\.com/in/[A-Za-z0-9_%-]+/?$")
    full_name: str = Field(min_length=1, max_length=255)
    company: Optional[str] = Field(default=None, max_length=255)


class ExternalSuggestionIn(BaseModel):
    account_id: uuid.UUID
    external_ref: str = Field(min_length=1, max_length=128)
    kind: Literal["message", "connect_note"]
    target: ExternalTarget
    text: str = Field(min_length=1)
    approved_by: str = Field(pattern=r"^[^@\s]+@[^@\s]+$", max_length=200)
    approved_at: datetime


def require_service_token(authorization: Optional[str] = Header(None)) -> str:
    """Check the bearer against the service token; return the org id to file under."""
    expected = os.getenv("SOCIAL_AGENT_SERVICE_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="service_token_unset")
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(
        supplied.strip().encode(), expected.encode()
    ):
        raise HTTPException(status_code=401, detail="invalid_service_token")
    org_id = os.getenv("SOCIAL_AGENT_SERVICE_ORG_ID", "")
    if not org_id:
        raise HTTPException(status_code=503, detail="service_org_unset")
    return org_id


def _parse(body: dict) -> ExternalSuggestionIn:
    """Validate by hand: the contract wants ``{"detail": "<field>: <reason>"}``, not a list."""
    try:
        payload = ExternalSuggestionIn.model_validate(body)
    except ValidationError as exc:
        err = exc.errors()[0]
        field = ".".join(str(part) for part in err["loc"]) or "body"
        raise HTTPException(status_code=422, detail=f"{field}: {err['msg']}") from exc
    limit = TEXT_LIMITS[payload.kind]
    if len(payload.text) > limit:
        raise HTTPException(
            status_code=422, detail=f"text: too long for {payload.kind} (max {limit})"
        )
    return payload


async def _status_of(db: AsyncSession, row: OutreachSuggestion) -> tuple:
    """Map the internal row to (status, reason). Live checks cover rows still waiting."""
    s = row.status
    if s == SuggestionStatus.SENT:
        return "sent", None
    if s == SuggestionStatus.FAILED:
        return "failed", row.error
    if s in (SuggestionStatus.BLOCKED, SuggestionStatus.REJECTED, SuggestionStatus.CANCELLED, SuggestionStatus.EXPIRED):
        return "blocked", row.error or f"suggestion is {s}"

    # Still waiting: it is blocked if the thing that would send it is not allowed to.
    target = (
        await db.execute(select(OutreachTarget).where(OutreachTarget.id == row.target_id))
    ).scalar_one_or_none()
    if target is not None and target.status in REFUSED_TARGETS:
        return "blocked", f"target is {target.status}"
    account = await accounts_service.get_account_record(db, str(row.account_id))
    if account is None:
        return "blocked", "account no longer exists"
    if warmup_planner.paused(account):
        return "blocked", "account is paused"
    if account.status != AccountStatus.ACTIVE:
        return "blocked", f"account is {account.status}"
    return "approved", None


async def _out(db: AsyncSession, row: OutreachSuggestion) -> dict:
    status, reason = await _status_of(db, row)
    return {
        "id": str(row.id),
        "external_ref": row.external_ref,
        "status": status,
        "sent_at": row.sent_at.isoformat() if row.sent_at else None,
        "reason": reason,
    }


async def _by_ref(db: AsyncSession, org_id: str, ref: str) -> Optional[OutreachSuggestion]:
    return (
        await db.execute(
            select(OutreachSuggestion).where(
                OutreachSuggestion.org_id == uuid.UUID(org_id),
                OutreachSuggestion.external_ref == ref,
            )
        )
    ).scalar_one_or_none()


async def _resolve_target(db: AsyncSession, org_id: str, account, tgt) -> OutreachTarget:
    """Find this person on the account by any identifier a row can hold; import only if absent.

    import_targets dedupes on member_urn alone, so a person stored under a real
    LinkedIn urn or a differently cased handle would get a second, unsuppressed row.
    An existing row's status (suppressed, not interested) decides, so a refused row wins.
    """
    slug = (targeting_service.public_id_from_url(tgt.profile_url) or "").lower()
    rows = (
        await db.execute(
            select(OutreachTarget).where(
                OutreachTarget.account_id == account.id,
                or_(
                    func.lower(OutreachTarget.member_urn) == slug,
                    func.lower(OutreachTarget.public_id) == slug,
                    OutreachTarget.profile_url.ilike(f"%/in/{slug}%"),
                ),
            )
        )
    ).scalars().all()
    # ilike is a superset (underscore wildcard, longer slugs): confirm in Python.
    found = [
        r for r in rows
        if slug in (
            (r.member_urn or "").lower(),
            (r.public_id or "").lower(),
            (targeting_service.public_id_from_url(r.profile_url) or "").lower(),
        )
    ]
    if found:
        return next((r for r in found if r.status in REFUSED_TARGETS), found[0])
    item = TargetImportItem(
        profile_url=tgt.profile_url, full_name=tgt.full_name, company=tgt.company
    )
    created, _ = await targeting_service.import_targets(
        db, org_id=org_id, account_id=str(account.id), items=[item]
    )
    return created[0]


@router.post("", status_code=201)
async def create_external_suggestion(
    response: Response,
    body: dict = Body(...),
    idempotency_key: Optional[str] = Header(None),
    org_id: str = Depends(require_service_token),
    db: AsyncSession = Depends(get_db),
) -> dict:
    payload = _parse(body)
    if idempotency_key is not None and idempotency_key != payload.external_ref:
        raise HTTPException(status_code=422, detail="idempotency_key: must equal external_ref")

    existing = await _by_ref(db, org_id, payload.external_ref)
    if existing is not None:
        response.status_code = 200
        return await _out(db, existing)

    account = await accounts_service.get_account_record(db, str(payload.account_id), org_id)
    if account is None:
        raise HTTPException(status_code=404, detail="account_not_found")

    target = await _resolve_target(db, org_id, account, payload.target)

    row = OutreachSuggestion(
        id=uuid.uuid4(),
        org_id=uuid.UUID(org_id),
        account_id=account.id,
        target_id=target.id,
        action=ACTIONS[payload.kind],
        status=SuggestionStatus.PENDING,
        draft_text=payload.text,
        rationale=f"Approved in Harbinger by {payload.approved_by}",
        generated_by="harbinger",
        external_ref=payload.external_ref,
    )
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:
        # A concurrent retry won the unique external_ref: return its row, no second one.
        await db.rollback()
        response.status_code = 200
        return await _out(db, await _by_ref(db, org_id, payload.external_ref))

    if target.status in REFUSED_TARGETS:
        row.status, row.error = SuggestionStatus.BLOCKED, f"target is {target.status}"
        await db.commit()
        return await _out(db, row)

    previous = target.status
    try:
        # Harbinger's approval stands in for the agent's own: approve() still runs
        # the quality gate and picks the paced send time. It does not send.
        await executor.approve(db, row, account=account)
    except executor.ExecutionBlocked as exc:
        row.error = exc.reason
        await db.commit()
        return await _out(db, row)

    row.reviewed_at = payload.approved_at
    if previous in KEEP_TARGET_STATUS:
        target.status = previous
    await db.commit()
    await db.refresh(row)
    return await _out(db, row)


@router.get("/{suggestion_id}")
async def get_external_suggestion(
    suggestion_id: str,
    org_id: str = Depends(require_service_token),
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        key = uuid.UUID(suggestion_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="suggestion_not_found")
    row = (
        await db.execute(
            select(OutreachSuggestion).where(
                OutreachSuggestion.id == key,
                OutreachSuggestion.org_id == uuid.UUID(org_id),
                OutreachSuggestion.external_ref.is_not(None),  # never expose the agent's own rows
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="suggestion_not_found")
    return await _out(db, row)
