"""The vocabulary the doctrine allows and the words it forbids, as matchers over text.

Probability uses the PHIA yardstick only (docs/03 section 5); confidence is a separate
High, Moderate or Low rating (section 6). Everything here is pure string handling so
the validator, the prompts and the tests share one definition.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class Probability(StrEnum):
    REMOTE_CHANCE = "remote_chance"
    HIGHLY_UNLIKELY = "highly_unlikely"
    UNLIKELY = "unlikely"
    REALISTIC_POSSIBILITY = "realistic_possibility"
    LIKELY = "likely"
    HIGHLY_LIKELY = "highly_likely"
    ALMOST_CERTAIN = "almost_certain"


class Confidence(StrEnum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class YardstickBand:
    probability: Probability
    term: str
    low_percent: int
    high_percent: int

    @property
    def range_description(self) -> str:
        """PHIA's approximate, discontinuous bands exclude certainty and the 50% boundary."""
        lower = "above 0" if self.low_percent == 0 else f"about {self.low_percent}"
        upper = (
            f"under {self.high_percent}"
            if self.high_percent in (50, 100)
            else f"about {self.high_percent}"
        )
        return f"{lower} to {upper} percent"


YARDSTICK: tuple[YardstickBand, ...] = (
    YardstickBand(Probability.REMOTE_CHANCE, "remote chance", 0, 5),
    YardstickBand(Probability.HIGHLY_UNLIKELY, "highly unlikely", 10, 20),
    YardstickBand(Probability.UNLIKELY, "unlikely", 25, 35),
    YardstickBand(Probability.REALISTIC_POSSIBILITY, "realistic possibility", 40, 50),
    YardstickBand(Probability.LIKELY, "likely", 55, 75),
    YardstickBand(Probability.HIGHLY_LIKELY, "highly likely", 80, 90),
    YardstickBand(Probability.ALMOST_CERTAIN, "almost certain", 95, 100),
)

# Phrases that map to a band but are not the band's own term ("probable" is the same band).
TERM_TO_BAND: dict[str, Probability] = {band.term: band.probability for band in YARDSTICK} | {
    "probable": Probability.LIKELY
}

# US ICD 203 and other likelihood language the PHIA vocabulary replaces.
FORBIDDEN_TERMS: tuple[str, ...] = (
    "almost no chance",
    "very unlikely",
    "roughly even chance",
    "roughly even odds",
    "chances about even",
    "very likely",
    "nearly certain",
    "probably not",
    "improbable",
    "even chance",
)

HEDGES: tuple[str, ...] = ("may", "might", "could", "possible", "possibly")
CONFIDENCE_PHRASES: tuple[str, ...] = (
    "high confidence",
    "moderate confidence",
    "low confidence",
    "confidence is high",
    "confidence is moderate",
    "confidence is low",
)
JUDGEMENT_OPENERS: tuple[str, ...] = ("we assess", "we judge")


def _phrase_pattern(phrases: Iterable[str]) -> re.Pattern[str]:
    # Longest first so "highly unlikely" wins over "unlikely" and "very likely" over "likely".
    ordered = sorted(phrases, key=len, reverse=True)
    return re.compile(r"\b(" + "|".join(re.escape(p) for p in ordered) + r")\b", re.IGNORECASE)


_LIKELIHOOD = _phrase_pattern([*FORBIDDEN_TERMS, *TERM_TO_BAND])
_HEDGE = _phrase_pattern(HEDGES)
_CONFIDENCE = _phrase_pattern(CONFIDENCE_PHRASES)
_URL = re.compile(r"https?://[^\s)\]>\"']+", re.IGNORECASE)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True, slots=True)
class LikelihoodScan:
    bands: tuple[Probability, ...]
    forbidden: tuple[str, ...]


def scan_likelihood(text: str) -> LikelihoodScan:
    """Yardstick bands and forbidden likelihood phrases found in `text`, in order."""
    bands: list[Probability] = []
    forbidden: list[str] = []
    for match in _LIKELIHOOD.finditer(text):
        phrase = match.group(1).lower()
        band = TERM_TO_BAND.get(phrase)
        if band is None:
            forbidden.append(phrase)
        else:
            bands.append(band)
    return LikelihoodScan(tuple(bands), tuple(forbidden))


def distinct_bands(text: str) -> tuple[Probability, ...]:
    seen: list[Probability] = []
    for band in scan_likelihood(text).bands:
        if band not in seen:
            seen.append(band)
    return tuple(seen)


def find_hedges(text: str) -> tuple[str, ...]:
    return tuple(match.group(1).lower() for match in _HEDGE.finditer(text))


def mentions_confidence(text: str) -> bool:
    return _CONFIDENCE.search(text) is not None


def find_urls(text: str) -> tuple[str, ...]:
    return tuple(match.group(0) for match in _URL.finditer(text))


def sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE.split(text.strip()) if part.strip()]


def opens_as_judgement(statement: str) -> bool:
    lowered = statement.strip().lower()
    return any(lowered.startswith(opener) for opener in JUDGEMENT_OPENERS)


def term_for(probability: Probability) -> str:
    return next(band.term for band in YARDSTICK if band.probability is probability)
