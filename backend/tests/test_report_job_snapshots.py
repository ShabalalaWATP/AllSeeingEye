"""Admission snapshots retain bounded report context, never private capabilities."""

import copy
import json
from dataclasses import replace
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest

from ase.application.report_jobs.snapshots import freeze_job, restore_job
from ase.application.reports.request import ReportRequest
from ase.application.reports.scope import report_scope
from ase.domain.events import BoundingBox
from ase.domain.map_research_origin import MapResearchOrigin
from ase.domain.report_records import body_from_dict
from ase.domain.research import ResearchMode
from ase.domain.research_area import direct_area_from_geometry
from ase.domain.research_brief_values import IntelligenceRequirement
from feeds_helpers import NOW
from report_documents_helpers import document_records
from report_helpers import GOOD_BODY
from report_job_snapshot_helpers import (
    INPUT_ID,
    PRIVATE_SENTINEL,
    fixture_evidence,
    fixture_job,
    fixture_routing,
    private_job,
    private_store,
)


def test_private_admission_selects_frozen_evidence_and_forgets_input_capability() -> None:
    job = private_job()
    data = freeze_job(job, fixture_routing(job), {}, private_store)
    serialised = json.dumps(data)
    assert PRIVATE_SENTINEL not in serialised and str(INPUT_ID) not in serialised
    for key in (
        "seed_events",
        "api_key_encrypted",
        "password_hash",
        "research_input_id",
        "base_url",
    ):
        assert key not in serialised
    restored = restore_job(json.loads(serialised), job.actor, job.profile)
    assert restored.seed_events == () and restored.request.research_input_id is None
    assert restored.reused_evidence[0].title == job.seed_events[0].title
    assert restored.reused_evidence[0].published_at is None
    assert restored.seed_attempts == job.seed_attempts
    assert restored.scope["research_input"] == job.scope["research_input"]
    assert restored.actor is job.actor and restored.profile is job.profile
    assert restored.direction == job.direction


def test_reused_evidence_keeps_priority_and_followup_pins_exact_parent_version() -> None:
    job = private_job()
    parent = uuid4()
    request = replace(job.request, parent_report_id=parent, parent_version=4)
    scope = {
        **job.scope,
        "parent_report_id": str(parent),
        "parent_version": 4,
        "research_reuse": {
            "report_id": str(parent),
            "version": 4,
            "evidence_items": 1,
            "basis": "frozen_saved_evidence",
        },
    }
    judgements = body_from_dict(GOOD_BODY).key_judgements
    job = replace(
        job,
        request=request,
        scope=scope,
        reused_evidence=(fixture_evidence(),),
        followup_judgements=judgements,
    )
    data = freeze_job(job, fixture_routing(job), {}, private_store)
    restored = restore_job(data, job.actor, job.profile)
    assert restored.request.parent_version == 4
    assert restored.reused_evidence[0].event_id == job.reused_evidence[0].event_id
    assert len(restored.reused_evidence) == 2
    assert restored.followup_judgements == judgements


@pytest.mark.parametrize("fixed", [False, True])
def test_absolute_period_does_not_drift_on_restore(fixed: bool) -> None:
    request = ReportRequest(
        "ask",
        question="What changed?",
        research_mode=ResearchMode.QUICK,
        research_since=NOW - timedelta(days=4) if fixed else None,
        research_until=NOW - timedelta(days=2) if fixed else None,
    )
    job = fixture_job(request)
    data = freeze_job(job, fixture_routing(job), {}, private_store)
    restored = restore_job(data, job.actor, job.profile)
    assert (restored.now, restored.period_from, restored.period_to) == (
        job.now,
        job.period_from,
        job.period_to,
    )
    assert data["period_from"] == job.period_from.isoformat()


def test_ordinary_report_and_geographic_context_roundtrip() -> None:
    job = fixture_job(ReportRequest("intsum", country_iso="GB", window_hours=48))
    job = replace(
        job,
        bbox=BoundingBox(-5, 50, 2, 58),
        countries=("GB",),
        terms=("energy",),
        background="Frozen context",
        country_name="United Kingdom",
    )
    restored = restore_job(
        freeze_job(job, fixture_routing(job), {}, private_store), job.actor, job.profile
    )
    assert restored.request.research_mode is None and restored.window == job.window
    assert restored.bbox == job.bbox and restored.background == job.background
    assert restored.country_name == job.country_name and restored.terms == job.terms


