"""Read-only bounded search of explicitly imported GeoGCDF reference catalogues."""

import json
import re
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ase.adapters.research_records.aiddata_catalogue import MAX_CATALOGUE_BYTES, MAX_PROJECTS
from ase.adapters.research_records.aiddata_records import RELEASE_COMMIT, RELEASE_ID, AidDataRecord
from ase.adapters.research_records.project_spatial import ProjectSpatialFilter
from ase.domain.evidence_geometry import LocationRole, geometry_from_dict
from ase.domain.project import project_from_dict
from ase.domain.project_time import ProjectYearMatch, commitment_match
from ase.domain.research_area import ResearchArea

MAX_ROW_BYTES = 8 * 1024 * 1024
MAX_RESULT_BYTES = 20 * 1024 * 1024
MAX_RESULTS = 20


@dataclass(frozen=True, slots=True)
class CatalogueResults:
    records: tuple[AidDataRecord, ...]
    matches: tuple[ProjectYearMatch, ...]
    truncated: bool
    catalogue_count: int
    manifest_sha256: str


def _record(text: str) -> AidDataRecord:
    value = json.loads(text)
    if not isinstance(value, dict) or set(value) != {
        "title",
        "recipient",
        "sector",
        "amount_constant_usd_2021",
        "project",
        "geometry",
    }:
        raise ValueError("Invalid catalogue record")
    for key, bound in (("title", 5000), ("recipient", 300), ("sector", 300)):
        field = value[key]
        if (
            not isinstance(field, str)
            or not field.strip()
            or len(field) > bound
            or any(ord(char) < 32 for char in field)
        ):
            raise ValueError("Invalid catalogue text")
        field.encode("utf-8")
    project = project_from_dict(value["project"])
    if (
        project is None
        or project.dataset_id != "aiddata-geogcdf"
        or project.release_id != RELEASE_ID
    ):
        raise ValueError("Invalid catalogue project provenance")
    if (
        not re.fullmatch(r"[0-9]{1,12}", project.project_id)
        or project.data_licence != "ODC-By-1.0"
        or project.geometry_licence != "ODbL-1.0"
    ):
        raise ValueError("Invalid catalogue identity or licence metadata")
    geometry = geometry_from_dict(value["geometry"])
    if geometry is not None and (
        geometry.location_role is not LocationRole.PROJECT_SITE
        or geometry.precision != project.precision
    ):
        raise ValueError("Invalid catalogue project geometry")
    amount = value["amount_constant_usd_2021"]
    if amount is not None and (
        not isinstance(amount, str) or len(amount) > 100 or not Decimal(amount).is_finite()
    ):
        raise ValueError("Invalid catalogue amount")
    return AidDataRecord(
        value["title"],
        value["recipient"],
        value["sector"],
        amount,
        project,
        geometry,
    )


def _metadata(connection: sqlite3.Connection) -> tuple[int, str]:
    tables = dict(
        connection.execute(
            "SELECT name,type FROM sqlite_schema WHERE name IN ('metadata','projects')"
        )
    )
    if tables != {"metadata": "table", "projects": "table"}:
        raise ValueError("Invalid reference catalogue tables")
    rows = connection.execute(
        "SELECT key,CASE WHEN length(value)<=300 THEN value END FROM metadata LIMIT 20"
    ).fetchall()
    metadata = dict(rows)
    if (
        len(rows) != 7
        or metadata.get("schema_version") != "1"
        or metadata.get("release_id") != RELEASE_ID
        or metadata.get("release_commit") != RELEASE_COMMIT
    ):
        raise ValueError("Unsupported reference catalogue metadata")
    count = int(metadata["project_count"])
    digest = metadata["manifest_sha256"]
    if (
        not 1 <= count <= MAX_PROJECTS
        or not isinstance(digest, str)
        or not re.fullmatch(r"[a-f0-9]{64}", digest)
    ):
        raise ValueError("Invalid reference catalogue manifest")
    return count, digest


