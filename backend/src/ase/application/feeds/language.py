"""Pipeline stage that fills in an event's language when the feed could not say."""

from __future__ import annotations

from dataclasses import replace

from ase.application.ports.language import LanguageDetector
from ase.domain.events import Event

UNKNOWN = frozenset({"", "und", "mul", "unknown"})


class LanguageStage:
    """Detects the language of untagged titles; tagged events pass through untouched."""

    def __init__(self, detector: LanguageDetector) -> None:
        self._detector = detector

    def process(self, events: list[Event]) -> list[Event]:
        out: list[Event] = []
        for event in events:
            if event.language.lower() not in UNKNOWN:
                out.append(event)
                continue
            sample = (
                event.title if len(event.title) >= 24 else f"{event.title} {event.summary or ''}"
            )
            detected = self._detector.detect(sample)
            out.append(replace(event, language=detected or "und"))
        return out
