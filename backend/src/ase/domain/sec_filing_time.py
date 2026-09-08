"""SEC filing calendar labels, never fabricated publication instants or source zones."""

from datetime import datetime, time

from ase.domain.events import Event
from ase.domain.sec_filings import parse_filing_date
from ase.domain.source_dates import SourceDate, resolve_source_date


def filing_source_date(raw: str) -> SourceDate:
    parse_filing_date(raw)
    return resolve_source_date(raw, "filingDate", "gregorian", basis="source_spec")


def filing_day_matches(event: Event, since: datetime | None, until: datetime | None) -> bool | None:
    if (
        event.source_id != "research-sec-submissions"
        or event.attributes.get("record_kind") != "filing_metadata"
    ):
        return None
    declarations = [row for row in event.source_dates if row.role == "publication"]
    if len(declarations) != 1:
        return False
    row = declarations[0]
    try:
        expected = filing_source_date(row.raw_text)
    except ValueError:
        return False
    if row != expected or row.day_start is None or row.day_end is None:
        return False
    # Request calendar labels intentionally do not assert the unknown source timezone.
    if since is not None and row.day_end <= since.date():
        return False
    return not (
        until is not None
        and (
            row.day_start > until.date()
            or (row.day_start == until.date() and until.time() == time.min)
        )
    )
