"""Strict native-list parsing for explicitly imported, bounded designation snapshots.

UKSL: https://www.gov.uk/guidance/format-guide-for-the-uk-sanctions-list
OFAC: https://ofac.treasury.gov/sdn-list-data-formats-data-schemas/tutorial-on-the-use-of-list-related-legacy-flat-files
The retired OFSI consolidated format is deliberately not accepted.
"""

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

Authority = Literal["uksl", "ofac_sdn"]
MAX_BYTES = 32 * 1024 * 1024
MAX_ROWS = 100_000
SOURCE_URLS = {
    "uksl": "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv",
    "ofac_sdn": "https://sanctionslistservice.ofac.treas.gov/api/download/sdn.csv",
}


@dataclass(frozen=True, slots=True)
class DesignationRecord:
    authority_id: str
    name: str
    native_name: str
    kind: str
    programme: str
    designated_on: str
    updated_on: str
    name_type: str


@dataclass(frozen=True, slots=True)
class DesignationSnapshot:
    authority: Authority
    version: str
    published_at: datetime
    licence: str
    source_sha256: str
    records: tuple[DesignationRecord, ...]

    def __post_init__(self) -> None:
        if self.authority not in SOURCE_URLS or not re.fullmatch(
            r"[A-Za-z0-9_-]{1,64}", self.version
        ):
            raise ValueError("Invalid snapshot authority or version")
        if self.published_at.utcoffset() is None:
            raise ValueError("Snapshot publication time requires a timezone")
        if not 1 <= len(self.licence) <= 300 or not re.fullmatch(
            r"[a-f0-9]{64}", self.source_sha256
        ):
            raise ValueError("Snapshot requires licence metadata and SHA-256")
        if not 1 <= len(self.records) <= MAX_ROWS:
            raise ValueError("Snapshot record count is outside bounds")
        for record in self.records:
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", record.authority_id) or not record.name:
                raise ValueError("Invalid designation identity")
            if any(len(getattr(record, field)) > 500 for field in record.__dataclass_fields__):
                raise ValueError("Designation field exceeds bounds")


def _cell(value: str) -> str:
    result = value.strip()
    if len(result) > 500 or "\x00" in result:
        raise ValueError("Designation field exceeds bounds")
    return "" if result == "-0-" else result


def parse_csv(
    data: bytes, authority: Authority, published_at: datetime
) -> tuple[DesignationRecord, ...]:
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Designation CSV exceeds 32 MiB")
    stream = io.StringIO(data.decode("utf-8-sig"), newline="")
    if authority == "uksl":
        report_date = stream.readline().strip()
        if not report_date.startswith("Report Date: "):
            raise ValueError("Expected current UKSL report-date header, not retired OFSI format")
        reported = datetime.strptime(report_date.removeprefix("Report Date: "), "%d-%b-%Y")
        if reported.date() != published_at.date():
            raise ValueError("UKSL report date does not match declared publication date")
        rows = csv.DictReader(stream, strict=True)
        required = {
            "Unique ID",
            "Name 1",
            "Name 6",
            "Name type",
            "Regime Name",
            "Date Designated",
            "Last Updated",
        }
        if not rows.fieldnames or not required.issubset(rows.fieldnames):
            raise ValueError("Unsupported UKSL CSV columns")
        records = []
        for index, row in enumerate(rows):
            if index >= MAX_ROWS or None in row or any(value is None for value in row.values()):
                raise ValueError("Invalid or oversized UKSL CSV")
            records.append(
                DesignationRecord(
                    _cell(row["Unique ID"]),
                    _cell(
                        " ".join(
                            row.get(f"Name {number}", "").strip() for number in range(1, 7)
                        ).strip()
                    ),
                    _cell(row.get("Name non-latin script", "")),
                    _cell(row.get("Designation Type", row.get("Individual, Entity, Ship", ""))),
                    _cell(row["Regime Name"]),
                    _cell(row["Date Designated"]),
                    _cell(row["Last Updated"]),
                    _cell(row["Name type"]),
                )
            )
        return tuple(records)
    if authority != "ofac_sdn":
        raise ValueError("Unsupported designation authority")
    output = []
    for index, columns in enumerate(csv.reader(stream, strict=True)):
        if (
            index >= MAX_ROWS
            or len(columns) != 12
            or not re.fullmatch(r"[0-9]{1,12}", columns[0].strip())
        ):
            raise ValueError("Expected the native headerless 12-column OFAC SDN CSV")
        output.append(
            DesignationRecord(
                _cell(columns[0]),
                _cell(columns[1]),
                "",
                _cell(columns[2]),
                _cell(columns[3]),
                "",
                "",
                "primary_name_only",
            )
        )
    return tuple(output)
