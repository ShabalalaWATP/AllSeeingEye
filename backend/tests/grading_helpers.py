"""Synthetic source registry and headlines for grading regression tests."""

from datetime import timedelta

from ase.domain.events import Category, Event
from ase.domain.grading import SourceProfile
from feeds_helpers import NOW, make_event

PROFILES = {
    "bbc": SourceProfile("bbc", "BBC", "BBC News World"),
    "bbc_arabic": SourceProfile("bbc_arabic", "BBC", "BBC Arabic"),
    "aljazeera": SourceProfile("aljazeera", "Al Jazeera", "Al Jazeera English"),
    "reuters_via_guardian": SourceProfile("reuters_via_guardian", "Guardian", "The Guardian"),
    "tass": SourceProfile("tass", "TASS", "TASS English", flags=frozenset({"state_controlled"})),
    "usgs": SourceProfile("usgs", "USGS", "USGS earthquakes", instrument=True),
    "gdacs": SourceProfile("gdacs", "JRC", "GDACS", instrument=True),
    "kev": SourceProfile("kev", "CISA", "CISA KEV", flags=frozenset({"authoritative"})),
}


def news(
    key: str, source: str, title: str, *, minutes: int = 0, country: str | None = "SD"
) -> Event:
    return make_event(
        key,
        source_id=source,
        category=Category.NEWS,
        subtype="article",
        title=title,
        published_at=NOW + timedelta(minutes=minutes),
        point=None,
        country_iso=country,
    )
