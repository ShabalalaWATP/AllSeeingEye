"""Daily briefing identities and their minimum admission-marker retention period."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid5

from ase.domain.report_jobs import ReportJob

REFRESH_INTERVAL = timedelta(hours=24)


def briefing_key(owner_id: UUID, now: datetime) -> UUID:
    """Stable across tabs and process restarts, without retaining raw feed history."""
    return uuid5(owner_id, f"ase:daily-briefing:v1:{now.astimezone(UTC).date().isoformat()}")


def retains_daily_admission(job: ReportJob, now: datetime) -> bool:
    """Keep the marker even if work is paused, failed or already published.

    Preparation can cross UTC midnight before persistence stamps created_at,
    so the prior date is also recognised as the job's admission-key date.
    """
    return (
        job.team_id is None
        and now < job.created_at + REFRESH_INTERVAL
        and job.request_key
        in {
            briefing_key(job.owner_id, job.created_at),
            briefing_key(job.owner_id, job.created_at - REFRESH_INTERVAL),
        }
    )
