"""Brief-derived subscriptions retain history without changing analytical compatibility."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from ase.application.schedules.manage import ScheduleInput, build_schedule
from ase.application.schedules.revision_snapshot import (
    request_from_revision,
    revision_from_schedule,
)
from ase.domain.research_brief_values import BriefQuestion, IntelligenceRequirement
from ase.domain.subscription_snapshots import decode_snapshot
from test_research_brief_persistence import _brief


def _schedule():
    now = datetime(2026, 9, 20, tzinfo=UTC)
    brief = replace(
        _brief(),
        question=BriefQuestion(
            "What changed?", (IntelligenceRequirement("IR1", "What changed in energy supply?"),)
        ),
    )
    schedule = build_schedule(
        ScheduleInput(
            name="Brief updates",
            template_id="ask",
            question=brief.question.main,
            brief_id=brief.identity.id,
            brief_revision=brief.identity.revision,
        ),
        schedule_id=uuid4(),
        owner=brief.identity.owner_id,
        created=now,
        now=now,
    )
    return schedule, brief


def test_brief_history_roundtrip_preserves_requirements_and_stable_fingerprint():
    schedule, brief = _schedule()
    before = revision_from_schedule(schedule, 1, brief=brief)
    baseline = uuid4()
    updated = replace(schedule, baseline_report_id=baseline, seen_content_signatures=("a" * 64,))
    after = revision_from_schedule(updated, 2, brief=brief)
    request = request_from_revision(after)
    assert request.subscription_previous_report_id == baseline
    assert request.subscription_seen_signatures == ("a" * 64,)
    assert request.canonical_requirements == brief.question.requirements
    assert after.request_snapshot != before.request_snapshot
    assert after.compatibility_fingerprint == before.compatibility_fingerprint
    assert (
        decode_snapshot(after.request_snapshot)["brief_ref"]["revision"] == brief.identity.revision
    )
    # Previously frozen history-free revisions keep their original meaning.
    assert request_from_revision(before).subscription_previous_report_id is None
    assert request_from_revision(before).subscription_seen_signatures == ()


def test_brief_repetition_opt_out_omits_saved_history():
    schedule, brief = _schedule()
    schedule = replace(
        schedule,
        avoid_repetition=False,
        baseline_report_id=uuid4(),
        seen_content_signatures=("b" * 64,),
    )
    restored = request_from_revision(revision_from_schedule(schedule, 1, brief=brief))
    assert restored.subscription_previous_report_id is None
    assert restored.subscription_seen_signatures == ()


def test_brief_authored_question_changes_compatibility_even_with_same_history():
    schedule, brief = _schedule()
    original = revision_from_schedule(schedule, 1, brief=brief)
    revised = replace(brief, question=BriefQuestion("What changed in another sector?"))
    changed = revision_from_schedule(schedule, 2, brief=revised)
    assert changed.compatibility_fingerprint != original.compatibility_fingerprint
