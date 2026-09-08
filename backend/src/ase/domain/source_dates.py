"""Declared calendars only, preserving raw dates and uncertainty independently of retrieval.

Solar Hijri uses the ICU 33-year arithmetic convention, restricted to SH 1304..1468.
The formula and epoch are documented by Unicode ICU persncal.cpp (release 76.1).
This is not the 2820-year calendar or a universal Islamic calendar converter.
"""

import re
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Literal
from uuid import UUID

Calendar = Literal["gregorian", "solar_hijri_icu33", "unknown"]
DateRole = Literal["publication", "occurrence", "record_validity", "modification", "unspecified"]
DateBasis = Literal["operator", "source_spec", "source_metadata"]
DIGITS = {base + digit: str(digit) for base in (0x6F0, 0x660) for digit in range(10)}


@dataclass(frozen=True, slots=True)
class SourceDate:
    field: str
    raw_text: str
    role: DateRole
    calendar: Calendar
    basis: DateBasis
    precision: Literal["instant", "day", "unknown"]
    status: Literal["resolved", "ambiguous", "unsupported", "invalid"]
    method: str
    value: datetime | None = None
    day_start: date | None = None
    day_end: date | None = None
    actor_id: UUID | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 1 <= len(self.field) <= 120 or not 1 <= len(self.raw_text) <= 300:
            raise ValueError("Source date exceeds bounds")
        if self.calendar not in {"gregorian", "solar_hijri_icu33", "unknown"} or (
            self.role
            not in {"publication", "occurrence", "record_validity", "modification", "unspecified"}
            or self.basis not in {"operator", "source_spec", "source_metadata"}
        ):
            raise ValueError("Invalid source date declaration")
        if self.precision not in {"instant", "day", "unknown"} or self.status not in {
            "resolved",
            "ambiguous",
            "unsupported",
            "invalid",
        }:
            raise ValueError("Invalid source date resolution")
        if self.value is not None and self.value.utcoffset() is None:
            raise ValueError("Resolved instants require an explicit timezone")
        if self.status == "resolved":
            if self.precision == "instant" and self.value is not None:
                if self.day_start is not None or self.day_end is not None:
                    raise ValueError("An instant cannot also declare a day interval")
            elif self.precision == "day" and self.day_start is not None and self.day_end:
                if self.day_end - self.day_start != timedelta(days=1) or self.value is not None:
                    raise ValueError("Invalid source day interval")
            else:
                raise ValueError("Resolved dates require a value or day interval")
        elif any(value is not None for value in (self.value, self.day_start, self.day_end)):
            raise ValueError("Unresolved dates cannot claim converted values")
        if (
            not 1 <= len(self.method) <= 120
            or len(self.limitations) > 4
            or any(len(value) > 500 for value in self.limitations)
        ):
            raise ValueError("Invalid date method or limitations")


def solar_hijri_day(year: int, month: int, day: int) -> date:
    if not 1304 <= year <= 1468:
        raise OverflowError("Solar Hijri ICU33 supports years 1304 to 1468 only")
    leap = (25 * year + 11) % 33 < 8
    length = 31 if month <= 6 else (30 if month < 12 or leap else 29)
    if not 1 <= month <= 12 or not 1 <= day <= length:
        raise ValueError("Invalid Solar Hijri day")
    offset = 31 * (month - 1) if month <= 7 else 186 + 30 * (month - 7)
    julian = 1948320 + 365 * (year - 1) + (8 * year + 21) // 33 + offset + day - 1
    return date.fromordinal(julian - 1721425)


def resolve_source_date(
    raw_text: str,
    field: str,
    calendar: Calendar,
    *,
    role: DateRole = "publication",
    basis: DateBasis = "operator",
    actor_id: UUID | None = None,
) -> SourceDate:
    """No inferred calendar, date ordering or zone. Preserve failed parses as evidence."""
    method = "ase-source-date-v1:" + calendar
    base = SourceDate(
        field, raw_text, role, calendar, basis, "unknown", "unsupported", method, actor_id=actor_id
    )

    if calendar == "unknown":
        return replace(base, limitations=("Calendar is undeclared; no conversion attempted.",))
    text = raw_text.strip().translate(DIGITS)
    try:
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
            year, month, day = map(int, text.split("-"))
            converted = (
                solar_hijri_day(year, month, day)
                if calendar == "solar_hijri_icu33"
                else date(year, month, day)
            )
            return replace(
                base,
                precision="day",
                status="resolved",
                day_start=converted,
                day_end=converted + timedelta(days=1),
                limitations=("Calendar day only; timezone and occurrence time are unknown.",),
            )
        if calendar == "solar_hijri_icu33":
            return replace(
                base, limitations=("ICU33 conversion requires an explicit YYYY-MM-DD date.",)
            )
        return _gregorian_instant(base, text)
    except OverflowError:
        return replace(
            base, limitations=("Calendar date is outside the supported conversion range.",)
        )
    except (ValueError, TypeError):
        return replace(
            base, status="invalid", limitations=("Date could not be parsed without guessing.",)
        )


def _gregorian_instant(base: SourceDate, text: str) -> SourceDate:
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        parsed = parsedate_to_datetime(text)
    if parsed.utcoffset() is None:
        return replace(base, status="ambiguous", limitations=("Timezone is undeclared.",))
    return replace(base, precision="instant", status="resolved", value=parsed.astimezone(UTC))
