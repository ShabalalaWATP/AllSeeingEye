"""The processing chain every fetched batch passes through before it reaches the store."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from html import unescape
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import urlsplit

from ase.domain.events import MAX_SUMMARY, MAX_TITLE, Event, content_hash

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE = re.compile(r"\s+")
MAX_URL = 2_048


class PipelineStage(Protocol):
    def process(self, events: list[Event]) -> list[Event]: ...


class _TextExtractor(HTMLParser):
    """Collects the text of an HTML fragment; tags and attributes are discarded."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def strip_html(value: str | None) -> str | None:
    """Plain text from a body that may hold literal or entity-escaped HTML."""
    if not value:
        return None
    extractor = _TextExtractor()
    extractor.feed(unescape(value))
    extractor.close()
    text = " ".join(extractor.parts)
    return text or None


def clean_text(value: str | None, limit: int) -> str | None:
    """Plain text only: strip markup and control characters, collapse whitespace, bound."""
    if value is None:
        return None
    text = strip_html(value) or ""
    text = unicodedata.normalize("NFC", _CONTROL.sub("", text))
    text = _WHITESPACE.sub(" ", text).strip()
    if not text:
        return None
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def safe_url(value: str | None) -> str | None:
    """Only absolute http(s) links of sane length survive; anything else becomes None."""
    if value is None:
        return None
    candidate = value.strip()
    if not candidate or len(candidate) > MAX_URL:
        return None
    parts = urlsplit(candidate)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    return candidate


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
            url = safe_url(event.url)
            digest = event.content_hash or content_hash(
                title, summary, url, event.published_at.isoformat()
            )
            result.append(
                event.with_changes(title=title, summary=summary, url=url, content_hash=digest)
            )
        return result


class Pipeline:
    def __init__(self, stages: Sequence[PipelineStage]) -> None:
        self._stages = tuple(stages)

    def run(self, events: list[Event]) -> list[Event]:
        for stage in self._stages:
            events = stage.process(events)
        return events
