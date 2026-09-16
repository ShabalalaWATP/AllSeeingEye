"""Economic relevance is decided by readable rules, using headlines the page really served."""

import pytest

from ase.domain.economy_relevance import assess_relevance

# Seen on the live page in a two-day window: only the last one was economic reporting.
SERVED = (
    "AI app ads promoting 'objectification of women' banned by watchdog",
    "The extreme engineering of aircraft windows",
    "We are all new job starters - here's how we got through the first few days",
    "Complaints to watchdog about water firms jump 84%",
    "Nvidia boss says AI 'doesn't need new laws' as safety concerns grow",
)


@pytest.mark.parametrize("title", SERVED)
def test_soft_business_features_are_refused_with_a_reason(title: str) -> None:
    verdict = assess_relevance(title)
    assert not verdict.passed
    assert verdict.reason


def test_a_company_word_and_a_percentage_are_not_enough_on_their_own() -> None:
    verdict = assess_relevance("Complaints to watchdog about water firms jump 84%")
    assert not verdict.passed and verdict.reason == "No economic subject matter in the headline"


@pytest.mark.parametrize(
    "title",
    [
        "Will China's new local surtax provide relief for its regions' fiscal headaches?",
        "US inflation rose to 3.1% in August",
        "Sterling falls against the dollar after weak jobs data",
        "Nvidia quarterly earnings beat forecasts as data centre revenue jumps",
        "Treasury raises borrowing forecast as debt interest climbs",
    ],
)
def test_economic_reporting_is_kept_and_says_why(title: str) -> None:
    verdict = assess_relevance(title)
    assert verdict.passed
    assert verdict.reason.startswith("Economic subject matter")
    assert verdict.themes


def test_an_official_issuer_release_outranks_general_coverage() -> None:
    official = assess_relevance("Bank rate maintained at 4%", official=True)
    general = assess_relevance("Shoppers feel the squeeze as prices rise")
    assert official.passed and general.passed
    assert official.tier < general.tier
    assert "Official economic issuer release" in official.reason


def test_a_declared_country_remit_lifts_the_score_without_carrying_a_headline() -> None:
    plain = assess_relevance("Aircraft window design explained")
    remitted = assess_relevance("Aircraft window design explained", remit=True)
    assert not plain.passed and not remitted.passed
    kept = assess_relevance("Inflation eases", remit=True)
    assert kept.passed and kept.score > assess_relevance("Inflation eases").score
