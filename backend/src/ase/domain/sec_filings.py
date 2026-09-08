"""Exact public SEC filing references, distinct from filing assertions."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


def parse_filing_date(value: object) -> date:
    """Accept only the SEC's exact ASCII Gregorian calendar spelling."""
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("SEC filing date must be canonical YYYY-MM-DD")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("SEC filing date must preserve its exact provider spelling")
    return parsed


@dataclass(frozen=True, slots=True)
class SecFiling:
    cik: str
    accession: str
    primary_document: str
    form: str
    filing_date: date
    company_name: str

    def __post_init__(self) -> None:
        if (
            not re.fullmatch(r"[0-9]{10}", self.cik)
            or int(self.cik) == 0
            or not re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}", self.accession)
            or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_.-]{0,110}\.(?:htm|html|txt)",
                self.primary_document,
                re.IGNORECASE,
            )
            or ".." in self.primary_document
            or not 1 <= len(self.form) <= 32
            or not 1 <= len(self.company_name) <= 180
        ):
            raise ValueError("Invalid exact SEC primary-document reference")


@dataclass(frozen=True, slots=True)
class SecFilingPage:
    items: tuple[SecFiling, ...]
    archive_page: int
    archive_pages: int
    offset: int
    next_offset: int | None
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SecFilingChoice:
    selection_id: UUID
    filing: SecFiling
    expires_at: datetime
