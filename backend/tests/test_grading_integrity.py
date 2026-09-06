"""Topic overlap is a discovery signal, never proof that a claim is true."""

from dataclasses import replace

import pytest

from ase.domain.events import Credibility, Reliability
from ase.domain.grading import SourceProfile, grade_events, title_tokens
from grading_helpers import PROFILES, news


@pytest.mark.parametrize(
    "opposing",
    [
        "Soldiers did not seize border city after overnight assault",
        "Soldiers didn't seize border city after overnight assault",
        "Soldiers never seized border city after overnight assault",
        "Officials deny soldiers seized border city after overnight assault",
    ],
)
def test_opposing_headlines_are_related_but_never_corroboration(opposing: str) -> None:
    events = [
        news("negative", "bbc", opposing),
        news("affirmative", "aljazeera", "Soldiers seize border city after overnight assault"),
        news("third", "reuters_via_guardian", "Border city seized by soldiers in night assault"),
    ]
    graded = grade_events(events, PROFILES)
    assert len({item.story_id for item in graded}) == 1
    assert {item.credibility for item in graded} == {Credibility.CANNOT_BE_JUDGED}
    assert all("negation or qualification" in item.rationale for item in graded)
    assert all("not verified" in item.rationale for item in graded)


def test_matching_affirmative_headlines_do_not_establish_claim_agreement() -> None:
    events = [
        news("first", "bbc", "Soldiers seize border city after overnight assault"),
        news("second", "aljazeera", "Soldiers capture border city in assault"),
        news("third", "reuters_via_guardian", "Border city seized by soldiers overnight"),
    ]
    for item in grade_events(events, PROFILES):
        assert item.credibility is Credibility.CANNOT_BE_JUDGED
        assert "claim agreement" in item.rationale
        assert "not verified" in item.rationale


def test_negation_survives_topic_tokenisation() -> None:
    assert "not" in title_tokens(news("negative", "bbc", "Soldiers did not seize border city"))
    assert "no" in title_tokens(news("negative", "bbc", "No soldiers seized border city"))


def test_same_area_is_context_not_a_truth_assessment() -> None:
    events = [
        news("first", "bbc", "Minister appointed in Khartoum"),
        news("second", "aljazeera", "Railway workers protest at station"),
    ]
    for item in grade_events(events, PROFILES):
        assert item.credibility is Credibility.CANNOT_BE_JUDGED
        assert "Area/category context" in item.rationale
        assert "corroboration" in item.rationale


def test_source_reliability_does_not_determine_item_credibility() -> None:
    event = news("first", "bbc", "Soldiers seize border city after overnight assault")
    for reliability in Reliability:
        item = grade_events([replace(event, reliability=reliability)], PROFILES)[0]
        assert item.credibility is Credibility.CANNOT_BE_JUDGED
        assert item.apply().reliability is reliability


def test_instrument_data_remains_provisional_not_independently_verified() -> None:
    profile = SourceProfile("sensor", "sensor", "Sensor", instrument=True)
    event = news("sensor", "sensor", "Magnitude six earthquake recorded offshore")
    graded = grade_events([event], {"sensor": profile})[0]
    assert graded.credibility is Credibility.PROBABLY_TRUE
    assert "provisional" in graded.rationale.lower()
    assert "not independently verified" in graded.rationale


def test_untranslated_reporting_is_unassessed_until_a_translation_exists() -> None:
    event = replace(news("first", "bbc", "Soldaten nehmen Grenzstadt ein"), language="de")
    graded = grade_events([event], PROFILES)[0]
    assert graded.credibility is Credibility.CANNOT_BE_JUDGED
    assert "Untranslated item" in graded.rationale
    translated = replace(event, title_en="Soldiers did not take border city")
    assert "negation or qualification" in grade_events([translated], PROFILES)[0].rationale


def test_interested_party_policy_is_explicit_and_never_verified() -> None:
    profile = SourceProfile("party", "party", "Party", flags=frozenset({"interested_party"}))
    graded = grade_events([news("first", "party", "Border city captured")], {"party": profile})
    assert graded[0].credibility is Credibility.POSSIBLY_TRUE
    assert graded[0].rationale == "Interested party, uncorroborated"


def test_qualified_instrument_headline_cannot_receive_provisional_grade_two() -> None:
    profile = SourceProfile("sensor", "sensor", "Sensor", instrument=True)
    event = news("first", "sensor", "Unconfirmed earthquake reported offshore")
    graded = grade_events([event], {"sensor": profile})[0]
    assert graded.credibility is Credibility.CANNOT_BE_JUDGED
    assert "negation or qualification" in graded.rationale
