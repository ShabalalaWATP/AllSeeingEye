"""The processing chain every fetched batch passes through before it reaches the store."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from typing import Protocol

from ase.domain.events import MAX_SUMMARY, MAX_TITLE, Event, content_hash

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE = re.compile(r"\s+")


class PipelineStage(Protocol):
    def process(self, events: list[Event]) -> list[Event]: ...


def clean_text(value: str | None, limit: int) -> str | None:
    """Plain text only: strip control characters, collapse whitespace, bound the length."""
    if value is None:
        return None
    text = unicodedata.normalize("NFC", _CONTROL.sub("", value))
    text = _WHITESPACE.sub(" ", text).strip()
    if not text:
        return None
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


class Normaliser:
    """Bounds every text field, drops items without a usable title and de-duplicates by id."""

    def process(self, events: list[Event]) -> list[Event]:
        seen: set[str] = set()
        result: list[Event] = []
        for event in events:
            title = clean_text(event.title, MAX_TITLE)
            if title is None or event.id in seen:
                continue
            seen.add(event.id)
            summary = clean_text(event.summary, MAX_SUMMARY)
            digest = event.content_hash or content_hash(
                title, summary, event.url, event.published_at.isoformat()
            )
            result.append(event.with_changes(title=title, summary=summary, content_hash=digest))
        return result


class Pipeline:
    def __init__(self, stages: Sequence[PipelineStage]) -> None:
        self._stages = tuple(stages)

    def run(self, events: list[Event]) -> list[Event]:
        for stage in self._stages:
            events = stage.process(events)
        return events
