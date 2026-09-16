"""Nothing is stored or shown until every figure, year and phrase survives the checks."""

from __future__ import annotations

import json

import pytest

from ase.application.economy_explainer_facts import build_fact_pack
from ase.application.economy_explainer_model import parse_explainer
from ase.application.economy_explainer_validation import allowed_numbers, validate_explainer
from economy_explainer_helpers import content, headline, payload, snapshot


def facts():
    return build_fact_pack(snapshot(), (headline(),))


def checked(**overrides):
    return validate_explainer(parse_explainer(content(**overrides)), facts())


def world(**changes):
    section = dict(payload()["world"])  # type: ignore[arg-type]
    section.update(changes)
    return {"world": section}


def test_a_faithful_summary_passes_every_check():
    assert checked() == []


def test_an_invented_figure_is_rejected():
    problems = checked(
        **world(paragraphs=["Growth reached 7.7% in 2024.", "Prices rose by 3% in 2024."])
    )
    assert problems == ["the figure 7.7 does not match any supplied figure"]


def test_a_figure_within_rounding_of_a_supplied_one_is_accepted():
    rounded = ["Growth was 2% in 2024.", "Prices rose by 3% in 2024."]
    assert checked(**world(paragraphs=rounded)) == []


def test_a_year_that_is_not_in_the_data_is_rejected():
    problems = checked(
        **world(paragraphs=["Growth reached 2.4% in 2019.", "Prices rose by 3% in 2024."])
    )
    assert problems == ["the year 2019 is not present in the supplied data"]


def test_links_markup_and_long_dashes_are_rejected():
    problems = checked(
        **world(
            paragraphs=[
                "Read more at https://example.invalid/story.",
                "Prices <b>rose</b> by 3% in 2024" + chr(0x2014) + "sharply.",
            ]
        )
    )
    assert "a web address or link appears in the text; remove it" in problems
    assert "angle brackets or HTML entities appear in the text; use plain words" in problems
    assert any("em dash" in problem for problem in problems)


def test_jargon_must_be_explained_in_the_same_sentence():
    unexplained = checked(
        **world(
            paragraphs=[
                "The current account weakened in 2024.",
                "Prices rose by 3% in 2024.",
            ]
        )
    )
    assert any("current account" in problem for problem in unexplained)
    explained = checked(
        **world(
            paragraphs=[
                "The current account, which is the money a country earns from abroad minus "
                "what it spends abroad, weakened in 2024.",
                "Prices rose by 3% in 2024.",
            ]
        )
    )
    assert explained == []


def test_the_written_counts_and_lengths_are_bounded():
    problems = checked(**world(paragraphs=["Prices rose by 3% in 2024."]))
    assert "WORLD needs between 2 and 3 paragraphs" in problems


def test_an_unknown_region_key_is_refused_before_anything_is_stored():
    body = payload()
    body["regions"]["XX"] = body["regions"]["GB"]  # type: ignore[index]
    with pytest.raises(ValueError, match="not the known regions"):
        parse_explainer(json.dumps(body))


def test_a_missing_region_section_is_reported():
    body = payload()
    del body["regions"]["IR"]  # type: ignore[attr-defined]
    problems = validate_explainer(parse_explainer(json.dumps(body)), facts())
    assert problems == ["the IR section is missing"]


def test_counts_and_large_figures_may_be_quoted_at_a_readable_scale():
    allowed = allowed_numbers(facts())
    # Two indicators carry data and one does not, so both counts may be written.
    assert 2.0 in allowed and 1.0 in allowed
    # A large value may be written in billions rather than in full.
    assert 0.0024 in allowed
