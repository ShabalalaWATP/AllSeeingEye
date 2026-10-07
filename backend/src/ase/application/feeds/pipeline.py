"""The processing chain every fetched batch passes through before it reaches the store."""

from __future__ import annotations

import asyncio
import re
import unicodedata
from collections.abc import Sequence
from html import unescape
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import urlsplit

from ase.domain.events import MAX_SUMMARY, MAX_TITLE, Event, content_hash

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_CONTROL_OR_LINE = re.compile(r"[\x00-\x1f\x7f]")
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
    if "<" not in value and "&" not in value:
        # Without either character unescape is a no-op and the parser emits the
        # whole value as one data chunk, so its result is exactly the stripped text.
        return value.strip() or None
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
    """Only absolute http(s) links of sane length survive; anything else becomes None.

    Upstream text is untrusted: a malformed authority must never raise into the poll,
    and embedded credentials (`https://trusted@evil.example/`) or control characters
    must never reach a rendered link.
    """
    if value is None:
        return None
    candidate = value.strip()
    if not candidate or len(candidate) > MAX_URL or _CONTROL_OR_LINE.search(candidate):
        return None
    try:
        parts = urlsplit(candidate)
        hostname = parts.hostname
        credentials = parts.username is not None or parts.password is not None
        _ = parts.port  # An out-of-range or non-numeric port raises here.
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not hostname or credentials:
        return None
    return candidate


class Normaliser:
    """Bounds every text field, drops items without a usable title and de-duplicates by id."""

    def process(self, events: list[Event]) -> list[Event]:
        seen: set[str] = set()
        result: list[Event] = []
        for event in events:
            if event.id in seen:
                continue
            try:
                normalised = _normalised(event)
            except (ValueError, TypeError, OverflowError):
                # One malformed upstream record is dropped; the rest of the poll survives.
                continue
            if normalised is None:
                continue
            seen.add(event.id)
            result.append(normalised)
        return result


def _normalised(event: Event) -> Event | None:
    title = clean_text(event.title, MAX_TITLE)
    if title is None:
        return None
    summary = clean_text(event.summary, MAX_SUMMARY)
    url = safe_url(event.url)
    digest = event.content_hash or content_hash(
        title, summary, url, event.published_at.isoformat() if event.published_at else None
    )
    unchanged = (
        title == event.title
        and summary == event.summary
        and url == event.url
        and digest == event.content_hash
    )
    if unchanged:
        return event
    return event.with_changes(title=title, summary=summary, url=url, content_hash=digest)


class Pipeline:
    def __init__(self, stages: Sequence[PipelineStage]) -> None:
        self._stages = tuple(stages)

    def run(self, events: list[Event]) -> list[Event]:
        for stage in self._stages:
            events = stage.process(events)
        return events

    async def run_cooperatively(self, events: list[Event], batch_size: int = 250) -> list[Event]:
        """Yield between bounded batches so large sensor polls do not monopolise the API.

        Stages operate on independent records. Preserve whole-batch normaliser
        semantics by retaining the first surviving occurrence across chunks.
        """
        result: list[Event] = []
        seen: set[str] = set()
        for offset in range(0, len(events), batch_size):
            for event in self.run(events[offset : offset + batch_size]):
                if event.id not in seen:
                    seen.add(event.id)
                    result.append(event)
            await asyncio.sleep(0)
        return result
