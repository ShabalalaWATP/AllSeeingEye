"""Author requirements remain exact in the immutable saved report version."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import select

from ase.adapters.persistence.models import ReportVersionRow
from ase.api.schemas_reports import ReportVersionOut
from ase.domain.report_records import (
    document_schema_version_from_analysis,
    requirements_from_analysis,
)
from ase.domain.research_brief_values import IntelligenceRequirement
from report_documents_helpers import document_records


async def test_twelve_requirements_round_trip_in_saved_version(container) -> None:
    record, version = document_records()
    requirements = tuple(
        IntelligenceRequirement(
            f"REQ-{index}", f"Exactly worded question {index}?", index < 8, index
        )
        for index in range(1, 13)
    )
    brief_id = uuid4()
    version = replace(
        version,
        canonical_requirements=requirements,
        brief_id=brief_id,
        brief_revision=3,
        document_schema_version=2,
    )
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    async with container.session_factory() as session:
        saved = await container.repositories(session).reports.get_version(record.id, 1)
        row = await session.scalar(
            select(ReportVersionRow).where(ReportVersionRow.id == version.id)
        )
    assert saved is not None
    assert saved.canonical_requirements == requirements
    assert (saved.brief_id, saved.brief_revision) == (brief_id, 3)
    assert saved.document_schema_version == 2
    projected = ReportVersionOut.from_version(saved)
    assert (projected.brief_id, projected.brief_revision) == (brief_id, 3)
    assert [row.id for row in projected.canonical_requirements] == [row.id for row in requirements]
    assert row is not None
    assert len(row.analysis["canonical_requirements"]) == 12
    assert row.analysis["document_schema_version"] == 2


def test_historical_analysis_without_canonical_requirements_is_unchanged() -> None:
    assert requirements_from_analysis(None) == ()
    assert requirements_from_analysis({"direction": None}) == ()
    assert document_schema_version_from_analysis(None) == 1
    assert document_schema_version_from_analysis({"direction": None}) == 1


def test_invalid_saved_document_projection_version_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unsupported frozen document projection version"):
        document_schema_version_from_analysis({"document_schema_version": 3})


def test_malformed_saved_requirement_fails_closed() -> None:
    with pytest.raises(ValueError, match="Invalid saved canonical requirement"):
        requirements_from_analysis({"canonical_requirements": [{"id": "REQ-1"}]})
