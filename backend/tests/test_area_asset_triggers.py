"""Restraint first: the reviewed trigger table must stay silent on ordinary questions.

The negative cases are the point of this file. If a change makes any of them match,
the vocabulary is wrong and must be tightened, never the expectation loosened.
"""

import pytest

from ase.domain.area_assets import (
    ASSET_PHRASES,
    INSTRUMENT_PHRASES,
    MAX_MATCHED_PHRASES,
    AssetClass,
    InstrumentClass,
    TriggerMatch,
    asset_triggers,
    instrument_triggers,
    trigger_text,
)

# Realistic requests that must never pull a register or a spatial instrument into a report.
QUIET = (
    "Assess the outcome of the Dutch general election and the implications for coalition "
    "formation over the next month.",
    "What did the European Central Bank decide at its September meeting, and how did bond "
    "markets react to the decision?",
    "Assess the Akira ransomware campaign described in the latest CISA advisory to critical "
    "infrastructure operators.",
    "Assess the joint diplomatic statement issued after the France and Germany summit.",
    "What is the current measles outbreak situation and the vaccination response?",
    "What happened this week?",
    "Assess the new sanctions designation against a shipping company and its owners.",
    "Summarise the supreme court ruling on data protection and the privacy of user records.",
    "Assess the reported ceasefire and whether either side came under fire afterwards.",
    "Assess email spoofing and phishing against local government mail servers.",
)

LOUD = (
    (
        "Assess the risk to submarine cable connectivity after the reported cable cut.",
        AssetClass.SUBMARINE_CABLES,
    ),
    ("What data centre capacity is present in Ireland?", AssetClass.DATA_CENTRES),
    ("Assess threats to nuclear power stations and reactors.", AssetClass.NUCLEAR_FACILITIES),
    ("Assess the power grid after the blackout and load shedding.", AssetClass.ENERGY_SITES),
    ("Which chip fabs and semiconductor foundries are exposed?", AssetClass.SEMICONDUCTOR_SITES),
    ("Assess satellite ground stations and teleports in the region.", AssetClass.GROUND_STATIONS),
    ("Which traffic cameras and CCTV cover the junction?", AssetClass.CAMERAS),
)


@pytest.mark.parametrize("question", QUIET, ids=range(len(QUIET)))
def test_ordinary_questions_trigger_no_register_and_no_instrument(question):
    assert asset_triggers(question) == ()
    assert instrument_triggers(question) == ()


@pytest.mark.parametrize("question,expected", LOUD, ids=[row[1].value for row in LOUD])
def test_named_asset_classes_are_eligible(question, expected):
    matched = asset_triggers(question)
    assert expected.value in {row.name for row in matched}
    assert all(row.phrases for row in matched)


@pytest.mark.parametrize(
    "question,expected",
    (
        ("Are wildfires burning near the coast?", InstrumentClass.THERMAL_DETECTIONS),
        ("Assess reports of GPS jamming over the Baltic.", InstrumentClass.GNSS_INTERFERENCE),
        (
            "Assess military aircraft flight activity over the Black Sea.",
            InstrumentClass.AIRCRAFT_ACTIVITY,
        ),
        (
            "Assess shadow fleet vessel movements through the strait.",
            InstrumentClass.VESSEL_ACTIVITY,
        ),
    ),
    ids=("thermal", "gnss", "aircraft", "vessels"),
)
def test_instrument_vocabulary_is_narrower_but_still_matches(question, expected):
    assert {row.name for row in instrument_triggers(question)} == {expected.value}
    assert asset_triggers(question) == ()


def test_bare_fire_and_bare_spoofing_are_deliberately_excluded():
    assert instrument_triggers("Troops opened fire during the firefight and the ceasefire") == ()
    assert instrument_triggers("DNS spoofing and certificate spoofing were reported") == ()


def test_bare_aircraft_and_bare_ship_words_are_deliberately_excluded():
    """An aircraft crash or a ship's sanctioning is not a request to sweep the trackers."""
    assert instrument_triggers("A passenger aircraft crashed shortly after take-off") == ()
    assert instrument_triggers("The ship and its owner were named in the designation") == ()
    assert instrument_triggers("Flight MH17 and the airline's fleet were discussed") == ()


def test_matched_phrases_are_deduplicated_and_bounded():
    text = " ".join(["submarine cable"] * 20 + list(ASSET_PHRASES[AssetClass.ENERGY_SITES]))
    matched = {row.name: row for row in asset_triggers(text)}
    assert matched[AssetClass.SUBMARINE_CABLES.value].phrases == ("submarine cable",)
    assert len(matched[AssetClass.ENERGY_SITES.value].phrases) == MAX_MATCHED_PHRASES


def test_trigger_text_joins_only_present_parts_and_is_bounded():
    assert trigger_text("question", None, "terms") == "question terms"
    assert len(trigger_text("x" * 20_000)) == 8_000


def test_trigger_match_requires_a_class_and_bounded_phrases():
    with pytest.raises(ValueError):
        TriggerMatch("", ("cable",))
    with pytest.raises(ValueError):
        TriggerMatch("cables", ())
    with pytest.raises(ValueError):
        TriggerMatch("cables", tuple(str(index) for index in range(MAX_MATCHED_PHRASES + 1)))
    assert TriggerMatch("cables", ("cable cut",)).describe() == "cables (cable cut)"


def test_every_reviewed_class_has_phrases_and_no_phrase_is_shared_between_classes():
    seen: dict[str, str] = {}
    for table in (ASSET_PHRASES, INSTRUMENT_PHRASES):
        for key, phrases in table.items():
            assert phrases and len(set(phrases)) == len(phrases)
            for phrase in phrases:
                assert phrase == phrase.casefold() and phrase.strip() == phrase
                assert phrase not in seen, (phrase, key, seen.get(phrase))
                seen[phrase] = key.value
    assert set(ASSET_PHRASES) == set(AssetClass)
    assert set(INSTRUMENT_PHRASES) == set(InstrumentClass)
