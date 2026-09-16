"""What each product template's report must contain, as data an operator can read.

These rows say which parts of the body a template requires, which headings its
sections ask for and in what order, how many key judgements it expects and how long
the finished prose should be. They describe the template, so changing a template's
sections means changing its row here. Nothing here rewrites a report.
"""

from __future__ import annotations

from dataclasses import dataclass

PART_LABELS: dict[str, str] = {
    "key_judgements": "key judgements",
    "reporting": "reporting",
    "assessment": "an assessment section",
    "assumptions": "stated assumptions",
    "alternative_hypotheses": "at least one alternative hypothesis",
    "gaps": "a gaps section",
    "collection_recommendations": "collection recommendations",
    "sourcing_statement": "a sourcing statement",
    "indicators_and_warning": "indicators and warning",
}


@dataclass(frozen=True, slots=True)
class ExpectedHeading:
    """A heading the template asks for; ``key`` is matched inside the written heading."""

    key: str
    label: str


@dataclass(frozen=True, slots=True)
class TemplateStructure:
    required_parts: tuple[str, ...]
    expected_headings: tuple[ExpectedHeading, ...] = ()
    min_judgements: int = 1
    max_judgements: int = 5
    min_chars: int = 600
    max_chars: int = 24_000


_COMMON = ("key_judgements", "reporting", "sourcing_statement")

TEMPLATE_STRUCTURES: dict[str, TemplateStructure] = {
    "intsum": TemplateStructure(
        required_parts=(
            *_COMMON,
            "assessment",
            "indicators_and_warning",
            "gaps",
            "collection_recommendations",
        ),
        min_judgements=3,
        max_judgements=5,
        max_chars=24_000,
    ),
    "intrep": TemplateStructure(
        required_parts=(*_COMMON, "gaps"),
        min_judgements=1,
        max_judgements=3,
        min_chars=400,
        max_chars=16_000,
    ),
    "country_brief": TemplateStructure(
        required_parts=(
            *_COMMON,
            "indicators_and_warning",
            "gaps",
            "collection_recommendations",
        ),
        min_judgements=1,
        max_judgements=6,
        max_chars=24_000,
    ),
    "ask": TemplateStructure(
        required_parts=(
            *_COMMON,
            "assessment",
            "assumptions",
            "alternative_hypotheses",
            "gaps",
        ),
        min_judgements=1,
        max_judgements=5,
        max_chars=24_000,
    ),
    "disaster_sitrep": TemplateStructure(
        required_parts=(*_COMMON, "gaps"),
        expected_headings=(
            ExpectedHeading("event fact", "Event facts"),
            ExpectedHeading("impact", "Impact and exposure"),
            ExpectedHeading("response", "Response"),
        ),
        min_judgements=1,
        max_judgements=3,
        max_chars=20_000,
    ),
    "conflict_assessment": TemplateStructure(
        required_parts=(
            *_COMMON,
            "indicators_and_warning",
            "gaps",
            "collection_recommendations",
        ),
        expected_headings=(
            ExpectedHeading("belligerent", "Belligerents and objectives"),
            ExpectedHeading("activity", "Recent activity"),
            ExpectedHeading("humanitarian", "Humanitarian picture"),
        ),
        min_judgements=2,
        max_judgements=5,
        max_chars=28_000,
    ),
    "aviation_activity": TemplateStructure(
        required_parts=(*_COMMON, "gaps"),
        expected_headings=(
            ExpectedHeading("flight", "Notable military and interesting flights"),
            ExpectedHeading("baseline", "Patterns against baseline"),
            ExpectedHeading("gnss", "GNSS interference"),
            ExpectedHeading("emergenc", "Emergencies"),
        ),
        min_judgements=1,
        max_judgements=3,
        max_chars=20_000,
    ),
    "maritime_activity": TemplateStructure(
        required_parts=(*_COMMON, "gaps"),
        expected_headings=(
            ExpectedHeading("warning", "Warnings by region"),
            ExpectedHeading("exercise", "Exercises and closures"),
            ExpectedHeading("incident", "Security incidents"),
            ExpectedHeading("gnss", "GNSS interference notices"),
        ),
        min_judgements=1,
        max_judgements=3,
        max_chars=20_000,
    ),
    "cyber_summary": TemplateStructure(
        required_parts=(*_COMMON, "gaps"),
        expected_headings=(
            ExpectedHeading("vulnerabilit", "New known exploited vulnerabilities"),
            ExpectedHeading("ransomware", "Ransomware activity"),
            ExpectedHeading("outage", "Outages and shutdowns"),
        ),
        min_judgements=1,
        max_judgements=3,
        max_chars=20_000,
    ),
}

DEFAULT_STRUCTURE = TemplateStructure(required_parts=_COMMON)


def structure_for(template_id: str) -> TemplateStructure:
    """An unknown template keeps the minimum shared shape rather than failing."""
    return TEMPLATE_STRUCTURES.get(template_id, DEFAULT_STRUCTURE)
