"""Version-one adapter from existing schedules to immutable request revisions."""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime
from hashlib import sha256
from uuid import UUID

from pydantic import TypeAdapter

from ase.application.report_jobs.codec_boundary import record
from ase.application.report_jobs.request_snapshot import request_to_dict
from ase.application.reports.request import ReportRequest
from ase.application.reports.scope import report_scope
from ase.application.reports.templates import TEMPLATES
from ase.application.schedules.brief_link import standing_request_from_brief
from ase.application.schedules.report_request import scheduled_report_request
from ase.domain.report_jobs import canonical_job_payload
from ase.domain.research_brief import ResearchBrief
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.schedules import Schedule
from ase.domain.subscription_editions import SubscriptionRevision
from ase.domain.subscription_snapshots import canonical_snapshot, decode_snapshot

_REQUIREMENTS = TypeAdapter(tuple[IntelligenceRequirement, ...])


def revision_from_schedule(
    schedule: Schedule,
    revision: int,
    *,
    created_at: datetime | None = None,
    brief: ResearchBrief | None = None,
) -> SubscriptionRevision:
    """Names and due dates do not change analytical compatibility."""
    if (schedule.brief_id is None) != (brief is None):
        raise ValueError("An exact Research Brief revision is required for this subscription.")
    if brief is not None and (
        (brief.identity.id, brief.identity.revision) != (schedule.brief_id, schedule.brief_revision)
        or brief.identity.team_id != schedule.team_id
    ):
        raise ValueError("The Research Brief does not match this subscription.")
    request = (
        standing_request_from_brief(brief, now=created_at or schedule.created_at)
        if brief is not None
        else scheduled_report_request(schedule)
    )
    scope = report_scope(request, TEMPLATES[request.template_id])
    settings = request_to_dict(request)
    fingerprint_body = {
        "schema_version": 1,
        "scope": scope,
        "avoid_repetition": schedule.avoid_repetition,
    }
    if brief is not None:
        fingerprint_body["request"] = settings
        fingerprint_body["parent"] = {
            "report_id": str(request.parent_report_id) if request.parent_report_id else None,
            "version": request.parent_version,
        }
    fingerprint = sha256(canonical_job_payload(fingerprint_body)).hexdigest()
    snapshot = canonical_snapshot(
        {
            "schema_version": 4 if brief is not None else 3,
            "template_id": request.template_id,
            "scope": scope,
            "request": settings,
            **(
                {
                    "brief_ref": {
                        "id": str(brief.identity.id),
                        "revision": brief.identity.revision,
                        "parent_report_id": str(request.parent_report_id)
                        if request.parent_report_id
                        else None,
                        "parent_version": request.parent_version,
                    }
                }
                if brief is not None
                else {}
            ),
            "subscription_context": {
                "report_id": str(request.subscription_previous_report_id)
                if request.subscription_previous_report_id
                else None,
                "seen_signatures": list(request.subscription_seen_signatures),
            },
            "recurrence": {
                "cadence": schedule.cadence,
                "timezone": schedule.timezone,
                "local_hour": schedule.local_hour,
                "local_minute": schedule.local_minute,
                "weekday": schedule.weekday,
                "monthday": schedule.monthday,
                "anchor_month": schedule.anchor_month,
            },
            "collection_policy": f"{schedule.collection_policy.value}_v1",
            "avoid_repetition": schedule.avoid_repetition,
        }
    )
    return SubscriptionRevision(
        subscription_id=schedule.id,
        revision=revision,
        owner_id=schedule.created_by,
        team_id=schedule.team_id,
        request_snapshot=snapshot,
        compatibility_fingerprint=fingerprint,
        recurrence_policy="local_iana_v1",
        collection_policy=f"{schedule.collection_policy.value}_v1",
        enabled=schedule.enabled,
        created_at=created_at or schedule.created_at,
        brief_revision_id=brief.identity.id if brief is not None else None,
    )


def request_from_revision(revision: SubscriptionRevision) -> ReportRequest:
    """Restore a frozen schedule request, including comparison context after a restart."""
    snapshot = decode_snapshot(revision.request_snapshot)
    template_id = snapshot["template_id"]
    template = TEMPLATES[template_id]
    request = ReportRequest.from_scope(template.id, snapshot["scope"])
    settings = snapshot["request"]
    if type(settings) is not dict or settings.get("automation") is not True:
        raise ValueError("Subscription revisions require an automated report request.")
    context = snapshot.get("subscription_context") or {
        "report_id": None,
        "seen_signatures": [],
    }
    raw_requirements = settings.get("canonical_requirements", [])
    if type(raw_requirements) is not list or len(raw_requirements) > 12:
        raise ValueError("Invalid frozen canonical requirements.")
    requirements = _REQUIREMENTS.validate_python(raw_requirements)
    if raw_requirements != [asdict(row) for row in requirements]:
        raise ValueError("Frozen canonical requirements changed during restoration.")
    brief_ref = snapshot.get("brief_ref")
    request = replace(
        request,
        team_id=UUID(settings["team_id"]) if settings["team_id"] else None,
        profile_id=UUID(settings["profile_id"]) if settings["profile_id"] else None,
        automation=True,
        map_view_id=UUID(settings["map_view_id"]) if settings["map_view_id"] else None,
        map_revision_id=UUID(settings["map_revision_id"]) if settings["map_revision_id"] else None,
        parent_report_id=UUID(brief_ref["parent_report_id"])
        if brief_ref and brief_ref["parent_report_id"]
        else None,
        parent_version=brief_ref["parent_version"] if brief_ref else None,
        canonical_requirements=requirements,
        subscription_previous_report_id=UUID(context["report_id"])
        if context["report_id"]
        else None,
        subscription_seen_signatures=tuple(context["seen_signatures"]),
    )
    record(request)
    restored_settings = request_to_dict(request)
    if "canonical_requirements" not in settings:
        restored_settings.pop("canonical_requirements")
    if (
        restored_settings != settings
        or report_scope(request, template) != snapshot["scope"]
        or request.team_id != revision.team_id
        or (
            not snapshot["avoid_repetition"]
            and (context["report_id"] is not None or context["seen_signatures"])
        )
    ):
        raise ValueError("The retained subscription request no longer matches its revision.")
    fingerprint_body = {
        "schema_version": 1,
        "scope": snapshot["scope"],
        "avoid_repetition": snapshot["avoid_repetition"],
    }
    if brief_ref is not None:
        fingerprint_body["request"] = settings
        fingerprint_body["parent"] = {
            "report_id": brief_ref["parent_report_id"],
            "version": brief_ref["parent_version"],
        }
        if revision.brief_revision_id != UUID(brief_ref["id"]):
            raise ValueError("Frozen Research Brief identity changed.")
    fingerprint = sha256(canonical_job_payload(fingerprint_body)).hexdigest()
    if fingerprint != revision.compatibility_fingerprint:
        raise ValueError("The retained subscription scope changed.")
    return request
