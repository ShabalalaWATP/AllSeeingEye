"""Resumed production retains frozen collection labels, source context and usage totals."""

import copy
import json
from dataclasses import replace
from datetime import timedelta
from typing import Any

import pytest

from ase.application.report_jobs.collection_records import query_from_dict, query_to_dict
from ase.application.reports.production_checkpoint import (
    ProductionSnapshot,
    collection_from_dict,
    collection_to_dict,
)
from ase.application.reports.selection import Selection
from ase.domain.direction import Direction
from ase.domain.evidence_geometry import EvidenceGeometry, LocationRole
from ase.domain.observation import ObservationMetadata
from ase.domain.research import CollectionAttempt, CollectionPass, CollectionStatus, ResearchQuery
from ase.domain.research_area import direct_area_from_geometry
from ase.domain.research_plan import QueryTransformation, QueryVariant, ResearchPlan, ResearchTask
from ase.domain.research_records import ResearchReceipt
from ase.domain.research_tasks import PlannedQueryTask, ResearchCandidate
from ase.domain.source_dates import resolve_source_date
from ase.domain.validation import Finding, Severity
from feeds_helpers import NOW
from report_job_snapshot_helpers import PRIVATE_SENTINEL, fixture_evidence, fixture_totals


def snapshot() -> ProductionSnapshot:
    candidate = ResearchCandidate("C1", "Possible company", ("Unverified name",), origin="model")
    task = PlannedQueryTask("T1", "test_source", "disambiguation", ("company",), "C1", "model")
    variant = QueryVariant("en", ("company",))
    query = ResearchQuery(
        "What is known?",
        NOW - timedelta(days=2),
        NOW,
        terms=("company",),
        candidate_hypotheses=(candidate,),
        planned_tasks=(task,),
        query_variants=(variant,),
        source_ids=("test_source",),
        country_isos=("GB", "US"),
        research_web_search=True,
    )
    attempt = CollectionAttempt(
        "test_source",
        "Fixture source",
        CollectionStatus.COMPLETED,
        1,
        "One public item",
        task_id="model:T1",
        purpose="disambiguation",
        candidate_id="C1",
        query_variant=variant,
    )
    plan_task = ResearchTask(
        "test_source",
        "Fixture source",
        True,
        True,
        "en",
        ("company",),
        "model",
        task_id="model:T1",
        purpose="disambiguation",
        candidate_id="C1",
    )
    plan = ResearchPlan(
        query.question,
        query.since,
        query.until,
        query.languages,
        (plan_task,),
        8,
        30.0,
        100,
        candidate_hypotheses=(candidate,),
        translation=QueryTransformation(("company",), ("en",), "fixture", "completed", (variant,)),
        country_isos=("GB", "US"),
        research_web_search=True,
    )
    receipt = ResearchReceipt.build(
        query, (attempt,), 1, plan, (CollectionPass(("company",), (attempt,), plan),)
    )
    totals = fixture_totals()
    totals.findings.append(
        Finding("research_notice", Severity.WARNING, "collection", "Coverage is incomplete.")
    )
    return ProductionSnapshot(
        Selection((fixture_evidence(),), 0, 4), Direction(query.question), receipt, query, totals
    )


def test_collection_roundtrip_preserves_labels_runtime_planning_and_receipts() -> None:
    original = snapshot()
    value = collection_to_dict(original)
    result = collection_from_dict(json.loads(json.dumps(value)))
    assert result.selection == original.selection
    assert result.direction == original.direction and result.query == original.query
    assert result.receipt == original.receipt
    assert result.query and result.query.planned_tasks[0].origin == "model"
    assert result.totals.prompt_tokens == 200 and result.totals.completion_tokens == 50
    assert result.totals.findings == original.totals.findings
    assert result.totals.usage[0].error is None and result.totals.usage[0].id is None
    assert PRIVATE_SENTINEL not in json.dumps(value)
    assert collection_to_dict(result) == value


def test_snapshot_detaches_mutable_totals_and_scope() -> None:
    value = collection_to_dict(snapshot())
    result = collection_from_dict(value)
    value["totals"]["usage"][0]["purpose"] = "changed"
    value["query"]["terms"].append("changed")
    assert result.totals.usage[0].purpose == "report-direction"
    assert result.query and result.query.terms == ("company",)


def test_empty_collection_without_direction_or_research_is_resumable() -> None:
    original = replace(
        snapshot(), selection=Selection((), 0, 0), direction=None, receipt=None, query=None
    )
    result = collection_from_dict(collection_to_dict(original))
    assert result.selection == Selection((), 0, 0)
    assert result.direction is None and result.query is None and result.receipt is None


