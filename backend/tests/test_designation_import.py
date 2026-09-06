"""Synthetic designation imports are bounded, immutable and never identity clearance."""

import csv
import io
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ase.adapters.research_records.designation_import import (
    import_designation_csv,
    load_designation_snapshot,
)
from ase.adapters.research_records.designation_snapshot import MAX_BYTES, parse_csv
from ase.adapters.research_records.designations import DesignationProvider
from ase.domain.research import CollectionStatus, ResearchFocus
from research_records_helpers import CLOCK, QUERY

PUBLISHED = datetime(2026, 9, 3, tzinfo=UTC)
HEADERS = [
    "Unique ID",
    "Name 1",
    "Name 6",
    "Name type",
    "Regime Name",
    "Date Designated",
    "Last Updated",
    "Name non-latin script",
    "Designation Type",
]


def uksl_csv(count: int = 1) -> bytes:
    output = io.StringIO(newline="")
    output.write("Report Date: 03-Sep-2026\n")
    writer = csv.writer(output)
    writer.writerow(HEADERS)
    for index in range(count):
        writer.writerow(
            [
                f"IRN{index:04d}",
                "",
                "Example Entity",
                "Primary Name",
                "Iran regime",
                "01/01/2020",
                "03/09/2026",
                "شرکت می\u200cرود",
                "Entity",
            ]
        )
    return output.getvalue().encode("utf-8")


def imported(tmp_path: Path, count: int = 1):
    source = tmp_path / "synthetic.csv"
    source.write_bytes(uksl_csv(count))
    return import_designation_csv(
        source, tmp_path / "cache", "uksl", "2026-09-03", PUBLISHED, "OGL 3.0, operator-reviewed"
    )


def test_import_is_immutable_versioned_and_preserves_source_bytes_hash(tmp_path: Path) -> None:
    target = imported(tmp_path)
    snapshot = load_designation_snapshot(target)
    assert snapshot.authority == "uksl" and snapshot.published_at == PUBLISHED
    assert snapshot.records[0].native_name == "شرکت می\u200cرود"
    assert len(snapshot.source_sha256) == 64
    before = target.read_bytes()
    with pytest.raises(FileExistsError):
        imported(tmp_path)
    assert target.read_bytes() == before
    assert not list(target.parent.glob(".designation-*"))


@pytest.mark.parametrize(
    "content",
    [
        b"Group ID,Name 1,Name 6\n1,,Old OFSI format\n",
        b"Report Date: 03-Sep-2026\nUnique ID,Name 6\n1,Missing headers\n",
        b"bad\xff",
    ],
)
def test_unsupported_or_retired_formats_never_publish(tmp_path: Path, content: bytes) -> None:
    source = tmp_path / "invalid.csv"
    source.write_bytes(content)
    with pytest.raises((ValueError, UnicodeError)):
        import_designation_csv(source, tmp_path / "cache", "uksl", "v1", PUBLISHED, "reviewed")
    assert not (tmp_path / "cache").exists()


def test_invalid_date_path_version_and_oversized_csv_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="report date"):
        parse_csv(uksl_csv(), "uksl", PUBLISHED.replace(day=2))
    with pytest.raises(ValueError, match="32 MiB"):
        parse_csv(b"x" * (MAX_BYTES + 1), "uksl", PUBLISHED)
    source = tmp_path / "source.csv"
    source.write_bytes(uksl_csv())
    with pytest.raises(ValueError, match="version"):
        import_designation_csv(
            source, tmp_path / "cache", "uksl", "../escape", PUBLISHED, "reviewed"
        )
    assert not (tmp_path / "escape.json").exists()


async def test_matches_are_bounded_candidates_not_identity_or_clearance(tmp_path: Path) -> None:
    snapshot = load_designation_snapshot(imported(tmp_path, 25))
    provider = DesignationProvider(snapshot, CLOCK, "uksl")
    query = replace(
        QUERY, focus=ResearchFocus.COMPANY, subject="  EXAMPLE entity ", source_ids=(provider.id,)
    )
    batch = await provider.collect(query)
    assert len(batch.items) == 20
    assert all(item.grade == "F6" for item in batch.items)
    assert batch.items[0].attributes["identity_match"] == "exact_name_candidate_only"
    assert "not proof of identity or guilt" in batch.attempts[0].explanation
    exact = await provider.collect(replace(query, subject="UKSL:IRN0000"))
    assert len(exact.items) == 1
    assert exact.items[0].attributes["reported_designated_on"] == "01/01/2020"
    assert exact.items[0].attributes["authenticity"].startswith("operator-supplied")
    native = await provider.collect(replace(query, subject="شرکت می\u200cرود"))
    assert len(native.items) == 20
    absent = await provider.collect(replace(query, subject="Example"))
    assert absent.attempts[0].status is CollectionStatus.EMPTY
    assert "absence is not clearance" in absent.attempts[0].explanation


async def test_missing_configuration_and_other_namespace_do_not_download() -> None:
    provider = DesignationProvider(None, CLOCK, "uksl")
    query = replace(QUERY, focus=ResearchFocus.COMPANY, subject="UKSL:IRN0001")
    assert (await provider.collect(query)).attempts[0].status is CollectionStatus.UNAVAILABLE
    assert (await provider.collect(replace(query, subject="OFAC:123"))).attempts[
        0
    ].status is CollectionStatus.UNSUPPORTED


async def test_native_ofac_primary_format_has_explicit_missing_file_limits(tmp_path: Path) -> None:
    source = tmp_path / "sdn.csv"
    source.write_text(
        '123,"Example Name",individual,PROGRAM,-0-,-0-,-0-,-0-,-0-,-0-,-0-,remarks\n',
        encoding="utf-8",
    )
    target = import_designation_csv(
        source, tmp_path / "cache", "ofac_sdn", "v1", PUBLISHED, "Recorded source terms"
    )
    provider = DesignationProvider(load_designation_snapshot(target), CLOCK, "ofac_sdn")
    batch = await provider.collect(replace(QUERY, focus=ResearchFocus.COMPANY, subject="OFAC:123"))
    assert len(batch.items) == 1
    assert "separate aliases, addresses" in batch.attempts[0].explanation
    assert batch.items[0].attributes["reported_designated_on"] == ""
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["schema_version"] = 999
    target.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        load_designation_snapshot(target)