def test_job_frozen_before_the_origin_key_existed_still_restores() -> None:
    """Resume must not refuse a job whose scope predates a derived key."""
    job = fixture_job(ReportRequest("intsum", country_iso="GB", window_hours=48))
    frozen = freeze_job(job, fixture_routing(job), {}, private_store)
    assert frozen["scope"].pop("origin") == "research"
    restored = restore_job(frozen, job.actor, job.profile)
    assert restored.request.country_iso == "GB"
    assert report_scope(restored.request, restored.template)["origin"] == "research"


def test_twelve_canonical_requirements_survive_frozen_job_restore() -> None:
    requirements = tuple(
        IntelligenceRequirement(f"REQ-{index:02d}", f"What happened in sector {index}?")
        for index in range(12)
    )
    request = ReportRequest(
        "ask",
        question="Assess the twelve sectors",
        research_mode=ResearchMode.ADVANCED,
        canonical_requirements=requirements,
    )
    job = fixture_job(request)
    frozen = freeze_job(job, fixture_routing(job), {}, private_store)
    restored = restore_job(json.loads(json.dumps(frozen)), job.actor, job.profile)
    assert restored.request.canonical_requirements == requirements
    invalid = copy.deepcopy(frozen)
    invalid["request"]["canonical_requirements"][0]["priority"] = True
    with pytest.raises(ValueError):
        restore_job(invalid, job.actor, job.profile)


def test_collection_plan_requires_and_keeps_revision() -> None:
    request = replace(fixture_job().request, plan_id=uuid4())
    job = fixture_job(request)
    with pytest.raises(ValueError, match="revision"):
        freeze_job(job, fixture_routing(job), {}, private_store)
    job = replace(
        job,
        scope={
            **job.scope,
            "collection_plan_revision": {"id": str(request.plan_id), "updated_at": NOW.isoformat()},
        },
    )
    restored = restore_job(
        freeze_job(job, fixture_routing(job), {}, private_store), job.actor, job.profile
    )
    assert restored.scope["collection_plan_revision"] == job.scope["collection_plan_revision"]


@pytest.mark.parametrize(
    "patch",
    [
        {"schema_version": True},
        {"schema_version": 3},
        {"seed_events": []},
        {"window_seconds": True},
        {"window_seconds": -1},
        {"window_seconds": float("inf")},
        {"now": "2026-09-05T00:00:00"},
        {"period_from": "2026-09-01T00:00:00+00:00"},
        {"title": "x" * 2001},
        {"background": "x" * (768 * 1024)},
        {"bbox": {"west": 0, "east": 0, "south": 91, "north": 92}},
        {"terms": [1]},
        {"seed_attempts": [{"api_key": "forbidden"}]},
    ],
)
def test_rejects_invalid_version_types_bounds_and_private_fields(patch: dict[str, Any]) -> None:
    job = fixture_job()
    data = freeze_job(job, fixture_routing(job), {}, private_store)
    data.update(patch)
    with pytest.raises(ValueError):
        restore_job(data, job.actor, job.profile)


@pytest.mark.parametrize(
    "field,value",
    [
        ("research_input_id", "forbidden"),
        ("devils_advocacy", "false"),
        ("research_web_search", 1),
        ("research_terms", [3]),
        ("unknown", "value"),
    ],
)
def test_scope_cannot_smuggle_unknown_fields_or_coerce_types(field: str, value: Any) -> None:
    job = fixture_job()
    data = freeze_job(job, fixture_routing(job), {}, private_store)
    data["scope"][field] = value
    with pytest.raises(ValueError):
        restore_job(data, job.actor, job.profile)


@pytest.mark.parametrize(
    "changes",
    [
        {"revision": 2},
        {"model": "replacement"},
        {"max_output_tokens": 5000},
        {"temperature": 0.9},
        {"reasoning_effort": None},
    ],
)
def test_restoration_rejects_changed_model_settings(changes: dict[str, Any]) -> None:
    job = fixture_job()
    data = freeze_job(job, fixture_routing(job), {}, private_store)
    with pytest.raises(ValueError, match="model settings"):
        restore_job(data, job.actor, replace(job.profile, **changes))


def test_input_provenance_is_exactly_allowlisted_and_output_is_detached() -> None:
    job = private_job()
    data = freeze_job(job, fixture_routing(job), {}, private_store)
    changed = copy.deepcopy(data)
    changed["scope"]["research_input"]["preview_base64"] = "forbidden"
    with pytest.raises(ValueError):
        restore_job(changed, job.actor, job.profile)
    restored = restore_job(data, job.actor, job.profile)
    data["scope"]["research_input"]["limitations"].append("Later mutation")
    assert restored.scope == job.scope