@pytest.mark.parametrize(
    "path,value",
    [
        (("schema_version",), 2),
        (("schema_version",), True),
        (("selection", "considered"), -1),
        (("selection", "considered"), 0),
        (("selection", "flagged"), 5),
        (("selection", "flagged"), True),
        (("selection", "items", 0, "credibility"), True),
        (("selection", "items", 0, "summary"), ["not text"]),
        (("selection", "items", 0, "grade"), "A6"),
        (("selection", "items", 0, "lat"), 91),
        (("selection", "items", 0, "captured_at"), "2026-09-05T00:00:00"),
        (("selection", "items", 0, "password"), "forbidden"),
        (("selection", "items", 0, "new_field"), "not silently dropped"),
        (("direction", "pir"), 3),
        (("direction", "unknown"), "not silently dropped"),
        (("receipt", "collected_items"), -1),
        (("receipt", "collected_items"), True),
        (("receipt", "plan", "model_calls"), -1),
        (("receipt", "plan", "seconds_limit"), float("inf")),
        (("receipt", "attempts", 0, "result_count"), True),
        (("receipt", "plan", "tasks", 0, "selected"), "false"),
        (("query", "research_web_search"), 1),
        (("query", "question"), 7),
        (("totals", "prompt_tokens"), -1),
        (("totals", "prompt_tokens"), True),
        (("totals", "latency_ms"), float("nan")),
        (("totals", "usage", 0, "ok"), 1),
        (("totals", "usage", 0, "error"), "forbidden"),
        (("totals", "usage", 0, "id"), 45),
        (("totals", "usage", 0, "purpose"), "A full prompt"),
        (("totals", "findings", 0, "message"), ["not text"]),
    ],
)
def test_rejects_malformed_nested_collection_records(path: tuple[Any, ...], value: Any) -> None:
    data = collection_to_dict(snapshot())
    destination = data
    for key in path[:-1]:
        destination = destination[key]
    destination[path[-1]] = value
    with pytest.raises(ValueError):
        collection_from_dict(data)


def test_duplicate_evidence_identity_cannot_change_labels_on_resume() -> None:
    data = collection_to_dict(snapshot())
    duplicate = copy.deepcopy(data["selection"]["items"][0])
    duplicate["label"] = "E2"
    data["selection"]["items"].append(duplicate)
    with pytest.raises(ValueError, match="Duplicate"):
        collection_from_dict(data)


def test_oversized_evidence_and_usage_collections_are_rejected() -> None:
    data = collection_to_dict(snapshot())
    data["selection"]["items"] *= 101
    with pytest.raises(ValueError):
        collection_from_dict(data)
    data = collection_to_dict(snapshot())
    data["totals"]["usage"] *= 257
    with pytest.raises(ValueError):
        collection_from_dict(data)


def test_collection_size_budget_is_separate_from_job_repository_budget() -> None:
    data = collection_to_dict(snapshot())
    data["selection"]["items"][0]["summary"] = "x" * (768 * 1024)
    with pytest.raises(ValueError, match="size budget"):
        collection_from_dict(data)


def test_drawn_area_query_roundtrips_without_public_provider_disclosure_fields() -> None:
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
                            [[0.0, 50.0], [0.1, 50.0], [0.1, 50.1], [0.0, 50.0]],
                        ],
                    },
                },
            ],
        }
    )
    query = ResearchQuery("What happened here?", NOW - timedelta(days=1), NOW, area=area)
    assert query_from_dict(query_to_dict(query)) == query


def test_integral_gateway_latency_is_normalised_without_losing_usage() -> None:
    original = snapshot()
    original.totals.latency_ms = 10
    original.totals.usage[0].latency_ms = 10
    restored = collection_from_dict(collection_to_dict(original))
    assert restored.totals.latency_ms == 10.0 and restored.totals.usage[0].latency_ms == 10.0


def test_observation_geometry_and_calendar_day_provenance_are_retained() -> None:
    original = snapshot()
    geometry = EvidenceGeometry(
        '{"type":"Point","coordinates":[0,50]}',
        LocationRole.OBSERVATION_FOOTPRINT,
        "approximate",
        "source",
        "test_source",
        "Public source",
    )
    item = replace(
        fixture_evidence(),
        geometry=geometry,
        observation=ObservationMetadata(NOW, "collection", "scene", "No ground truth"),
        source_dates=(resolve_source_date("2026-09-04", "date", "gregorian"),),
    )
    original = replace(original, selection=Selection((item,), 0, 1))
    restored = collection_from_dict(collection_to_dict(original))
    assert restored.selection.items == (item,)


@pytest.mark.parametrize("item", [None, 3, "wrong type", {}, {"label": "E1"}])
def test_malformed_evidence_fails_with_a_controlled_value_error(item: Any) -> None:
    data = collection_to_dict(snapshot())
    data["selection"]["items"] = [item]
    with pytest.raises(ValueError):
        collection_from_dict(data)
