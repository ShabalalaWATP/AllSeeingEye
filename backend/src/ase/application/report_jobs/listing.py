"""Research progress list filters and an opaque, stable keyset cursor.

Status groups partition every durable job state:

- ``running``: queued or running work that is still advancing on the server.
- ``attention``: paused or failed work. Each row's ``can_resume`` separates work that
  can continue from failures that cannot be resumed.
- ``finished``: completed reports and reports saved for review.

Pages are ordered newest first by creation time, then by job ID, and continue strictly
after the previous page's last row. Creation time never changes, so status updates and
newly admitted jobs cannot repeat or skip rows in a later page of the same filter.
"""

import base64
import binascii
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from ase.domain.report_jobs import ReportJobStatus
from ase.domain.reports import ReportOrigin

JobStatusGroup = Literal["all", "running", "attention", "finished"]
JOB_STATUS_GROUPS: dict[str, tuple[ReportJobStatus, ...]] = {
    "running": ("queued", "running"),
    "attention": ("paused", "failed"),
    "finished": ("completed", "needs_review"),
}
MAX_CURSOR_CHARS = 120
_ORIGINS = frozenset(value.value for value in ReportOrigin)


@dataclass(frozen=True, slots=True)
class JobListQuery:
    limit: int = 20
    status: JobStatusGroup = "all"
    include_briefings: bool = False
    after: tuple[datetime, UUID] | None = None

    @property
    def statuses(self) -> tuple[ReportJobStatus, ...] | None:
        return None if self.status == "all" else JOB_STATUS_GROUPS[self.status]


def encode_job_cursor(created_at: datetime, job_id: UUID) -> str:
    raw = f"{created_at.astimezone(UTC).isoformat()}|{job_id}".encode()
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_job_cursor(value: str) -> tuple[datetime, UUID]:
    """Reject anything that is not a cursor this server issued in its exact form."""
    if not value or len(value) > MAX_CURSOR_CHARS:
        raise ValueError("Use a research progress cursor from the previous page.")
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode("ascii")
        stamp, identity = raw.split("|")
        created_at, job_id = datetime.fromisoformat(stamp), UUID(identity)
    except (binascii.Error, UnicodeError, ValueError) as exc:
        raise ValueError("Use a research progress cursor from the previous page.") from exc
    if created_at.utcoffset() is None or encode_job_cursor(created_at, job_id) != value:
        raise ValueError("Use a research progress cursor from the previous page.")
    return created_at, job_id


def job_origin(payload: Mapping[str, Any]) -> str:
    """Thin rows carry the SQL classification; detail reads use the frozen request scope.

    Unrecognised or absent origins keep the saved-report rule: media focus is a
    geolocation assessment and everything else is requested research.
    """
    summary = payload.get("summary")
    if isinstance(summary, dict) and summary.get("origin") in _ORIGINS:
        return str(summary["origin"])
    frozen = payload.get("input")
    scope = frozen.get("scope") if isinstance(frozen, dict) else None
    if not isinstance(scope, dict):
        return ReportOrigin.RESEARCH.value
    if scope.get("origin") in _ORIGINS:
        return str(scope["origin"])
    if scope.get("research_focus") == "media":
        return ReportOrigin.GEOLOCATION.value
    return ReportOrigin.RESEARCH.value
