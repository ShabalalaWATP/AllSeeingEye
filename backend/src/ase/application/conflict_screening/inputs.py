"""Exact source-URL joins, never generated CAMEO prose or inferred article bodies."""

from dataclasses import dataclass

from ase.application.conflict_screening.records import ScreeningInput
from ase.domain.conflict_evidence import canonical_report_url, is_conflict_context
from ase.domain.conflict_relevance import needs_conflict_review
from ase.domain.events import Category, Event, content_hash

TEXT_CATEGORIES = frozenset({Category.NEWS, Category.POLITICAL, Category.HUMANITARIAN})


@dataclass(frozen=True)
class Candidate:
    target: Event
    source: Event
    text: ScreeningInput


def source_text(event: Event) -> ScreeningInput:
    title, summary = event.title[:300], (event.summary or "")[:1000]
    return ScreeningInput(content_hash(title, summary), title, summary)


def candidates(events: list[Event]) -> list[Candidate]:
    texts: dict[str, Event] = {}
    for event in events:
        url = canonical_report_url(event.url)
        if (
            url
            and event.category in TEXT_CATEGORIES
            and not needs_conflict_review(event)
            and isinstance(event.attributes.get("outlet"), str)
        ):
            texts.setdefault(url, event)
    result: list[Candidate] = []
    for event in events:
        url = canonical_report_url(event.url)
        source = texts.get(url or "")
        if source is None:
            continue
        if (
            needs_conflict_review(event)
            or is_conflict_context(event)
            or event.attributes.get("conflict_screening") == "llm"
        ):
            result.append(Candidate(event, source, source_text(source)))
    return result
