"""A region is a collection choice over countries the application already knows."""

import json
from importlib.resources import files

import pytest

from ase.application.reports.request import ReportRequest
from ase.application.reports.scope import report_scope
from ase.application.reports.templates import TEMPLATES
from ase.domain.regions import (
    MAX_REGIONS,
    REGION_COUNTRIES,
    REGION_LABELS,
    Region,
    normalise_regions,
    region_countries,
)


def test_every_packaged_country_belongs_to_exactly_one_continent():
    packaged = {
        row["iso2"]
        for row in json.loads(
            files("ase.resources").joinpath("countries_110m.json").read_text("utf-8")
        )["countries"]
    }
    continents = [region for region in Region if region is not Region.MIDDLE_EAST]
    for iso in packaged:
        homes = [region for region in continents if iso in REGION_COUNTRIES[region]]
        assert len(homes) == 1, (iso, homes)
    assert set().union(*(REGION_COUNTRIES[region] for region in continents)) == packaged
    # The Middle East overlaps on purpose and names nothing the outlines lack.
    assert REGION_COUNTRIES[Region.MIDDLE_EAST] <= packaged
    assert set(REGION_LABELS) == set(Region)


def test_regions_normalise_to_known_values_in_order_without_repeats():
    assert normalise_regions(["Europe", "europe", " asia "]) == (Region.EUROPE, Region.ASIA)
    assert normalise_regions(()) == ()
    with pytest.raises(ValueError, match="Unknown region"):
        normalise_regions(["atlantis"])
    with pytest.raises(ValueError, match="Regions must be a list"):
        normalise_regions("europe")
    # Every region at once is the largest valid choice; the bound admits it exactly.
    assert len(normalise_regions(list(Region) * 2)) == len(Region) <= MAX_REGIONS


def test_region_countries_union_is_sorted_and_deduplicated():
    both = region_countries((Region.MIDDLE_EAST, Region.EUROPE))
    assert both == tuple(sorted(set(both)))
    assert "TR" in both and "GB" in both and "US" not in both
    assert region_countries(()) == ()


def test_a_request_freezes_its_regions_in_the_scope_and_restores_them():
    request = ReportRequest(
        template_id="ask", question="What changed?", regions=("europe", "middle_east")
    )
    assert request.regions == (Region.EUROPE, Region.MIDDLE_EAST)
    scope = report_scope(request, TEMPLATES["ask"])
    assert scope["regions"] == ["europe", "middle_east"]
    restored = ReportRequest.from_scope("ask", scope)
    assert restored.regions == request.regions
    assert "regions" not in report_scope(ReportRequest(template_id="ask"), TEMPLATES["ask"])
    with pytest.raises(ValueError, match="Unknown region"):
        ReportRequest(template_id="ask", regions=("nowhere",))
