"""Small allowlisted map-source projections and bounded lexical relevance."""

import re
from collections.abc import Iterable
from urllib.parse import parse_qs, urlsplit

from ase.domain.assistant import AssistantSource
from ase.domain.country_subject_aliases import COUNTRY_SUBJECT_ALIASES
from ase.domain.events import Event
from ase.domain.evidence import injection_flags
from ase.domain.traffic_classification import is_reported_military
from ase.domain.web_research import public_web_url

STOP_WORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "by",
        "can",
        "could",
        "current",
        "currently",
        "describe",
        "did",
        "do",
        "does",
        "for",
        "from",
        "give",
        "has",
        "have",
        "how",
        "i",
        "in",
        "information",
        "is",
        "it",
        "latest",
        "me",
        "more",
        "my",
        "near",
        "now",
        "of",
        "on",
        "or",
        "please",
        "recent",
        "show",
        "some",
        "tell",
        "that",
        "the",
        "their",
        "them",
        "there",
        "these",
        "this",
        "to",
        "us",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "would",
        "you",
        "about",
        "around",
        "happening",
        "happen",
        "going",
        "area",
        "map",
        "globe",
        "view",
        "selected",
        "item",
        "explain",
        "situation",
        "overview",
        "summarise",
        "summary",
        "all",
        "any",
        "many",
        "much",
        "count",
        "counts",
        "list",
        "details",
        "detail",
        "activity",
        "activities",
        "observations",
        "observation",
        "observed",
        "available",
        "retained",
        "sources",
        "source",
        "records",
        "record",
        "data",
        "dataset",
        "datasets",
        "brief",
        "briefly",
        "concise",
        "one",
        "two",
        "three",
        "four",
        "five",
        "limitation",
        "limitations",
        "provide",
        "using",
        "use",
        "based",
        "findings",
        "finding",
        "insight",
        "insights",
        "significant",
        "significance",
        "important",
        "importance",
        "risk",
        "risks",
        "impact",
        "impacts",
        "likely",
        "possible",
        "potential",
        "dangerous",
        "danger",
        "severe",
        "powerful",
        "compared",
        "compare",
        "information",
        "overview",
        "most",
        "useful",
        "coverage",
        "gaps",
        "gap",
    ]
)
TERM_ALIASES = {
    "planes": "aviation",
    "plane": "aviation",
    "flights": "aviation",
    "flight": "aviation",
    "aircraft": "aviation",
    "ships": "maritime",
    "ship": "maritime",
    "boats": "maritime",
    "boat": "maritime",
    "vessels": "maritime",
    "vessel": "maritime",
    "satellites": "space",
    "satellite": "space",
    "fires": "fire",
    "earthquakes": "earthquake",
    "conflicts": "conflict",
    "cameras": "camera",
    "cctv": "camera",
    "cables": "cable",
    "stations": "station",
    "strongest": "magnitude",
    "strength": "magnitude",
}
SAFE_ATTRIBUTES = (
    "military_public_catalogue",
    "affiliation_basis",
    "callsign",
    "registration",
    "icao24",
    "altitude_ft",
    "altitude_m",
    "speed_kt",
    "heading",
    "mmsi",
    "imo",
    "vessel_type",
    "ship_type",
    "ship_type_code",
    "flag_country",
    "military",
    "military_source",
    "orbit",
    "orbit_class",
    "norad_id",
    "magnitude",
    "depth_km",
    "hazard",
    "status",
    "position_kind",
    "is_stale",
    "epoch",
    "element_epoch",
    "propagated_at",
    "age_days",
)


def query_terms(question: str, *, limit: int | None = 24) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            TERM_ALIASES.get(term, term)
            for term in re.findall(r"[\w'-]{2,}", question.casefold())
            if term not in STOP_WORDS
        )
    )[:limit]


def safe_source_url(value: str | None) -> str | None:
    if value is None or not public_web_url(value):
        return None
    sensitive = {"key", "token", "api_key", "apikey", "access_token", "signature", "sig", "auth"}
    return (
        None
        if sensitive.intersection(key.lower() for key in parse_qs(urlsplit(value).query))
        else value
    )


def event_source(event: Event) -> AssistantSource | None:
    details = (
        f"Source ID: {event.source_id}; source words: {event.source_id.replace('_', ' ')}.",
        f"Category: {event.category.value}; subtype: {event.subtype}.",
        f"Incident country: {event.country_iso or 'unknown'} "
        f"({COUNTRY_SUBJECT_ALIASES.get(event.country_iso or '', ('unknown',))[0]}); "
        f"geography: {event.geo_confidence.value}.",
        "Source grade is not a probability or independent corroboration.",
        "Reported military traffic classification from provider metadata; affiliation unverified."
        if is_reported_military(event)
        else "",
        "Public military satellite catalogue classification; affiliation is unverified."
        if event.attributes.get("military_public_catalogue") is True
        else "",
        *(
            f"{key}: {str(event.attributes[key])[:100]}"
            for key in SAFE_ATTRIBUTES
            if key in event.attributes
        ),
    )
    if injection_flags(event.title, event.summary, *details):
        return None
    return AssistantSource(
        "",
        "event",
        event.id,
        event.source_id,
        event.title[:300],
        safe_source_url(event.url),
        event.published_at,
        event.observed_at,
        event.point,
        event.grade,
        (event.summary or "")[:600],
        (*details[:18], f"Grading rationale: {event.grade_rationale[:300]}"),
        event.country_iso,
        str(event.attributes.get("original_publisher", ""))[:200] or None,
    )


def relevance(source: AssistantSource, terms: tuple[str, ...]) -> int:
    text = " ".join((source.title, source.summary, *source.details)).casefold()
    return sum(bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text)) for term in terms)


def source_text_size(source: AssistantSource) -> int:
    return sum(map(len, (source.title, source.summary, *source.details)))


def unique_sources(rows: Iterable[AssistantSource]) -> list[AssistantSource]:
    return list({(row.kind, row.record_id): row for row in rows}.values())
