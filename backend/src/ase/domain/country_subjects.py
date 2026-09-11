"""Bounded country subjects supported by original source text, never geolocation."""

import json
import re
from bisect import bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from functools import lru_cache
from itertools import accumulate
from typing import Literal

from ase.domain.country_subject_aliases import COUNTRY_SUBJECT_ALIASES, COUNTRY_SUBJECT_EXCLUSIONS
from ase.domain.events import (
    MAX_ATTRIBUTES,
    MAX_SUMMARY,
    MAX_TITLE,
    Event,
    GeoConfidence,
    JsonScalar,
    freeze_attributes,
)
from ase.domain.research_scope import normalise_countries

SUBJECT_POLICY_KEY = "country_subject_policy"
SUBJECT_POLICY = "ase-original-rss-country-subject-v1"
SUBJECT_NOTICE_KEY = "country_subject_notice"
SUBJECT_PREFIX = "country_subject_"
SUBJECT_NOTICE = (
    "Country mentioned in original source text. Subject relevance only; incident geography "
    "is unverified. Not a location, nationality, identity or independent corroboration."
)
RSS_SOURCE_PREFIXES = ("research_google_news_", "research_publisher_", "research_regional_")


@dataclass(frozen=True, slots=True)
class CountrySubjectMatch:
    country_iso: str
    field: Literal["title", "summary"]
    start: int
    end: int
    text: str

    def encoded(self) -> str:
        return json.dumps([self.field, self.start, self.end, self.text], ensure_ascii=False)


@lru_cache(maxsize=512)
def _pattern(alias: str) -> re.Pattern[str]:
    # CJK country names are not normally separated by spaces. Longer distinct
    # names such as Belarus are excluded independently below.
    cjk = all("\u3400" <= character <= "\u9fff" for character in alias)
    expression = re.escape(alias) if cjk else rf"(?<!\w){re.escape(alias)}(?!\w)"
    return re.compile(expression, re.IGNORECASE)


def source_text_country_matches(
    title: str,
    summary: str | None,
    countries: Sequence[str],
    *,
    ignored_phrases: tuple[str, ...] = (),
) -> tuple[CountrySubjectMatch, ...]:
    """First exact original-text span per selected country, title before summary."""
    selected = normalise_countries(None, tuple(countries))
    matches: list[CountrySubjectMatch] = []
    fields: tuple[tuple[Literal["title", "summary"], str], ...] = (
        ("title", title[:MAX_TITLE]),
        ("summary", (summary or "")[:MAX_SUMMARY]),
    )
    for country in selected:
        for field, text in fields:
            excluded = sorted(
                match.span()
                for alias in (*COUNTRY_SUBJECT_EXCLUSIONS.get(country, ()), *ignored_phrases[:3])
                if 2 <= len(alias) <= 200
                for match in _pattern(alias).finditer(text)
            )
            starts = tuple(start for start, _ in excluded)
            # A prefix maximum supports overlapping and nested attribution spans.
            # Each candidate needs one binary search, not a scan of every span.
            furthest_ends = tuple(accumulate((end for _, end in excluded), max))
            candidates = [
                match
                for alias in COUNTRY_SUBJECT_ALIASES.get(country, ())
                for match in _pattern(alias).finditer(text)
                if (index := bisect_right(starts, match.start()) - 1) < 0
                or furthest_ends[index] < match.end()
            ]
            if candidates:
                match = min(candidates, key=lambda row: (row.start(), -len(row.group())))
                matches.append(CountrySubjectMatch(country, field, *match.span(), match.group()))
                break
    return tuple(matches)


def eligible_source_text(event: Event) -> bool:
    return (
        event.source_id.startswith(RSS_SOURCE_PREFIXES)
        and event.country_iso is None
        and event.point is None
        and event.geometry is None
        and event.observation is None
        and event.project is None
        and event.geo_confidence is GeoConfidence.NONE
        and not event.transformations
    )


def annotate_fresh_country_subject(event: Event, countries: Sequence[str]) -> Event:
    """Called only for fresh public RSS batch items entering the private report pool."""
    if not eligible_source_text(event):
        return event
    matches = source_text_country_matches(
        event.title, event.summary, countries, ignored_phrases=_publisher_phrases(event.attributes)
    )
    if not matches:
        return event
    hints: dict[str, JsonScalar] = {
        SUBJECT_POLICY_KEY: SUBJECT_POLICY,
        SUBJECT_NOTICE_KEY: SUBJECT_NOTICE,
        **{SUBJECT_PREFIX + match.country_iso: match.encoded() for match in matches},
    }
    # Never evict original source metadata to make room for a retrieval hint.
    if len(set(event.attributes) | set(hints)) > MAX_ATTRIBUTES:
        return event
    return replace(event, attributes=freeze_attributes({**event.attributes, **hints}))


def supported_subject_matches(
    title: str,
    summary: str | None,
    attributes: Mapping[str, JsonScalar],
    countries: Sequence[str],
) -> tuple[CountrySubjectMatch, ...]:
    """Recheck exact source spans rather than trusting stored country codes or notices."""
    if attributes.get(SUBJECT_POLICY_KEY) != SUBJECT_POLICY:
        return ()
    if attributes.get(SUBJECT_NOTICE_KEY) != SUBJECT_NOTICE:
        return ()
    return tuple(
        match
        for match in source_text_country_matches(
            title, summary, countries, ignored_phrases=_publisher_phrases(attributes)
        )
        if attributes.get(SUBJECT_PREFIX + match.country_iso) == match.encoded()
    )


def matches_country_subject(event: Event, countries: Sequence[str]) -> bool:
    return eligible_source_text(event) and bool(
        supported_subject_matches(event.title, event.summary, event.attributes, countries)
    )


def _publisher_phrases(attributes: Mapping[str, JsonScalar]) -> tuple[str, ...]:
    return tuple(
        value
        for key in ("original_publisher", "original_source_organisation", "collection_feed")
        if isinstance(value := attributes.get(key), str) and 2 <= len(value) <= 200
    )


def country_subject_lines(
    title: str, summary: str | None, attributes: Mapping[str, JsonScalar]
) -> tuple[str, ...]:
    countries = tuple(
        key.removeprefix(SUBJECT_PREFIX)
        for key in attributes
        if key.startswith(SUBJECT_PREFIX) and len(key) == len(SUBJECT_PREFIX) + 2
    )
    try:
        matches = supported_subject_matches(title, summary, attributes, countries)
    except ValueError:
        return ()
    if not matches:
        return ()
    return (
        SUBJECT_NOTICE,
        *(
            f"Country subject {row.country_iso}: original {row.field}[{row.start}:{row.end}] "
            f"contains {row.text!r}; method {SUBJECT_POLICY}."
            for row in matches
        ),
    )
