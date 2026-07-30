"""
Scheduler agent.

Owns cadence and timing: polls due sequence enrollments
(``SequenceEnrollment.next_run_at``) to fire the next step (comment-now /
DM-later), materializes approved content-calendar entries into posts, and
drafts a post when a connected account has gone quiet.

Phase 0 ships a booting skeleton; the scheduling loops are implemented in the
engagement/cadence phase.
"""

from src.agents.core._skeleton import SkeletonAgent


class SchedulerAgent(SkeletonAgent):
    CAPABILITIES = [
        "sequence_dispatch",
        "content_calendar",
        "quiet_account_posting",
    ]
