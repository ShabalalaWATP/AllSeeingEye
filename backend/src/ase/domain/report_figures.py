"""Figures and dates written in report prose, and the same values in frozen evidence.

Purely mechanical. The parser reads counts, percentages, percentage points, currency
amounts and calendar dates out of the model's prose and out of the frozen evidence,
then asks whether each prose figure is present in the evidence, is a stated rounding
of an evidence figure, or is a sum or difference the checker can reproduce. Nothing
here changes the report: an unexplained figure becomes a visible review reason.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from itertools import combinations
from typing import Literal

Kind = Literal["count", "percent", "percentage_point", "currency", "date"]

MAX_FIGURES_PER_TEXT = 40
MAX_EVIDENCE_FIGURES = 600
MAX_DERIVATION_TERMS = 24
MAX_DERIVATION_SIZE = 3
# Bare small integers are almost always enumerations ("three fronts"), not reported
# quantities, so they are not treated as traceable figures.
SMALL_COUNT = Decimal(10)

_MONTHS = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)
_MONTH_INDEX = {name: index for index, name in enumerate(_MONTHS, 1)}
_MONTH_INDEX.update({name[:3]: index for index, name in enumerate(_MONTHS, 1)})
_MONTH_PATTERN = "|".join((*_MONTHS, *(name[:3] for name in _MONTHS)))

_SCALES: dict[str, Decimal] = {
    "thousand": Decimal(1_000),
    "k": Decimal(1_000),
    "million": Decimal(1_000_000),
    "m": Decimal(1_000_000),
    "billion": Decimal(1_000_000_000),
    "bn": Decimal(1_000_000_000),
    "trillion": Decimal(1_000_000_000_000),
    "tn": Decimal(1_000_000_000_000),
}
_CURRENCY_SYMBOLS = {"$": "USD", "£": "GBP", "€": "EUR", "¥": "JPY"}
_CURRENCY_CODES = frozenset(
    {"usd", "gbp", "eur", "jpy", "chf", "cny", "rub", "uah", "aud", "cad", "inr", "try"}
)
_DURATION_UNITS = frozenset(
    {
        "second",
        "seconds",
        "minute",
        "minutes",
        "hour",
        "hours",
        "day",
        "days",
        "week",
        "weeks",
        "fortnight",
        "month",
        "months",
        "year",
        "years",
        "decade",
        "decades",
    }
)
_APPROXIMATORS = (
    "approximately",
    "about",
    "around",
    "roughly",
    "nearly",
    "almost",
    "some",
    "circa",
    "an estimated",
    "estimated",
    "up to",
    "at least",
    "more than",
    "over",
    "fewer than",
    "less than",
    "under",
    "in excess of",
    "close to",
)
_APPROX_TAIL = re.compile(
    r"(?:" + "|".join(re.escape(word) for word in _APPROXIMATORS) + r")\s*$", re.IGNORECASE
)
# Evidence labels (E1), requirement identifiers (SIR-2) and Admiralty grades (B2) carry
# digits that are identifiers, not reported quantities.
_IDENTIFIER = re.compile(r"\b(?:E\d{1,3}|(?:PIR|SIR|EEI)-[\d.]+|[A-F][1-6])\b")
_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_NUMBER = re.compile(
    r"(?P<currency>[$£€¥])?\s*"
    r"(?P<number>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"(?:\s*(?P<scale>thousand|million|billion|trillion)\b|(?P<suffix>k|m|bn|tn)(?![\w]))?"
    r"(?:\s*(?P<unit>%|per cent|percentage points?|percent|[A-Za-z]{1,20}))?",
    re.IGNORECASE,
)
_ISO_DATE = re.compile(r"\b(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\b")
_DAY_MONTH = re.compile(
    r"\b(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month>" + _MONTH_PATTERN + r")\.?"
    r"(?:\s+(?P<year>\d{4}))?\b",
    re.IGNORECASE,
)
_MONTH_DAY = re.compile(
    r"\b(?P<month>" + _MONTH_PATTERN + r")\.?\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?"
    r"(?:,?\s+(?P<year>\d{4}))?\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class Figure:
    """One figure as written, normalised enough to compare with another."""

    kind: Kind
    text: str
    value: Decimal | None = None
    currency: str = ""
    day: date | None = None
    approximate: bool = False

    def describe(self) -> str:
        return " ".join(self.text.split())


def _blank_identifiers(text: str) -> str:
    """Remove URLs, labels and grades so their digits are never read as quantities."""
    return _IDENTIFIER.sub(" ", _URL.sub(" ", text))


def _decimal(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return None


def _kind_of(currency: str, unit: str) -> tuple[Kind, str]:
    lowered = unit.strip().casefold()
    if lowered.startswith("percentage point"):
        return "percentage_point", ""
    if lowered in ("%", "per cent", "percent"):
        return "percent", ""
    if currency:
        return "currency", _CURRENCY_SYMBOLS[currency]
    if lowered in _CURRENCY_CODES:
        return "currency", lowered.upper()
    return "count", ""


def _numbers(text: str) -> list[Figure]:
    figures: list[Figure] = []
    for match in _NUMBER.finditer(text):
        value = _decimal(match.group("number"))
        if value is None:
            continue
        scale = match.group("scale") or match.group("suffix")
        if scale:
            value *= _SCALES[scale.casefold()]
        unit = match.group("unit") or ""
        if unit.casefold() in _DURATION_UNITS:
            continue
        kind, currency = _kind_of(match.group("currency") or "", unit)
        if kind == "count" and not scale and value < SMALL_COUNT:
            continue
        approximate = bool(_APPROX_TAIL.search(text[: match.start()]))
        figures.append(
            Figure(kind, match.group(0).strip(), value, currency, approximate=approximate)
        )
        if len(figures) >= MAX_FIGURES_PER_TEXT:
            break
    return figures


def _day(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _dates(text: str, window: tuple[date, date] | None) -> list[Figure]:
    figures: list[Figure] = []
    for match in _ISO_DATE.finditer(text):
        day = _day(int(match.group("year")), int(match.group("month")), int(match.group("day")))
        if day is not None:
            figures.append(Figure("date", match.group(0), day=day))
    for pattern in (_DAY_MONTH, _MONTH_DAY):
        for match in pattern.finditer(text):
            month = _MONTH_INDEX.get(match.group("month").casefold())
            number = int(match.group("day"))
            if month is None or not 1 <= number <= 31:
                continue
            written = match.group("year")
            years = (
                (int(written),)
                if written
                else ((window[1].year, window[1].year - 1, window[0].year) if window else ())
            )
            day = next(
                (value for year in years if (value := _day(year, month, number)) is not None), None
            )
            if day is None:
                continue
            if window and not written and not window[0] <= day <= window[1]:
                # An undated day-month reference outside the window cannot be placed.
                continue
            figures.append(Figure("date", match.group(0), day=day))
    return figures[:MAX_FIGURES_PER_TEXT]


def figures_in(text: str, window: tuple[date, date] | None = None) -> tuple[Figure, ...]:
    """Every checkable figure in one passage, with identifiers and URLs removed first."""
    clean = _blank_identifiers(text)
    dated = _dates(clean, window)
    spans = {figure.text for figure in dated}
    # A date's digits must not be read again as a bare count.
    without_dates = clean
    for span in spans:
        without_dates = without_dates.replace(span, " ")
    return (*dated, *_numbers(without_dates))


def _step(value: Decimal) -> Decimal:
    """The place value the figure appears to be rounded to, from its trailing zeros."""
    whole = value.copy_abs()
    if whole != whole.to_integral_value() or whole == 0:
        return Decimal(1)
    step = Decimal(1)
    while whole % (step * 10) == 0 and step * 10 <= whole / 10:
        step *= 10
    return step


def _tolerance(prose: Figure) -> Decimal:
    if prose.value is None:
        return Decimal(0)
    step = _step(prose.value)
    if step > 1:
        return step / 2
    if prose.approximate:
        return max(Decimal("0.5"), (prose.value.copy_abs() * Decimal("0.02")))
    return Decimal(0)


def _matches(prose: Figure, candidate: Decimal, tolerance: Decimal) -> bool:
    return prose.value is not None and abs(candidate - prose.value) <= tolerance


def _pool(prose: Figure, evidence: tuple[Figure, ...]) -> list[Decimal]:
    return list(
        dict.fromkeys(
            row.value
            for row in evidence
            if row.kind == prose.kind and row.currency == prose.currency and row.value is not None
        )
    )[:MAX_DERIVATION_TERMS]


def derivation_of(prose: Figure, evidence: tuple[Figure, ...]) -> str:
    """Name the sum or difference of evidence figures that reproduces this figure."""
    pool = _pool(prose, evidence)
    tolerance = _tolerance(prose)
    for left, right in combinations(pool, 2):
        for label, candidate in (("+", left + right), ("-", left - right), ("-", right - left)):
            if _matches(prose, candidate, tolerance):
                first, second = (left, right) if label == "+" or left > right else (right, left)
                return f"{first} {label} {second}"
    for size in range(MAX_DERIVATION_SIZE, 2, -1):
        for group in combinations(pool, size):
            if _matches(prose, sum(group, Decimal(0)), tolerance):
                return " + ".join(str(value) for value in group)
    return ""


def traceable(prose: Figure, evidence: tuple[Figure, ...]) -> bool:
    """True when the frozen evidence states this figure, or a value it rounds to."""
    if prose.kind == "date":
        return any(row.kind == "date" and row.day == prose.day for row in evidence)
    tolerance = _tolerance(prose)
    return any(
        row.kind == prose.kind
        and row.currency == prose.currency
        and row.value is not None
        and _matches(prose, row.value, tolerance)
        for row in evidence
    )


def bounded(figures: tuple[Figure, ...]) -> tuple[Figure, ...]:
    return figures[:MAX_EVIDENCE_FIGURES]
