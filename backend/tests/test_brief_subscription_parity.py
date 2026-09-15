"""One-off and recurring brief conversion honour the same supported choices."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from ase.application.research.brief_conversion import run_request_from_brief
from ase.application.schedules.brief_link import standing_request_from_brief
from ase.application.schedules.manage import ScheduleInput, build_schedule
from ase.application.schedules.revision_snapshot import (
    request_from_revision,
    revision_from_schedule,
)
from ase.domain.research import ResearchMode
from ase.domain.research_brief_scope import BriefCollection, BriefObservation
from ase.domain.research_brief_values import (
    BriefLens,
    BriefLimits,
    BriefMonitoring,
    BriefOutput,
    BriefQuestion,
    BriefValidationError,
    IntelligenceRequirement,
    LensId,
)
from test_research_brief_persistence import _brief


def test_twelve_supported_questions_and_authored_options_have_one_frozen_meaning() -> None:
    now = datetime(2026, 9, 15, 12, tzinfo=UTC)
    original = _brief()
    brief = replace(
        original,
        question=BriefQuestion(
            "What changed in energy supply?",
            tuple(
                IntelligenceRequirement(f"IR-{index}", f"Question {index}?", priority=index)
                for index in range(1, 13)
            ),
        ),
        observation=BriefObservation("relative", lookback_hours=48),
        lens=BriefLens(challenge_conclusions=True),
        collection=BriefCollection(
            languages=("en", "fr"),
            terms=("energy",),
            source_policy="selected_only",
            source_ids=("gdelt_news",),
            web_search=True,
        ),
        output=BriefOutput(
            depth=ResearchMode.ADVANCED,
            language="fr",
            style="briefing",
            template_id="ask",
        ),
    )
    once = run_request_from_brief(brief, now=now)
    standing = standing_request_from_brief(brief, now=now)
    due = replace(
        standing,
        window_hours=None,
        research_since=now - timedelta(hours=48),
        research_until=now,
    )
    assert due == replace(once, automation=True)
    schedule = build_schedule(
        ScheduleInput(
            name="Energy supply updates",
            template_id="ask",
            question=brief.question.main,
            research_mode=ResearchMode.ADVANCED,
            research_languages=brief.collection.languages,
            research_web_search=True,
            research_source_ids=brief.collection.source_ids,
            window_hours=48,
            brief_id=brief.identity.id,
            brief_revision=brief.identity.revision,
        ),
        schedule_id=uuid4(),
        owner=brief.identity.owner_id,
        created=now,
        now=now,
    )
    frozen = revision_from_schedule(schedule, 1, brief=brief)
    assert request_from_revision(frozen) == standing


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        (
            {"question": BriefQuestion("What changed?", exclusions=("Exclude rumours",))},
            "question.exclusions",
        ),
        ({"lens": BriefLens(id=LensId.UK_POLICY)}, "lens.id"),
        ({"lens": BriefLens(audience="Policy staff")}, "lens.audience"),
        ({"collection": BriefCollection(require_primary=True)}, "collection.require_primary"),
        ({"collection": BriefCollection(require_local=True)}, "collection.require_local"),
        ({"collection": BriefCollection(require_opposition=True)}, "collection.require_opposition"),
        (
            {"output": BriefOutput(ResearchMode.QUICK, preferred_sections=("timeline",))},
            "output.preferred_sections",
        ),
        (
            {"output": BriefOutput(ResearchMode.QUICK, chart_preference="prefer")},
            "output.chart_preference",
        ),
        ({"limits": BriefLimits(max_model_calls=10)}, "limits.max_model_calls"),
        ({"monitoring": BriefMonitoring(prefer_novelty=True)}, "monitoring.prefer_novelty"),
    ],
)
def test_unsupported_execution_choices_fail_at_both_admission_boundaries(changes, field) -> None:
    brief = replace(_brief(), **changes)
    now = datetime(2026, 9, 15, tzinfo=UTC)
    for convert in (run_request_from_brief, standing_request_from_brief):
        with pytest.raises(BriefValidationError) as error:
            convert(brief, now=now)
        assert error.value.field == field
        assert "Policy staff" not in str(error.value)
