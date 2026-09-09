"""Relevance admission is separate from source reliability and information credibility."""

from ase.domain.events import Category, Event

INCIDENT_RELEVANCE = frozenset({"armed_conflict", "civil_unrest", "military_activity"})


def needs_conflict_review(event: Event) -> bool:
    return event.source_id == "gdelt_events" or "machine_coded" in event.tags


def screened_relevance(event: Event) -> str | None:
    if event.attributes.get("conflict_screening") != "llm":
        return None
    value = event.attributes.get("conflict_relevance")
    return value if isinstance(value, str) else None


def is_admitted_conflict(event: Event) -> bool:
    if event.category is not Category.CONFLICT:
        return False
    relevance = screened_relevance(event)
    if relevance is not None:
        return relevance in INCIDENT_RELEVANCE
    # CAMEO coercion includes ordinary legal proceedings. Even a violence code is
    # only a candidate until actual source text has been assessed for relevance.
    return not needs_conflict_review(event)