def test_request_destination_and_override_are_retained() -> None:
    request = replace(fixture_job().request, team_id=uuid4(), profile_id=uuid4(), automation=True)
    job = fixture_job(request)
    data = freeze_job(job, fixture_routing(job), {}, private_store)
    restored = restore_job(data, job.actor, job.profile)
    assert restored.request.team_id == request.team_id
    assert restored.request.profile_id == request.profile_id and restored.request.automation
    data["routing"]["destination_team_id"] = str(uuid4())
    with pytest.raises(ValueError, match="destination"):
        restore_job(data, job.actor, job.profile)


def test_scheduled_update_keeps_exact_baseline_and_seen_fingerprints() -> None:
    _, baseline = document_records()
    request = replace(
        fixture_job().request,
        automation=True,
        subscription_previous_report_id=baseline.report_id,
        subscription_seen_signatures=("a" * 64, "b" * 64),
    )
    job = fixture_job(request)
    job = replace(
        job,
        subscription_baseline=baseline,
        followup_judgements=baseline.body.key_judgements,
        scope={
            **job.scope,
            "subscription_previous_report_id": str(baseline.report_id),
            "subscription_previous_version": baseline.number,
        },
    )
    frozen = freeze_job(job, fixture_routing(job), {}, private_store)
    assert frozen["schema_version"] == 2
    assert frozen["subscription_context"] == {
        "report_id": str(baseline.report_id),
        "version": baseline.number,
        "seen_signatures": ["a" * 64, "b" * 64],
    }
    serialised = json.dumps(frozen)
    assert baseline.evidence[0].title not in serialised
    restored = restore_job(json.loads(serialised), job.actor, job.profile)
    assert restored.request.subscription_previous_report_id == baseline.report_id
    assert restored.request.subscription_seen_signatures == request.subscription_seen_signatures
    assert restored.followup_judgements == baseline.body.key_judgements


def test_scheduled_update_rejects_tampered_baseline_and_signatures() -> None:
    _, baseline = document_records()
    request = replace(
        fixture_job().request,
        automation=True,
        subscription_previous_report_id=baseline.report_id,
        subscription_seen_signatures=("a" * 64,),
    )
    job = fixture_job(request)
    job = replace(
        job,
        subscription_baseline=baseline,
        scope={
            **job.scope,
            "subscription_previous_report_id": str(baseline.report_id),
            "subscription_previous_version": baseline.number,
        },
    )
    frozen = freeze_job(job, fixture_routing(job), {}, private_store)
    for change in (
        {"version": 0},
        {"report_id": str(uuid4())},
        {"seen_signatures": ["not-a-digest"]},
    ):
        tampered = copy.deepcopy(frozen)
        tampered["subscription_context"].update(change)
        with pytest.raises(ValueError):
            restore_job(tampered, job.actor, job.profile)


def test_private_metadata_without_matching_scope_is_not_dropped() -> None:
    job = fixture_job()
    data = freeze_job(job, fixture_routing(job), {}, private_store)
    data["scope"] = report_scope(job.request, job.template)
    data["scope"]["parent_report_id"] = str(uuid4())
    with pytest.raises(ValueError, match="exact saved version"):
        restore_job(data, job.actor, job.profile)


def test_saved_map_revision_and_explicit_geography_consent_survive_restore() -> None:
    area = direct_area_from_geometry(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 50], [0.1, 50], [0.1, 50.1], [0, 50]],
                        ],
                    },
                }
            ],
        }
    )
    origin = MapResearchOrigin(uuid4(), uuid4(), uuid4(), uuid4(), 2, "a" * 64, "b" * 64, area)
    request = replace(
        fixture_job().request,
        map_view_id=origin.view_id,
        map_revision_id=origin.revision_id,
        map_origin=origin,
        disclose_area_to_provider=True,
    )
    job = fixture_job(request)
    data = freeze_job(job, fixture_routing(job), {}, private_store)
    restored = restore_job(data, job.actor, job.profile)
    assert restored.request.map_origin == origin and restored.request.disclose_area_to_provider
    data["request"]["map_revision_id"] = str(uuid4())
    with pytest.raises(ValueError, match="exact map revision"):
        restore_job(data, job.actor, job.profile)
