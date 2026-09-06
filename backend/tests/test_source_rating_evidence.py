"""Selected evidence carries immutable source context without changing its event grades."""

from dataclasses import replace
from datetime import timedelta

from ase.adapters.store.memory import InMemoryEventStore
from ase.api.schemas_report_evidence import ReportEvidenceOut
from ase.api.schemas_source_ratings import SourceRatingOut
from ase.application.feeds.grading import profiles_from_specs
from ase.application.reports.selection import select_evidence
from ase.application.reports.templates import TEMPLATES
from ase.domain.events import Reliability
from ase.domain.evidence import EvidenceItem
from ase.domain.source_ratings import source_rating_for
from feeds_helpers import NOW, make_event, make_spec


def test_selected_rating_is_a_frozen_snapshot_and_does_not_replace_item_grades():
    spec = replace(make_spec(), id="bbc_world", reliability=Reliability.B, rating=None)
    profiles = profiles_from_specs([spec])
    event = make_event("item", source_id=spec.id).with_changes(reliability=Reliability.B)
    store = InMemoryEventStore()
    store.upsert([event])
    selected = select_evidence(store, profiles, TEMPLATES["intsum"].strategy, now=NOW).items[0]
    assert selected.source_rating is spec.rating
    assert selected.grade == event.grade and selected.reliability == event.reliability.value
    assert spec.rating is not None
    profiles[spec.id] = replace(
        profiles[spec.id],
        rating=replace(spec.rating, basis="A later registry assessment."),
    )
    assert selected.source_rating.basis != profiles[spec.id].rating.basis
    output = ReportEvidenceOut.model_validate(selected).model_dump(mode="json")
    assert output["source_rating"]["assessed_grade"] == "B"
    assert output["source_rating"]["reviewed_at"] is None
    assert output["grade"] == event.grade


def test_new_unknown_evidence_is_explicitly_unassessed_but_legacy_absence_stays_null():
    event = make_event("unknown")
    store = InMemoryEventStore()
    store.upsert([event])
    selected = select_evidence(store, {}, TEMPLATES["intsum"].strategy, now=NOW).items[0]
    assert selected.source_rating is not None
    assert selected.source_rating.status == "unassessed"
    assert selected.source_rating.assessed_grade is None
    assert selected.grade == event.grade
    legacy = EvidenceItem.from_event("E1", event, NOW, source_name="Unknown", independence_key="")
    assert legacy.source_rating is None
    assert ReportEvidenceOut.model_validate(legacy).source_rating is None


def test_api_preserves_source_rating_scope_and_explicit_review_date_without_inventing_one():
    original = source_rating_for("google_news_watchlists", Reliability.C)
    output = SourceRatingOut.model_validate(original)
    assert output.provenance_role == "aggregator"
    assert output.publisher_reliability_assessed is False
    assert output.reviewed_at is None
    reviewed = replace(original, reviewed_at=NOW)
    assert SourceRatingOut.model_validate(reviewed).reviewed_at == NOW
    assert original.reviewed_at is None


def test_current_collection_cannot_be_captured_before_it_was_observed():
    observed = NOW + timedelta(seconds=30)
    published = NOW - timedelta(hours=2)
    event = make_event(published_at=published, observed_at=observed)
    frozen = EvidenceItem.from_event("E1", event, NOW, source_name="Source", independence_key="")
    assert frozen.captured_at == observed
    assert frozen.observed_at == observed and frozen.published_at == published
    later = observed + timedelta(seconds=10)
    captured = EvidenceItem.from_event(
        "E1", event, later, source_name="Source", independence_key=""
    )
    assert captured.captured_at == later
