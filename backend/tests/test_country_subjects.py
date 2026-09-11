"""Country subjects require exact source-text support, never a query or inferred location."""

from dataclasses import replace

import pytest

import ase.domain.country_subjects as subjects
from ase.domain.country_subjects import (
    SUBJECT_NOTICE,
    SUBJECT_NOTICE_KEY,
    SUBJECT_POLICY,
    SUBJECT_POLICY_KEY,
    annotate_fresh_country_subject,
    country_subject_lines,
    matches_country_subject,
    source_text_country_matches,
)
from ase.domain.events import MAX_ATTRIBUTES, GeoConfidence, Point, freeze_attributes
from test_research_collection import event


def headline(title="Ukraine and Russia hold talks", **changes):
    return replace(
        event("story"),
        title=title,
        source_id="research_google_news_en",
        content_hash="unchanged-source-hash",
        **changes,
    )


@pytest.mark.parametrize(
    ("title", "countries", "expected"),
    [
        ("Ukraine and Russia hold talks", ("UA", "RU"), ("Ukraine", "Russia")),
        ("Talks about России and України", ("RU", "UA"), ("России", "України")),
        ("乌克兰与俄罗斯举行会谈", ("UA", "RU"), ("乌克兰", "俄罗斯")),
        ("United States and India publish figures", ("US", "IN"), ("United States", "India")),
        ("People's Republic of China statement", ("CN",), ("People's Republic of China",)),
    ],
)
def test_explicit_original_country_names_have_exact_offsets(title, countries, expected):
    matches = source_text_country_matches(title, None, countries)
    assert tuple(match.text for match in matches) == expected
    assert all(title[match.start : match.end] == match.text for match in matches)


@pytest.mark.parametrize(
    ("title", "countries"),
    [
        ("Georgia meets Jordan while Chad cooks turkey", ("GE", "JO", "TD", "TR")),
        ("They told us in the briefing", ("US", "IN")),
        ("US, RU and UA update; a Russian spokesperson responds", ("US", "RU", "UA")),
        ("Nigeria announces new projects", ("NE",)),
        ("South Sudan signs agreement", ("SD",)),
        ("Northern Ireland vote", ("IE",)),
        ("Democratic Republic of the Congo election", ("CG",)),
        ("Democratic People's Republic of Korea delegation", ("KR",)),
        ("Republic of China statement", ("CN",)),
        ("白俄罗斯举行会谈", ("RU",)),
        ("American Samoa travel updates", ("WS",)),
    ],
)
def test_ambiguous_names_abbreviations_and_longer_distinct_places_are_excluded(title, countries):
    assert not source_text_country_matches(title, None, countries)


def test_country_can_be_subject_of_original_summary_without_becoming_incident_location():
    original = headline("Peace negotiations", summary="Delegations from Ukraine and Russia met.")
    annotated = annotate_fresh_country_subject(original, ("UA", "RU"))
    assert annotated.country_iso is annotated.point is annotated.geometry is None
    assert annotated.geo_confidence is GeoConfidence.NONE
    assert replace(annotated, attributes=original.attributes) == original
    assert annotated.attributes[SUBJECT_NOTICE_KEY] == SUBJECT_NOTICE
    assert annotated.attributes[SUBJECT_POLICY_KEY] == SUBJECT_POLICY
    assert matches_country_subject(annotated, ("UA",))
    assert "summary" in annotated.attributes["country_subject_UA"]
    assert "incident geography is unverified" in " ".join(
        country_subject_lines(
            annotated.title,
            annotated.summary,
            annotated.attributes,
        )
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"country_iso": "US"},
        {"point": Point(-77, 38)},
        {"geo_confidence": GeoConfidence.COUNTRY},
        {"source_id": "research-web-search"},
        {"source_id": "research-upload"},
        {"source_id": "live-news"},
    ],
)
def test_explicit_geography_and_non_rss_origins_cannot_gain_subject_admission(changes):
    original = replace(headline(), **changes)
    assert annotate_fresh_country_subject(original, ("UA", "RU")) == original
    assert not matches_country_subject(original, ("UA", "RU"))


def test_query_translations_publisher_origin_and_unrelated_titles_are_not_country_evidence():
    original = headline(
        "Local railway disruption",
        title_en="Ukraine railway disruption",
        attributes=freeze_attributes({"original_publisher": "Russia Today"}),
    )
    assert annotate_fresh_country_subject(original, ("UA", "RU")) == original
    suffix = replace(original, title="Local railway disruption - Russia Today")
    assert annotate_fresh_country_subject(suffix, ("RU",)) == suffix
    actual = replace(original, title="Russia responds to Ukraine - Russia Today")
    assert matches_country_subject(annotate_fresh_country_subject(actual, ("RU",)), ("RU",))


def test_stale_or_forged_match_spans_fail_closed():
    annotated = annotate_fresh_country_subject(headline(), ("UA", "RU"))
    assert not matches_country_subject(replace(annotated, title="Unrelated football news"), ("UA",))
    attributes = {**annotated.attributes, "country_subject_UA": '["title", 99, 106, "Ukraine"]'}
    forged = replace(annotated, attributes=freeze_attributes(attributes))
    assert not matches_country_subject(forged, ("UA",))
    missing_notice = replace(
        annotated, attributes=freeze_attributes({SUBJECT_POLICY_KEY: SUBJECT_POLICY})
    )
    assert not matches_country_subject(missing_notice, ("UA",))
    assert not country_subject_lines("Ukraine", None, {"country_subject_ZZ": "forged"})
    assert not country_subject_lines(
        "Ukraine",
        None,
        {
            SUBJECT_POLICY_KEY: SUBJECT_POLICY,
            SUBJECT_NOTICE_KEY: SUBJECT_NOTICE,
            "country_subject_ZZ": "forged",
        },
    )


def test_original_metadata_is_not_evicted_to_fit_match_hints():
    original = headline(attributes=freeze_attributes({str(i): i for i in range(MAX_ATTRIBUTES)}))
    assert annotate_fresh_country_subject(original, ("UA", "RU")) == original


def test_repeated_exclusions_use_one_bounded_lookup_per_candidate(monkeypatch):
    searches = []
    original = subjects.bisect_right

    def counted(starts, value):
        searches.append(len(starts))
        return original(starts, value)

    monkeypatch.setattr(subjects, "bisect_right", counted)
    assert not source_text_country_matches("", "白俄罗斯" * 500, ("RU",))
    assert len(searches) == 500 and max(searches) == 500
    assert (
        source_text_country_matches("", "白俄罗斯" * 490 + " 俄罗斯", ("RU",))[0].text == "俄罗斯"
    )


def test_nested_publisher_exclusions_and_longer_country_aliases_keep_exact_spans():
    assert not source_text_country_matches(
        "Ukraine Russia", None, ("RU",), ignored_phrases=("Ukraine Russia", "Ukraine")
    )
    assert (
        source_text_country_matches("People's Republic of China", None, ("CN",))[0].text
        == "People's Republic of China"
    )
