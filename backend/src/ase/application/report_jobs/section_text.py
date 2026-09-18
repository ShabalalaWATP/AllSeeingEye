"""Bounded accepted section prose, with citation-aware final-context previews."""

from typing import Any

from ase.application.reports.sections.synthesis_contracts import ALTERNATIVES, validate_part
from ase.domain.errors import InvalidRequest
from ase.domain.reports import MAX_ITEM_CHARS, MAX_SECTION_CHARS
from ase.domain.research import ResearchMode


def text(value: Any, limit: int = 2048) -> str:
    if (
        type(value) is not str
        or len(value) > limit
        or any(ord(char) < 32 and char not in "\n\t" for char in value)
    ):
        raise InvalidRequest("The saved report progress is unavailable.")
    return value


def context_preview(body: dict[str, Any]) -> str | None:
    parts = []
    if "sourcing_statement" in body:
        parts.append("Sourcing: " + text(body["sourcing_statement"], MAX_SECTION_CHARS))
    values = body.get("collection_recommendations", [])
    if type(values) is not list or len(values) > 8:
        raise InvalidRequest("The saved report context is unavailable.")
    for value in values:
        parts.append("Collection recommendation: " + text(value, MAX_ITEM_CHARS))
    return "\n\n".join(parts) or None


def alternatives_preview(body: dict[str, Any], labels: Any) -> tuple[str, set[str]]:
    if (
        type(labels) is not list
        or len(labels) > 100
        or any(type(value) is not str for value in labels)
    ):
        raise InvalidRequest("The saved report section citations are unavailable.")
    try:
        # Production already enforced the frozen depth. Progress must accept the
        # structural ceiling of every supported depth, including older snapshots.
        validated = validate_part(
            body,
            part=ALTERNATIVES,
            labels=frozenset(labels),
            eeis=frozenset(),
            research_mode=ResearchMode.ADVANCED,
        )
    except (ValueError, TypeError, RecursionError):
        raise InvalidRequest("The saved report alternatives are unavailable.") from None
    parts: list[str] = []
    citations: set[str] = set()
    for item in validated["alternative_hypotheses"]:
        parts.extend(
            ("Alternative: " + item["text"], "Why less likely: " + item["why_less_likely"])
        )
        citations.update(item["evidence"])
    warning = validated["indicators_and_warning"]
    parts.append("Warning level: " + warning["watch_condition"])
    parts.extend("Watch for: " + value for value in warning["changes"])
    return "\n\n".join(parts), citations
