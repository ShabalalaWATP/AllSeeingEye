"""Discovery geography is feed scope, not publisher nationality or event location."""

import pytest

from ase.domain.source_discovery import source_coverage


@pytest.mark.parametrize(
    ("source_id", "countries"),
    [
        ("meduza_ru", ("RU",)),
        ("research_regional_meduza_ru", ("RU",)),
        ("research_regional_hrana_en", ("IR",)),
        ("cdt_zh", ("CN",)),
        ("research_social_reddit_ukrainianconflict", ("UA", "RU")),
        ("research-companies-house-officers", ("GB",)),
        ("research-sec-submissions", ("US",)),
    ],
)
def test_explicit_focus_and_derivatives(source_id: str, countries: tuple[str, ...]) -> None:
    coverage = source_coverage(source_id)
    assert coverage.scope == "regional"
    assert coverage.countries == countries
    assert coverage.note


@pytest.mark.parametrize("source_id", ["bbc_world", "gov_uk_travel_advice", "aisstream"])
def test_international_feeds_are_not_assigned_publisher_country(source_id: str) -> None:
    coverage = source_coverage(source_id)
    assert coverage.scope == "global"
    assert coverage.countries == ()


def test_edition_and_language_do_not_imply_nation() -> None:
    assert source_coverage("research_google_news_ru").countries == ()
    assert source_coverage("research_google_news_ru").scope == "global"
    assert source_coverage("custom_news_zh").scope == "unspecified"
    assert source_coverage("research_regional_custom_ru").countries == ()


def test_finnish_receiver_coverage_is_distinct_from_worldwide_shipping() -> None:
    coverage = source_coverage("digitraffic_ais")
    assert coverage.countries == ("FI",)
    assert coverage.regions == ("Baltic Sea",)
    assert "not global" in coverage.note


def test_regional_ocean_coverage_does_not_invent_countries() -> None:
    coverage = source_coverage("nhc_atlantic")
    assert coverage.scope == "regional"
    assert coverage.regions == ("Atlantic Ocean",)
    assert coverage.countries == ()
