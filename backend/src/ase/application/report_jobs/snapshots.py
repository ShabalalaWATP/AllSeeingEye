"""Freeze report work explicitly, without actor/profile secrets or raw input events."""

from collections.abc import Callable, Mapping
from dataclasses import asdict
from datetime import timedelta
from typing import Any

from pydantic import TypeAdapter

from ase.application.model_routing import RoleProfiles
from ase.application.ports.feeds import EventStore
from ase.application.report_jobs.codec_boundary import (
    boundary,
    canonical,
    encoded,
    identifier,
    json_copy,
    number,
    record,
    text,
    timestamp,
)
from ase.application.report_jobs.collection_records import direction_from_json, evidence_from_json
from ase.application.report_jobs.request_snapshot import (
    request_from_dict,
    request_to_dict,
    template_digest,
)
from ase.application.report_jobs.subscription_snapshot import (
    freeze_subscription_context,
    restore_subscription_context,
)
from ase.application.reports.production_selection import select_for_job
from ase.application.reports.production_types import Job
from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import template_for
from ase.domain.direction import direction_to_dict
from ase.domain.events import BoundingBox
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.grading import SourceProfile
from ase.domain.llm import LlmProfile
from ase.domain.model_routing_records import routing_from_dict, routing_to_dict
from ase.domain.project_time import MAX_PROJECT_INTERVAL
from ase.domain.report_records import evidence_to_list
from ase.domain.reports import KeyJudgement
from ase.domain.research import CollectionAttempt
from ase.domain.trackers import Hazard
from ase.domain.users import User

_KEYS = {
    "schema_version",
    "template_id",
    "template_digest",
    "request",
    "scope",
    "now",
    "period_from",
    "period_to",
    "window_seconds",
    "title",
    "country_name",
    "report_id",
    "bbox",
    "countries",
    "hazard",
    "terms",
    "background",
    "direction",
    "evidence",
    "seed_attempts",
    "followup_judgements",
    "routing",
}
_SUBSCRIPTION_KEYS = _KEYS | {"subscription_context"}
_LIVE_WINDOW_SECONDS = 730 * 86400


def freeze_job(
    job: Job,
    routing: RoleProfiles,
    profiles: Mapping[str, SourceProfile],
    store_factory: Callable[[], EventStore],
) -> dict[str, Any]:
    if job.previous is not None:
        raise ValueError("Only new report jobs can be frozen")
    if len(job.seed_events) > 1000:
        raise ValueError("Too many private input items to freeze")
    evidence = job.reused_evidence
    if job.seed_events:
        # A fresh private store is essential: unselected shared live events never enter a job.
        store = store_factory()
        store.upsert(job.seed_events)
        evidence = select_for_job(store, profiles, job, job.direction).items
    subscription_context = freeze_subscription_context(job)
    value: dict[str, Any] = json_copy(
        {
            "schema_version": 2 if subscription_context is not None else 1,
            "template_id": job.template.id,
            "template_digest": template_digest(job.template),
            "request": request_to_dict(job.request),
            "scope": dict(job.scope),
            "now": job.now.isoformat(),
            "period_from": job.period_from.isoformat(),
            "period_to": job.period_to.isoformat(),
            "window_seconds": job.window.total_seconds(),
            "title": job.title,
            "country_name": job.country_name,
            "report_id": str(job.report_id) if job.report_id else None,
            "bbox": asdict(job.bbox) if job.bbox else None,
            "countries": job.countries,
            "hazard": job.hazard.value if job.hazard else None,
            "terms": job.terms,
            "background": job.background,
            "direction": direction_to_dict(job.direction) if job.direction else None,
            "evidence": evidence_to_list(evidence),
            "seed_attempts": [asdict(row) for row in job.seed_attempts],
            "followup_judgements": [asdict(row) for row in job.followup_judgements],
            "routing": routing_to_dict(routing.provenance),
            **(
                {"subscription_context": subscription_context}
                if subscription_context is not None
                else {}
            ),
        }
    )
    restore_job(value, job.actor, job.profile)
    return value


def _texts(value: Any, limit: int, each: int) -> tuple[str, ...]:
    if type(value) is not list or len(value) > limit:
        raise ValueError("Invalid report snapshot text collection")
    if any(type(item) is not str or len(item) > each for item in value):
        raise ValueError("Invalid report snapshot text")
    return tuple(value)


