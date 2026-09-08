"""Bounded SEC history pages resolve only filenames declared by the issuer JSON."""

import re
from datetime import date
from typing import Any

from ase.adapters.research_records.sec_client import SecClient
from ase.domain.sec_filings import SecFiling, SecFilingPage, parse_filing_date

MAX_ARCHIVE_PAGES = 50
MAX_ROWS = 10000


def identity(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,10}", value) or not int(value):
        raise ValueError("Choose an explicit numeric SEC CIK")
    return value.zfill(10)


def archives(data: dict[str, Any], cik: str, since: date, until: date) -> tuple[list[str], bool]:
    files = data.get("filings", {}).get("files", [])
    if not isinstance(files, list):
        raise ValueError("Invalid SEC history manifest")
    values = []
    for row in files[:1000]:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            continue
        if not re.fullmatch(rf"CIK{cik}-submissions-[0-9]{{3,6}}\.json", row["name"]):
            continue
        try:
            start, end = parse_filing_date(row["filingFrom"]), parse_filing_date(row["filingTo"])
        except (ValueError, TypeError, KeyError):
            continue
        if start <= end and start <= until and end >= since:
            values.append((end, row["name"]))
    names = list(dict.fromkeys(name for _, name in sorted(values, reverse=True)))
    return names[:MAX_ARCHIVE_PAGES], len(names) > MAX_ARCHIVE_PAGES or len(files) > 1000


def rows(data: dict[str, Any], cik: str, company: str, since: date, until: date) -> list[SecFiling]:
    columns: list[list[Any]] = []
    for key in ("accessionNumber", "filingDate", "form", "primaryDocument"):
        column = data.get(key)
        if not isinstance(column, list):
            raise ValueError("Invalid SEC filing columns")
        columns.append(column)
    if len({len(c) for c in columns}) != 1 or len(columns[0]) > MAX_ROWS:
        raise ValueError("Misaligned or oversized SEC filing page")
    result, seen = [], set()
    for accession, filed, form, document in zip(*columns, strict=True):
        if not all(isinstance(v, str) for v in (accession, filed, form, document)):
            continue
        if not re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}", accession) or accession in seen:
            continue
        if (
            not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_.-]{0,110}\.(?:htm|html|txt)", document, re.IGNORECASE
            )
            or ".." in document
        ):
            continue
        try:
            published = parse_filing_date(filed)
        except ValueError:
            continue
        if not since <= published <= until or not form.strip() or len(form) > 32:
            continue
        seen.add(accession)
        result.append(SecFiling(cik, accession, document, form, published, company[:180]))
    return sorted(result, key=lambda row: (row.filing_date, row.accession), reverse=True)


async def index(client: SecClient, cik: str) -> dict[str, Any]:
    data = await client.get_json(f"https://data.sec.gov/submissions/CIK{cik}.json")
    if (
        str(data.get("cik", "")).zfill(10) != cik
        or not isinstance(data.get("name"), str)
        or not data["name"].strip()
    ):
        raise ValueError("Mismatched SEC company identity")
    if not isinstance(data.get("filings"), dict) or not isinstance(
        data["filings"].get("recent"), dict
    ):
        raise ValueError("Missing SEC recent filings")
    return data


async def page(
    client: SecClient, cik: str, since: date, until: date, archive_page: int, offset: int
) -> SecFilingPage:
    data = await index(client, cik)
    names, truncated = archives(data, cik, since, until)
    if not 0 <= archive_page <= len(names):
        raise ValueError("The requested older SEC page is no longer available")
    body = (
        data["filings"]["recent"]
        if archive_page == 0
        else await client.get_json(f"https://data.sec.gov/submissions/{names[archive_page - 1]}")
    )
    filings = rows(body, cik, data["name"], since, until)
    limitations = [
        "Filing metadata is not filing content or SEC verification. Dates have day precision.",
        "Only HTML/TXT primary documents are selectable; other formats and invalid "
        "rows are omitted.",
    ]
    if truncated:
        limitations.append(
            "Older history exceeded the 50-page bound; narrow the filing-date interval."
        )
    return SecFilingPage(
        tuple(filings[offset : offset + 20]),
        archive_page,
        len(names),
        offset,
        offset + 20 if offset + 20 < len(filings) else None,
        tuple(limitations),
    )
