"""Bounded polling metadata, separate from the original checkpoint and its integrity."""

from copy import deepcopy
from typing import Any

from ase.domain.report_jobs import canonical_job_payload
from ase.domain.reports import ReportOrigin

# The progress-list contract also includes main's automatic workspace briefings.
POLLING_ORIGINS = frozenset(value.value for value in ReportOrigin) | {"briefing"}


def compact_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Project an already validated checkpoint, without mutating its summary or bytes.

    Both the write codec and migration backfill validate the original checkpoint first.
    Its 8 KiB summary allowance stays intact; only this projection gains a small,
    recognised origin. Explicit frozen origins win, then the legacy media fallback.
    """
    frozen = payload.get("input")
    scope = frozen.get("scope") if isinstance(frozen, dict) else None
    origin = ReportOrigin.RESEARCH.value
    if isinstance(scope, dict):
        stated = scope.get("origin")
        if isinstance(stated, str) and stated in POLLING_ORIGINS:
            origin = stated
        elif scope.get("research_focus") == "media":
            origin = ReportOrigin.GEOLOCATION.value
    return {**deepcopy(payload.get("summary", {})), "origin": origin}


def polling_payload(summary: dict[str, Any]) -> dict[str, Any]:
    """Validate a thin projection with a separate, fixed allowance for derived origin.

    Polling rows are not resumable checkpoints. Validate their remaining JSON using
    the unchanged checkpoint limits, then attach only a recognised origin. This also
    makes the returned view independent of the ORM's mutable JSON column.
    """
    if type(summary) is not dict:
        raise ValueError("Invalid report job summary projection")
    value = dict(summary)
    origin = value.pop("origin", ReportOrigin.RESEARCH.value)
    if type(origin) is not str or origin not in POLLING_ORIGINS:
        raise ValueError("Invalid report job origin projection")
    payload = {"schema_version": 1, "summary": value}
    canonical_job_payload(payload)
    return {"schema_version": 1, "summary": {**deepcopy(value), "origin": origin}}