def _bbox(value: Any) -> BoundingBox | None:
    if value is None:
        return None
    if type(value) is not dict or set(value) != {"west", "east", "south", "north"}:
        raise ValueError("Invalid frozen bounding box")
    for name, limit in (("west", 180), ("east", 180), ("south", 90), ("north", 90)):
        number(value[name], -limit, limit)
    if value["south"] > value["north"]:
        raise ValueError("Invalid frozen bounding box")
    return BoundingBox(**value)


def _window_limit(request: ReportRequest) -> float:
    """Recorded-time research may cover the long project interval accepted at the boundary."""
    if request.effective_time_basis is EvidenceTimeBasis.RECORDED:
        return MAX_PROJECT_INTERVAL.total_seconds()
    return float(_LIVE_WINDOW_SECONDS)


def restore_job(data: Any, actor: User, profile: LlmProfile) -> Job:
    try:
        return _restore_job(data, actor, profile)
    except (KeyError, TypeError, AttributeError, OverflowError) as exc:
        raise ValueError("Malformed frozen report job") from exc


def _restore_job(data: Any, actor: User, profile: LlmProfile) -> Job:
    if type(data) is not dict or type(data.get("schema_version")) is not int:
        raise ValueError("Invalid report snapshot version")
    if data["schema_version"] not in {1, 2}:
        raise ValueError("Unsupported report snapshot version")
    value = boundary(data, _SUBSCRIPTION_KEYS if data["schema_version"] == 2 else _KEYS)
    template = template_for(text(value["template_id"], 120) or "")
    if value["template_digest"] != template_digest(template):
        raise ValueError("The frozen report template has changed")
    request = request_from_dict(value["request"], value["scope"], template)
    if value["schema_version"] == 2:
        request = restore_subscription_context(
            value["subscription_context"], request, value["scope"]
        )
    routing = routing_from_dict(value["routing"])
    if routing is None or routing.destination_team_id != request.team_id:
        raise ValueError("Invalid frozen model routing destination")
    canonical(value["routing"], routing_to_dict(routing))
    for routed in routing.profiles:
        record(routed)
    chosen = next((item for item in routing.profiles if item.role is template.role), None)
    if chosen is None or (
        chosen.profile_id != profile.id
        or chosen.profile_revision != profile.revision
        or chosen.model != profile.model
        or chosen.provider != profile.provider
        or chosen.reasoning_effort != profile.reasoning_effort
        or chosen.max_output_tokens != profile.max_output_tokens
        or chosen.temperature != profile.temperature
        or chosen.profile_updated_at != profile.updated_at
    ):
        raise ValueError("The frozen report model settings have changed")
    attempts_data, judgements_data = value["seed_attempts"], value["followup_judgements"]
    if type(attempts_data) is not list or len(attempts_data) > 64:
        raise ValueError("Invalid frozen seed collection receipts")
    if type(judgements_data) is not list or len(judgements_data) > 100:
        raise ValueError("Invalid frozen follow-up judgements")
    attempts = TypeAdapter(tuple[CollectionAttempt, ...]).validate_json(
        encoded(attempts_data), strict=True
    )
    judgements = TypeAdapter(tuple[KeyJudgement, ...]).validate_json(
        encoded(judgements_data), strict=True
    )
    canonical(attempts_data, [asdict(row) for row in attempts])
    canonical(judgements_data, [asdict(row) for row in judgements])
    job = Job(
        actor=actor,
        template=template,
        request=request,
        profile=profile,
        now=timestamp(value["now"]),
        window=timedelta(seconds=number(value["window_seconds"], 1, _window_limit(request))),
        title=text(value["title"], 2000) or "",
        scope=json_copy(value["scope"]),
        country_name=text(value["country_name"], 2000, nullable=True),
        report_id=identifier(value["report_id"]),
        bbox=_bbox(value["bbox"]),
        countries=_texts(value["countries"], 250, 3),
        hazard=Hazard(value["hazard"]) if value["hazard"] is not None else None,
        terms=_texts(value["terms"], 100, 300),
        background=text(value["background"], 20_000, nullable=True),
        direction=direction_from_json(value["direction"]),
        seed_attempts=attempts,
        reused_evidence=evidence_from_json(value["evidence"]),
        followup_judgements=judgements,
    )
    if (
        job.period_from != timestamp(value["period_from"])
        or job.period_to != timestamp(value["period_to"])
        or job.period_to <= job.period_from
        or job.period_to - job.period_from != job.window
    ):
        raise ValueError("Invalid frozen report interval")
    return job
