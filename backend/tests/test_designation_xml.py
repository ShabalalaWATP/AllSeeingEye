"""Synthetic UN/EU lists exercise imports, bounds and independent receipts."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ase.adapters.research_records.designation_import import (
    import_designation_csv,
    load_designation_snapshot,
)
from ase.adapters.research_records.designation_snapshot import Authority
from ase.adapters.research_records.designation_xml import parse_xml
from ase.adapters.research_records.designations import DesignationProvider
from ase.domain.research import CollectionStatus, ResearchFocus
from research_records_helpers import CLOCK, QUERY

PUBLISHED = datetime(2026, 9, 30, tzinfo=UTC)
UN = b"""<CONSOLIDATED_LIST dateGenerated="2026-09-30T12:00:00Z"><INDIVIDUALS>
<INDIVIDUAL><DATAID>123</DATAID><FIRST_NAME>Example</FIRST_NAME><SECOND_NAME>Person</SECOND_NAME>
<UN_LIST_TYPE>Example regime</UN_LIST_TYPE><LISTED_ON>2020-01-01</LISTED_ON>
<INDIVIDUAL_ALIAS><ALIAS_NAME>Other Name</ALIAS_NAME></INDIVIDUAL_ALIAS>
</INDIVIDUAL></INDIVIDUALS><ENTITIES><ENTITY><DATAID>456</DATAID>
<FIRST_NAME>Example Company</FIRST_NAME></ENTITY></ENTITIES></CONSOLIDATED_LIST>"""
EU = b"""<export xmlns="http://eu.europa.ec/fpi/fsd/export" generationDate="2026-09-30T12:00:00Z">
<sanctionEntity logicalId="789" lastUpdated="2026-09-20"><subjectType code="enterprise"/>
<regulation programme="Example regime" publicationDate="2020-01-01"/>
<nameAlias wholeName="Example Company" strong="true"/>
<nameAlias wholeName="Other Name"/></sanctionEntity></export>"""


@pytest.mark.parametrize(
    ("authority", "data", "prefix", "identity"),
    [
        ("un_sc", UN, "UNSC", "456"),
        ("eu_fsf", EU, "EUFSF", "789"),
    ],
)
async def test_native_xml_import_is_immutable_and_authority_specific(
    tmp_path: Path,
    authority: Authority,
    data: bytes,
    prefix: str,
    identity: str,
) -> None:
    source = tmp_path / "source.xml"
    source.write_bytes(data)
    target = import_designation_csv(
        source, tmp_path / "cache", authority, "v1", PUBLISHED, "reviewed"
    )
    snapshot = load_designation_snapshot(target)
    with pytest.raises(FileExistsError):
        import_designation_csv(source, tmp_path / "cache", authority, "v1", PUBLISHED, "reviewed")
    provider = DesignationProvider(snapshot, CLOCK, authority)
    query = replace(QUERY, focus=ResearchFocus.COMPANY, subject=f"{prefix}:{identity}")
    batch = await provider.collect(query)
    assert len(batch.items) == 1
    assert batch.items[0].attributes["record_issuer"] == authority
    assert batch.items[0].attributes["snapshot_version"] == "v1"
    assert batch.items[0].attributes["declared_licence"] == "reviewed"
    alias = await provider.collect(replace(query, subject="Other Name", source_ids=(provider.id,)))
    assert len(alias.items) == 1
    unavailable = await DesignationProvider(None, CLOCK, authority).collect(query)
    assert unavailable.attempts[0].status is CollectionStatus.UNAVAILABLE
    assert unavailable.attempts[0].source_id == provider.id


@pytest.mark.parametrize("data", [b"not xml", b'<!DOCTYPE a [<!ENTITY x "boom">]><a>&x;</a>'])
def test_unsafe_xml_is_rejected(data: bytes) -> None:
    with pytest.raises(ValueError, match="unsafe"):
        parse_xml(data, "un_sc", PUBLISHED)


def test_wrong_schema_and_date_are_rejected() -> None:
    with pytest.raises(ValueError, match="namespace"):
        parse_xml(UN, "eu_fsf", PUBLISHED)
    with pytest.raises(ValueError, match="publication date"):
        parse_xml(UN, "un_sc", PUBLISHED.replace(day=29))


def test_xml_row_and_byte_caps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ase.adapters.research_records.designation_xml.MAX_ROWS", 1)
    with pytest.raises(ValueError, match="100,000"):
        parse_xml(UN, "un_sc", PUBLISHED)
    monkeypatch.setattr("ase.adapters.research_records.designation_xml.MAX_BYTES", 10)
    with pytest.raises(ValueError, match="32 MiB"):
        parse_xml(UN, "un_sc", PUBLISHED)
