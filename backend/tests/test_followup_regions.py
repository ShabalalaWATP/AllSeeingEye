"""Regional scope remains frozen independently of explicit country choices."""

from dataclasses import replace

import pytest

from ase.application.reports.followup_scope import require_followup_scope
from ase.application.reports.request import ReportRequest
from ase.application.reports.scope import report_scope
from ase.application.reports.templates import TEMPLATES
from ase.domain.errors import InvalidRequest
from ase.domain.regions import Region
from ase.domain.research import ResearchMode


def regional_request(countries=()):
    return ReportRequest(
        "ask",
        question="What changed?",
        research_mode=ResearchMode.QUICK,
        regions=(Region.EUROPE, Region.MIDDLE_EAST),
        country_isos=countries,
    )


@pytest.mark.parametrize("countries", [(), ("US",)])
@pytest.mark.parametrize("regions", [(), (Region.EUROPE,), (Region.ASIA,)])
def test_followup_rejects_changed_regions_even_when_countries_match(countries, regions):
    original = regional_request(countries)
    saved = report_scope(original, TEMPLATES["ask"])
    assert saved["countries"] == list(countries)
    with pytest.raises(InvalidRequest, match="regions"):
        require_followup_scope(saved, replace(original, regions=regions))


@pytest.mark.parametrize("countries", [(), ("US",)])
def test_followup_accepts_same_normalised_regions_and_explicit_countries(countries):
    original = regional_request(countries)
    saved = report_scope(original, TEMPLATES["ask"])
    require_followup_scope(saved, replace(original, regions=tuple(reversed(original.regions))))


@pytest.mark.parametrize("malformed", ["europe", ["unknown"], None])
def test_invalid_saved_regions_fail_closed(malformed):
    original = regional_request()
    saved = {**report_scope(original, TEMPLATES["ask"]), "regions": malformed}
    with pytest.raises(InvalidRequest, match="invalid research scope"):
        require_followup_scope(saved, original)


def test_legacy_parent_without_regions_keeps_country_scope():
    original = replace(regional_request(("GB",)), regions=())
    saved = report_scope(original, TEMPLATES["ask"])
    assert "regions" not in saved
    require_followup_scope(saved, original)
