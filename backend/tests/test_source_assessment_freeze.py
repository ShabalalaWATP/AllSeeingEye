"""New frozen assessments retain the exact historical rating and origin decisions."""

import json
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta

import pytest

from ase.domain.events import Reliability
from ase.domain.origin_chains import analyse_origin_chains
from ase.domain.origin_records import OriginObservation, OriginRelation
from ase.domain.source_assessment import Assessor
from ase.domain.source_assessment_policy import (
    append_rating_revision,
    freeze_source_assessment,
    resolve_source_assessment,
)
from source_assessment_helpers import NOW, assertion, edge, node, review, source


def assessment(history=(), **changes):
    return resolve_source_assessment(
        **{
            "evidence_id": "E1",
            "claim_id": "C1",
            "source_id": "statistics-office",
            "subject": "population-statistics",
            "source_history": history,
            "assertion_history": (assertion(),),
            **changes,
        }
    )


def test_later_source_revision_and_detached_json_edits_cannot_change_historical_snapshot():
    first = source()
    origins = analyse_origin_chains([node()])
    frozen = freeze_source_assessment(assessment((first,)), origins, frozen_at=NOW)
    before = json.dumps(frozen.to_dict(), sort_keys=True)
    changed = source(
        Reliability.E,
        review=review(
            "r2",
            assessor=Assessor.REVIEWER,
            reviewed_at=NOW,
            supersedes="r1",
        ),
    )
    history = append_rating_revision((first,), changed)
    current = freeze_source_assessment(assessment(history), origins, frozen_at=NOW)
    assert current.to_dict()["assessment"]["reliability"] == "E"
    assert frozen.to_dict()["assessment"]["reliability"] == "A"
    detached = frozen.to_dict()
    detached["assessment"]["reliability"] = "E"
    detached["origin_group"]["member_ids"].append("invented")
    assert json.dumps(frozen.to_dict(), sort_keys=True) == before
    with pytest.raises(FrozenInstanceError):
        frozen.frozen_at = NOW + timedelta(days=1)


def test_origin_review_changes_current_snapshot_without_rewriting_earlier_proposal():
    proposed = analyse_origin_chains([node(), node("N2")], [edge()])
    first = freeze_source_assessment(assessment(), proposed, frozen_at=NOW)
    reviewed = analyse_origin_chains(
        [node(), node("N2")],
        [
            edge(
                reviewer_id="reviewer-1",
                reviewed_at=NOW,
                rejected=True,
            )
        ],
    )
    current = freeze_source_assessment(assessment(), reviewed, frozen_at=NOW)
    assert first.to_dict()["relationships"][0]["status"] == "proposal"
    assert len(first.origin_group.member_ids) == 2
    assert len(current.origin_group.member_ids) == 1
    assert current.to_dict()["relationships"][0]["status"] == "rejected"
    assert {row.id for row in current.origin_nodes} == {"N1", "N2"}


def test_frozen_provenance_contains_endpoint_identity_reason_and_observable_reference():
    observation = OriginObservation(
        "P2", "E2", "passage", "retained-exact-passage-2", OriginRelation.TRANSLATION, "E1", "C1"
    )
    origins = analyse_origin_chains(
        [node(), node("N2")], [edge(observation_ids=("P2",))], observations=[observation]
    )
    frozen = freeze_source_assessment(assessment(), origins, frozen_at=NOW).to_dict()
    assert {row["id"] for row in frozen["origin_nodes"]} == {"N1", "N2"}
    assert frozen["observations"][0]["reference"] == "retained-exact-passage-2"
    assert frozen["relationships"][0]["edge"]["reason"]
    assert frozen["relationships"][0]["edge"]["method"] == "origin-proposal-v1"


@pytest.mark.parametrize(
    "changed",
    [
        {"source_id": "other"},
        {"claim_id": "other"},
        {"evidence_id": "other"},
    ],
)
def test_freeze_rejects_inconsistent_origin_and_assessment_identity(changed):
    with pytest.raises(ValueError, match="exactly one"):
        freeze_source_assessment(
            assessment(**changed), analyse_origin_chains([node()]), frozen_at=NOW
        )


def test_freeze_cannot_predate_applied_grades_or_origin_relationships():
    with pytest.raises(ValueError, match="predate"):
        freeze_source_assessment(
            assessment((source(),)),
            analyse_origin_chains([node()]),
            frozen_at=NOW - timedelta(seconds=1),
        )
    future = edge(recorded_at=NOW + timedelta(seconds=1))
    with pytest.raises(ValueError, match="predate"):
        freeze_source_assessment(
            assessment(), analyse_origin_chains([node(), node("N2")], [future]), frozen_at=NOW
        )


def test_direct_construction_cannot_detach_grades_from_their_applied_revisions():
    with pytest.raises(ValueError):
        replace(assessment(), reliability=Reliability.A)
    with pytest.raises(ValueError):
        replace(assessment((source(),)), source_id="other")