def _check_deadline(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise ValueError("Project catalogue search exceeded its work limit")


def search_catalogue(
    path: Path,
    *,
    terms: tuple[str, ...],
    since: datetime,
    until: datetime,
    recipient_iso3: str | None = None,
    project_id: str | None = None,
    include_unknown_years: bool = False,
    area: ResearchArea | None = None,
) -> CatalogueResults:
    """All terms must occur in project title/recipient/sector; no query-time downloads.

    Date matches are possible within a reported year, not exact occurrence claims.
    Read-only mode, a query deadline, row/result bounds and strict decoding apply
    even when an operator has replaced or modified an imported database.
    """
    if (
        any(value.utcoffset() is None for value in (since, until))
        or since >= until
        or (project_id is not None and not re.fullmatch(r"[0-9]{1,12}", project_id))
        or type(include_unknown_years) is not bool
        or len(terms) > 12
        or any(not term.strip() or len(term) > 300 for term in terms)
        or (recipient_iso3 is not None and not re.fullmatch(r"[A-Z]{3}", recipient_iso3))
    ):
        raise ValueError("Invalid project search scope")
    spatial = ProjectSpatialFilter(area) if area is not None else None
    if path.stat().st_size > MAX_CATALOGUE_BYTES:
        raise ValueError("Reference catalogue exceeds its size limit")
    since, until = since.astimezone(UTC), until.astimezone(UTC)
    parameters = [
        MAX_ROW_BYTES,
        since.year,
        (until - timedelta(microseconds=1)).year,
        include_unknown_years,
        recipient_iso3,
        recipient_iso3,
        project_id,
        project_id,
        json.dumps([term.casefold() for term in terms]),
        MAX_PROJECTS + 1 if spatial else MAX_RESULTS + 1,
    ]
    sql = (
        "SELECT id,recipient_iso3,commitment_year,CASE WHEN length(CAST(record_json AS BLOB))<=? "
        "THEN record_json END FROM projects "
        "WHERE (commitment_year BETWEEN ? AND ? OR (? AND commitment_year IS NULL)) "
        "AND (? IS NULL OR recipient_iso3=?) "
        "AND (? IS NULL OR id=?) "
        "AND NOT EXISTS (SELECT 1 FROM json_each(?) AS term "
        "WHERE instr(search_text, term.value)=0) "
        "ORDER BY id LIMIT ?"
    )
    try:
        with closing(
            sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=0.1)
        ) as connection:
            connection.execute("PRAGMA trusted_schema=OFF")
            connection.execute("PRAGMA query_only=ON")
            connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_ROW_BYTES + 1024)
            deadline = time.monotonic() + 2
            connection.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
            count, digest = _metadata(connection)
            records: list[AidDataRecord] = []
            matches: list[ProjectYearMatch] = []
            size = 0
            truncated = False
            for scanned, (identity, country, year, encoded) in enumerate(
                connection.execute(sql, parameters), 1
            ):
                if scanned > MAX_PROJECTS or time.monotonic() >= deadline:
                    raise ValueError("Project catalogue search exceeded its work limit")
                if not isinstance(encoded, str):
                    raise ValueError("Invalid or oversized catalogue row")
                size += len(encoded.encode("utf-8"))
                if size > MAX_RESULT_BYTES:
                    truncated = True
                    break
                record = _record(encoded)
                if (
                    record.project.project_id != identity
                    or (project_id is not None and identity != project_id)
                    or record.project.recipient_iso3 != country
                    or record.project.commitment_year != year
                ):
                    raise ValueError("Catalogue index and stored record disagree")
                record_text = " ".join((record.title, record.recipient, record.sector)).casefold()
                if any(term.casefold() not in record_text for term in terms):
                    raise ValueError("Catalogue search index and record text disagree")
                match = commitment_match(record.project, since, until)
                if match is ProjectYearMatch.OUTSIDE:
                    raise ValueError("Catalogue returned out-of-window project")
                if spatial is not None and not spatial.intersects(record.geometry):
                    continue
                if len(records) >= MAX_RESULTS:
                    truncated = True
                    break
                records.append(record)
                matches.append(match)
            _check_deadline(deadline)
            return CatalogueResults(tuple(records), tuple(matches), truncated, count, digest)
    except (sqlite3.Error, KeyError, TypeError, InvalidOperation, RecursionError) as exc:
        raise ValueError("Reference catalogue is unavailable or invalid") from exc
