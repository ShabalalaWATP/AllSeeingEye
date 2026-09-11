"""Admission rejects stale scope provenance and malformed saved job envelopes."""

from dataclasses import replace
from typing import Any, cast
from uuid import uuid4

import pytest

from ase.application.report_jobs.snapshots import freeze_job, restore_job
from ase.application.reports.production_checkpoint import collection_from_dict, collection_to_dict
from ase.application.reports.production_types import Totals
from ase.domain.report_records import ReportVersion
from report_job_snapshot_helpers import fixture_job, fixture_routing, private_job, private_store
from test_report_collection_snapshot import snapshot


@pytest.mark.parametrize(
    "field,value",
    [
        ("sha256", "bad"),
        ("sha256", "x" * 64),
        ("limitations", "not a list"),
        ("limitations", ["bounded"] * 101),
        ("extracted_items", 1001),
        ("filename", "x" * 241),
        ("imported_at", "not a date"),
    ],
)
def test_invalid_private_input_provenance_is_not_durably_admitted(field: str, value: Any) -> None:
    job = private_job()
    data = freeze_job(job, fixture_routing(job), {}, private_store)
    data["scope"]["research_input"][field] = value
    with pytest.raises(ValueError):
        restore_job(data, job.actor, job.profile)


@pytest.mark.parametrize(
    "patch",
    [
        {"parent_report_id": str(uuid4()), "parent_version": 0},
        {
            "research_reuse": {
                "report_id": str(uuid4()),
                "version": 1,
                "evidence_items": 1,
                "basis": "newly_collected",
            }
        },
        {
            "collection_plan_revision": {
                "id": str(uuid4()),
                "updated_at": "2026-09-05T00:00:00+00:00",
            }
        },
    ],
)
def test_invalid_parent_and_plan_revision_provenance_cannot_resume(patch: dict[str, Any]) -> None:
    job = fixture_job()
    data = freeze_job(job, fixture_routing(job), {}, private_store)
    data["scope"].update(patch)
    with pytest.raises(ValueError):
        restore_job(data, job.actor, job.profile)


@pytest.mark.parametrize(
    "field,value",
    [
        ("automation", 1),
        ("team_id", "not-an-id"),
        ("profile_id", "BD44C5C9-38C6-419A-A48B-2D915C1E1030"),
    ],
)
def test_request_override_types_are_strict(field: str, value: Any) -> None:
    job = fixture_job()
    data = freeze_job(job, fixture_routing(job), {}, private_store)
    data["request"][field] = value
    with pytest.raises(ValueError):
        restore_job(data, job.actor, job.profile)


@pytest.mark.parametrize(
    "patch",
    [
        {"seed_attempts": [None] * 65},
        {"followup_judgements": [None] * 101},
        {"terms": ["one"] * 101},
        {"seed_attempts": None},
        {"followup_judgements": None},
        {"bbox": {"west": 0, "east": 1, "south": 60, "north": 50}},
        {"bbox": []},
        {"template_digest": "changed"},
        {"routing": None},
        {"evidence": [{}]},
        {"scope": None},
    ],
)
def test_saved_job_envelopes_have_bounded_counts_and_known_structure(patch: dict[str, Any]) -> None:
    job = fixture_job()
    data = freeze_job(job, fixture_routing(job), {}, private_store)
    data.update(patch)
    with pytest.raises(ValueError):
        restore_job(data, job.actor, job.profile)


def test_oversized_raw_input_is_rejected_before_private_store_creation() -> None:
    job = private_job()
    job = replace(job, seed_events=job.seed_events * 1001)
    with pytest.raises(ValueError, match="Too many"):
        freeze_job(job, fixture_routing(job), {}, private_store)


def test_regeneration_is_explicitly_unsupported_in_initial_job_codec() -> None:
    job = fixture_job()
    job = replace(job, previous=cast(ReportVersion, object()))
    with pytest.raises(ValueError, match="Only new report jobs"):
        freeze_job(job, fixture_routing(job), {}, private_store)


def test_empty_usage_preserves_unknown_token_counts() -> None:
    original = replace(snapshot(), totals=Totals())
    result = collection_from_dict(collection_to_dict(original))
    assert result.totals.prompt_tokens is None and result.totals.completion_tokens is None
    assert result.totals.usage == []


@pytest.mark.parametrize("field,value", [("selection", None), ("query", []), ("totals", None)])
def test_malformed_collection_objects_fail_cleanly(field: str, value: Any) -> None:
    data = collection_to_dict(snapshot())
    data[field] = value
    with pytest.raises(ValueError):
        collection_from_dict(data)
