"""Cheap topic similarity signals, not semantic agreement or truth verification."""

import math
import re
from datetime import timedelta

from ase.domain.events import Category, Event, Point

STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "was",
        "were",
        "will",
        "with",
        "over",
        "after",
        "into",
        "amid",
        "say",
        "says",
        "said",
        "new",
        "more",
        "than",
        "this",
        "their",
        "they",
        "what",
        "when",
        "who",
        "how",
        "why",
        "been",
        "being",
        "also",
        "about",
        "against",
        "between",
        "during",
        "before",
        "under",
        "his",
        "her",
        "but",
        "out",
        "off",
        "all",
        "any",
        "can",
        "now",
        "one",
        "two",
        "amid",
        "via",
        "per",
    ]
)
MIN_TOKEN_LENGTH = 3
STORY_SIMILARITY = 0.4
COPY_SIMILARITY = 0.85
MIN_SHARED_TOKENS = 3
TEXT_WINDOW = timedelta(hours=48)
GEO_WINDOW = timedelta(hours=12)
GEO_RADIUS_KM = 150.0
EARTH_RADIUS_KM = 6371.0
GEO_LINKED_CATEGORIES = frozenset({Category.DISASTER})

_TOKEN = re.compile(r"[a-z0-9]+")


def stem(token: str) -> str:
    """Crude English stemming so "enters", "entered" and "entering" meet as "enter"."""
    if token.endswith("ies") and len(token) >= 5:
        return token[:-3] + "y"
    if token.endswith("ing") and len(token) >= 6:
        return token[:-3]
    if token.endswith("ed") and len(token) >= 5:
        return token[:-2]
    if token.endswith("s") and not token.endswith("ss") and len(token) >= 4:
        return token[:-1]
    return token


def text_tokens(text: str) -> frozenset[str]:
    """English topic tokens, including negation; never claim-equivalence evidence."""
    text = re.sub(r"n['\u2019]t\b", " not", text.lower())
    tokens: set[str] = set()
    for raw in _TOKEN.findall(text):
        if (len(raw) < MIN_TOKEN_LENGTH and raw != "no") or raw in STOPWORDS:
            continue
        word = stem(raw)
        if (len(word) >= MIN_TOKEN_LENGTH or word == "no") and word not in STOPWORDS:
            tokens.add(word)
    return frozenset(tokens)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def distance_km(a: Point, b: Point) -> float:
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlon = math.radians(b.lon - a.lon)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def title_tokens(event: Event) -> frozenset[str]:
    return text_tokens(event.title_en or event.title)
