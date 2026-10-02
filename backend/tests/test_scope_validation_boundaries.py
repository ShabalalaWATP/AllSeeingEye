"""Service validation is enforced for non-HTTP callers as well as request models."""

import pytest

from ase.application.reports.templates import TEMPLATES
from ase.application.schedules.definition import ScheduleInput
from ase.application.schedules.validation import validate_subscription_scope
from ase.application.teams.validation import team_description
from ase.domain.errors import InvalidRequest
from ase.domain.research import ResearchFocus


@pytest.mark.parametrize(
    "overrides,template,reason",
    [
        ({"conflict_id": "ukraine", "hazard": "earthquake"}, "intsum", "not both"),
        ({"conflict_id": "ukraine", "research_focus": ResearchFocus.COMPANY}, "intsum", "general"),
        ({"conflict_id": " "}, "intsum", "valid conflict"),
        ({"conflict_id": "x" * 121}, "intsum", "valid conflict"),
        ({}, "disaster_sitrep", "Choose a natural hazard"),
        ({"avoid_repetition": "yes"}, "intsum", "enabled or disabled"),
        ({"disclose_area_to_provider": "yes"}, "intsum", "enabled or disabled"),
    ],
)
def test_invalid_subscription_scope_is_rejected(overrides, template, reason):
    data = ScheduleInput("Scope test", template, **overrides)
    with pytest.raises(InvalidRequest, match=reason):
        validate_subscription_scope(data, TEMPLATES[template])


@pytest.mark.parametrize("description", ["x" * 501, "control\x00character"])
def test_team_description_is_bounded_and_printable(description):
    with pytest.raises(InvalidRequest, match="printable"):
        team_description(description)
