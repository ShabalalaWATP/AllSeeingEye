"""Mechanical checks run before anything generated is stored or shown.

Every number in the text must match a supplied figure within rounding, every year must
exist in the supplied data, and the wording must stay inside the house rules. A failure
returns readable messages so one retry can be attempted; nothing unchecked is ever kept.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from ase.application.economy_explainer_facts import FactPack
from ase.domain.economy_explainer import (
    GLOSSARY_ENTRIES,
    MAX_PARAGRAPH,
    MAX_PLAIN_ENGLISH,
    MAX_POINT,
    MAX_TAKEAWAY,
    MAX_TERM,
    REGION_IDS,
    ExplainerText,
    section_bounds,
)

NUMBER = re.compile(r"(?<![\d.,])\d[\d,]*(?:\.\d+)?")
SENTENCE = re.compile(r"(?<=[.!?])\s+")
LINK = re.compile(r"https?://|www\.|://|\[[^\]]*\]\([^)]*\)", re.IGNORECASE)
MARKUP = re.compile(r"[<>]|&lt;|&gt;|&amp;|&#\d")
# Em dash and en dash: house style forbids both in written prose.
LONG_DASHES = (chr(0x2014), chr(0x2013))
SCALES = (1.0, 1e3, 1e6, 1e9, 1e12)
YEAR_RANGE = (1900, 2100)
# Terms a reader may not know. Each must be explained in the sentence that uses it.
BANNED_JARGON = (
    "quantitative easing",
    "fiscal consolidation",
    "monetary tightening",
    "monetary loosening",
    "yield curve",
    "basis points",
    "stagflation",
    "disinflation",
    "deleveraging",
    "terms of trade",
    "output gap",
    "soft landing",
    "hard landing",
    "headwinds",
    "tailwinds",
    "macroprudential",
    "current account",
    "capital formation",
    "value added",
    "nominal terms",
    "real terms",
)
EXPLANATION_CUES = (
    "which means",
    "which is",
    "which measures",
    "which covers",
    "that means",
    "that is",
    "meaning",
    "in other words",
    "put simply",
    "or simply",
    "in plain terms",
    "in everyday terms",
)


def _date_numbers(value: str | None) -> tuple[float, ...]:
    if not value:
        return ()
    parts = value.split("-")
    return tuple(float(part) for part in parts if part.isdigit())


def _scaled(values: Iterable[float | None]) -> set[float]:
    result: set[float] = set()
    for value in values:
        if value is None:
            continue
        magnitude = abs(float(value))
        for scale in SCALES:
            result.add(magnitude / scale)
    return result


def allowed_numbers(pack: FactPack) -> set[float]:
    """Figures, derived differences, counts and date parts the text may quote."""
    raw: list[float | None] = [float(len(pack.regions)), float(len(pack.fx))]
    years: set[float] = set()
    for region in pack.regions:
        raw.extend(
            (
                float(region.available),
                float(region.stale),
                float(region.unavailable),
                float(len(region.indicators)),
                float(len(region.headlines)),
            )
        )
        for fact in region.indicators:
            raw.extend((fact.latest_value, fact.previous_value, fact.change))
            years.update(_date_numbers(fact.latest_year))
            years.update(_date_numbers(fact.previous_year))
            for year in fact.missing_years:
                years.update(_date_numbers(year))
        for headline in region.headlines:
            years.update(_date_numbers(headline.published_on))
    for rate in pack.fx:
        raw.extend((rate.value, rate.previous_value))
        if rate.value is not None and rate.previous_value not in (None, 0):
            previous = float(rate.previous_value or 0)
            raw.append(round(rate.value - previous, 4))
            raw.append(round((rate.value - previous) / abs(previous) * 100, 2))
        years.update(_date_numbers(rate.observed_on))
        years.update(_date_numbers(rate.previous_on))
    return _scaled(raw) | years


def allowed_years(pack: FactPack) -> set[int]:
    result: set[int] = set()
    for region in pack.regions:
        for fact in region.indicators:
            for value in (fact.latest_year, fact.previous_year, *fact.missing_years):
                if value and value[:4].isdigit():
                    result.add(int(value[:4]))
        for headline in region.headlines:
            result.add(int(headline.published_on[:4]))
    for rate in pack.fx:
        for value in (rate.observed_on, rate.previous_on):
            if value and value[:4].isdigit():
                result.add(int(value[:4]))
    return result


def _matches(token: str, allowed: set[float]) -> bool:
    value = float(token.replace(",", ""))
    decimals = len(token.partition(".")[2])
    tolerance = 0.5 * (10.0**-decimals) + 1e-9
    return any(abs(value - candidate) <= tolerance for candidate in allowed)


def unsupported_numbers(text: str, allowed: set[float], years: set[int]) -> list[str]:
    problems: list[str] = []
    for match in NUMBER.finditer(text):
        token = match.group(0)
        plain = token.replace(",", "")
        if plain.isdigit() and YEAR_RANGE[0] <= int(plain) <= YEAR_RANGE[1]:
            if int(plain) in years or _matches(token, allowed):
                continue
            problems.append(f"the year {token} is not present in the supplied data")
            continue
        if not _matches(token, allowed):
            problems.append(f"the figure {token} does not match any supplied figure")
    return problems


def _sentences(text: str) -> list[str]:
    return [part for part in SENTENCE.split(text) if part.strip()]


def unexplained_jargon(text: str) -> list[str]:
    lowered = text.lower()
    problems: list[str] = []
    for term in BANNED_JARGON:
        if term not in lowered:
            continue
        holders = [part for part in _sentences(lowered) if term in part]
        if any(not any(cue in part for cue in EXPLANATION_CUES) for part in holders):
            problems.append(f'"{term}" is used without a plain explanation in the same sentence')
    return problems


def _style_problems(text: str) -> list[str]:
    problems: list[str] = []
    if LINK.search(text):
        problems.append("a web address or link appears in the text; remove it")
    if MARKUP.search(text):
        problems.append("angle brackets or HTML entities appear in the text; use plain words")
    if any(dash in text for dash in LONG_DASHES):
        problems.append("an em dash or en dash appears in the text; use commas or short sentences")
    return problems


def _length_problems(text: ExplainerText) -> list[str]:
    problems: list[str] = []
    for key, section in text.sections():
        paragraphs, points = section_bounds(key)
        if len(section.takeaway) > MAX_TAKEAWAY:
            problems.append(f"the {key} takeaway is longer than {MAX_TAKEAWAY} characters")
        if not paragraphs[0] <= len(section.paragraphs) <= paragraphs[1]:
            problems.append(f"{key} needs between {paragraphs[0]} and {paragraphs[1]} paragraphs")
        for name, items in (("drivers", section.drivers), ("watch", section.watch)):
            if not points[0] <= len(items) <= points[1]:
                problems.append(f"{key} {name} needs between {points[0]} and {points[1]} entries")
            if any(len(item) > MAX_POINT for item in items):
                problems.append(f"a {key} {name} entry is longer than {MAX_POINT} characters")
        if any(len(item) > MAX_PARAGRAPH for item in section.paragraphs):
            problems.append(f"a {key} paragraph is longer than {MAX_PARAGRAPH} characters")
    if not GLOSSARY_ENTRIES[0] <= len(text.glossary) <= GLOSSARY_ENTRIES[1]:
        problems.append(
            f"the glossary needs between {GLOSSARY_ENTRIES[0]} and {GLOSSARY_ENTRIES[1]} entries"
        )
    for entry in text.glossary:
        if len(entry.term) > MAX_TERM or len(entry.plain_english) > MAX_PLAIN_ENGLISH:
            problems.append(f'the glossary entry "{entry.term[:40]}" is too long')
    return problems


def _region_problems(text: ExplainerText, pack: FactPack) -> list[str]:
    expected = [region.id for region in pack.regions if region.id != "WORLD"]
    written = [key for key, _section in text.regions]
    problems = [
        f'"{key}" is not one of the known regions'
        for key in written
        if key not in REGION_IDS or key == "WORLD"
    ]
    problems.extend(f"the {key} section is missing" for key in expected if key not in written)
    return problems


def body_strings(text: ExplainerText) -> list[str]:
    """Written prose only. The glossary is itself the explanation, so it is checked apart."""
    result: list[str] = []
    for _key, section in text.sections():
        result.append(section.takeaway)
        result.extend(section.paragraphs)
        result.extend(section.drivers)
        result.extend(section.watch)
    return result


def validate_explainer(text: ExplainerText, pack: FactPack) -> list[str]:
    """Return every problem found; an empty list means the text may be stored."""
    problems = _region_problems(text, pack) + _length_problems(text)
    numbers, years = allowed_numbers(pack), allowed_years(pack)
    glossary: Sequence[str] = [
        part for entry in text.glossary for part in (entry.term, entry.plain_english)
    ]
    seen: set[str] = set()
    for value in body_strings(text):
        _collect(
            problems,
            seen,
            (
                *_style_problems(value),
                *unsupported_numbers(value, numbers, years),
                *unexplained_jargon(value),
            ),
        )
    for value in glossary:
        _collect(
            problems, seen, (*_style_problems(value), *unsupported_numbers(value, numbers, years))
        )
    return problems


def _collect(problems: list[str], seen: set[str], found: Sequence[str]) -> None:
    for problem in found:
        if problem not in seen:
            seen.add(problem)
            problems.append(problem)
