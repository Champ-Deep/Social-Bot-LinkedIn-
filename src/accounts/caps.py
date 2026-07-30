"""
Per-account activity caps and human pacing defaults.

These numbers are deliberately **below** what LinkedIn tolerates, not at the
edge of it. The product goal is to look like an attentive human using LinkedIn
daily, not like software extracting maximum throughput. An account that quietly
sends 15 well-targeted invitations a day survives indefinitely; one that sends
80 gets restricted, and the restriction costs far more than the extra volume was
ever worth.

Reference points (LinkedIn's actual behavior, which changes over time):
- Invitations are throttled on a **weekly** basis, roughly 100/week for a normal
  account. We hold to ~15/day, which lands well inside that.
- Messaging, reactions and comments have no published cap but attract
  bot-detection when they arrive in bursts or outside plausible hours.

Every number here is overridable per account (``ConnectedAccount.daily_caps``)
so an established account can be dialed up and a brand-new one dialed down.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

# A brand-new or recently-restricted account starts at a fraction of the normal
# allowance and is walked up over its first weeks ("warmup").
WARMUP_MULTIPLIER = 0.4


@dataclass(frozen=True)
class ActionCaps:
    """Caps and pacing for a single action type."""
    per_hour: int
    per_day: int
    # Minimum seconds between two actions of this type. Real people don't fire
    # invitations four seconds apart.
    cooldown_seconds: int


# Conservative-by-default policy. Tuned for "safe and credible", not "maximum".
DEFAULT_CAPS = {
    "connect": ActionCaps(per_hour=4, per_day=15, cooldown_seconds=420),
    "message": ActionCaps(per_hour=8, per_day=30, cooldown_seconds=180),
    "comment": ActionCaps(per_hour=5, per_day=18, cooldown_seconds=300),
    "like": ActionCaps(per_hour=15, per_day=60, cooldown_seconds=45),
    "follow": ActionCaps(per_hour=10, per_day=40, cooldown_seconds=60),
    "post": ActionCaps(per_hour=1, per_day=1, cooldown_seconds=86400),
    "fetch_profile": ActionCaps(per_hour=40, per_day=150, cooldown_seconds=5),
}

# Ceiling on how many suggestions we put in front of a user per account per day.
# Approval fatigue is a real failure mode: a queue of 200 items gets rubber
# stamped, which defeats the point of human review.
DEFAULT_SUGGESTION_BUDGET = 20

# Hours (account-local) during which actions may run. Outreach that lands at
# 3am reads as automated to both LinkedIn and the recipient.
DEFAULT_ACTIVE_HOURS = (8, 19)

# Weekend activity is heavily reduced rather than zero -- some people do post on
# a Sunday, but a bot that works exactly 7 days a week is conspicuous.
WEEKEND_MULTIPLIER = 0.25


def caps_for(account, action: str) -> ActionCaps:
    """
    Resolve the effective caps for ``account`` + ``action``.

    Order: per-account override -> conservative default. A warmup account has
    its allowance scaled down (never up).
    """
    base = DEFAULT_CAPS.get(action, ActionCaps(per_hour=5, per_day=20, cooldown_seconds=120))

    overrides = getattr(account, "daily_caps", None) or {}
    entry = overrides.get(action) if isinstance(overrides, dict) else None
    if isinstance(entry, dict):
        base = ActionCaps(
            per_hour=int(entry.get("per_hour", base.per_hour)),
            per_day=int(entry.get("per_day", base.per_day)),
            cooldown_seconds=int(entry.get("cooldown_seconds", base.cooldown_seconds)),
        )
    elif isinstance(entry, int):
        # Shorthand: a bare integer sets the daily cap only.
        base = ActionCaps(
            per_hour=min(base.per_hour, entry),
            per_day=entry,
            cooldown_seconds=base.cooldown_seconds,
        )

    if isinstance(overrides, dict) and overrides.get("warmup"):
        base = ActionCaps(
            per_hour=max(1, int(base.per_hour * WARMUP_MULTIPLIER)),
            per_day=max(1, int(base.per_day * WARMUP_MULTIPLIER)),
            cooldown_seconds=int(base.cooldown_seconds / WARMUP_MULTIPLIER),
        )
    return base


def suggestion_budget(account) -> int:
    """How many new suggestions may be generated for this account today."""
    overrides = getattr(account, "daily_caps", None) or {}
    if isinstance(overrides, dict) and overrides.get("suggestion_budget"):
        return int(overrides["suggestion_budget"])
    return DEFAULT_SUGGESTION_BUDGET


def active_hours(account) -> tuple:
    """The (start_hour, end_hour) window during which this account acts."""
    overrides = getattr(account, "daily_caps", None) or {}
    window = overrides.get("active_hours") if isinstance(overrides, dict) else None
    if isinstance(window, (list, tuple)) and len(window) == 2:
        return int(window[0]), int(window[1])
    return DEFAULT_ACTIVE_HOURS


def default_caps_payload(warmup: bool = True) -> dict:
    """The caps blob written onto a newly connected account."""
    payload = {action: asdict(caps) for action, caps in DEFAULT_CAPS.items()}
    payload["suggestion_budget"] = DEFAULT_SUGGESTION_BUDGET
    payload["active_hours"] = list(DEFAULT_ACTIVE_HOURS)
    payload["warmup"] = warmup
    return payload


def describe(account) -> dict:
    """Human-readable snapshot of an account's effective policy (for the UI)."""
    return {
        "actions": {
            action: asdict(caps_for(account, action))
            for action in DEFAULT_CAPS
        },
        "suggestion_budget": suggestion_budget(account),
        "active_hours": list(active_hours(account)),
        "warmup": bool((getattr(account, "daily_caps", None) or {}).get("warmup")),
    }


def timezone_of(account) -> Optional[str]:
    """IANA timezone the account's active hours are interpreted in."""
    overrides = getattr(account, "daily_caps", None) or {}
    return overrides.get("timezone") if isinstance(overrides, dict) else None
