"""Explainer prose length limits protect callers beyond the JSON parser."""

from dataclasses import replace

import pytest

from ase.application.economy_explainer_model import parse_explainer
from ase.application.economy_explainer_validation import validate_explainer
from economy_explainer_helpers import content
from test_economy_explainer_validation import facts


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("takeaway", "x" * 1000, "takeaway is longer"),
        ("paragraphs", ("x" * 3000, "Context."), "paragraph is longer"),
        ("drivers", (), "drivers needs"),
        ("watch", ("x" * 1000,), "watch entry is longer"),
    ],
)
def test_section_length_and_entry_limits_are_enforced(field, value, reason):
    text = parse_explainer(content())
    text = replace(text, world=replace(text.world, **{field: value}))
    assert any(reason in error for error in validate_explainer(text, facts()))


def test_glossary_count_and_term_limits_are_enforced():
    text = parse_explainer(content())
    missing = replace(text, glossary=())
    assert any("glossary needs" in error for error in validate_explainer(missing, facts()))
    oversized = replace(text, glossary=(replace(text.glossary[0], term="x" * 1000),))
    assert any("glossary entry" in error for error in validate_explainer(oversized, facts()))
