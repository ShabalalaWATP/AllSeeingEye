"""The final source guard covers both report and session rechecks before release."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.application.reports.original_passages import ReadOriginalPassage
from ase.domain.errors import NotFound, Unauthenticated
from test_private_record_use_cases import NOW, actor


def reader(*, enabled=True, session_error=None):
    owner = actor()
    report_id, version_id, ref = uuid4(), uuid4(), uuid4()
    events = []
    linked = SimpleNamespace(
        passage_ref=ref,
        status="acquired",
        evidence_label="E1",
        event_id="event",
        source_id="source",
        document_version_id="document",
        passage_id="passage",
    )
    version = SimpleNamespace(
        id=version_id,
        number=2,
        research=SimpleNamespace(original_followup=[linked]),
        evidence=[SimpleNamespace(label="E1", event_id="event", source_id="source")],
    )
    report = SimpleNamespace(created_by=owner.id, team_id=None)
    document = SimpleNamespace(
        id="document",
        owner_id=owner.id,
        team_id=None,
        source_id="source",
        acquisition_policy_id="policy",
        canonical_url="https://example.org/document",
        passages=[SimpleNamespace(id="passage")],
    )
    staged = SimpleNamespace(
        id=ref,
        job_id=uuid4(),
        document=document,
        evidence_label="E1",
        event_id="event",
    )

    @asynccontextmanager
    async def guard():
        events.append("guard acquired")
        try:
            yield
        finally:
            events.append("guard released")

    async def report_recheck(*args):
        events.append("report rechecked")

    async def validate_session():
        events.append("session rechecked")
        if session_error:
            raise session_error

    reports = SimpleNamespace(
        execute=AsyncMock(return_value=(report, version)),
        recheck=AsyncMock(side_effect=report_recheck),
    )
    admission = SimpleNamespace(guard=guard, enabled=AsyncMock(return_value=enabled))
    policy = SimpleNamespace(policy_id="policy", permits=lambda *_: True)
    service = ReadOriginalPassage(
        SimpleNamespace(linked=AsyncMock(return_value=staged)),
        reports,
        admission,
        {"source": policy},
        SimpleNamespace(now=lambda: NOW),
    )
    return service, (owner, report_id, 2, ref, validate_session), events, staged


async def test_original_release_rechecks_both_authorities_inside_source_guard():
    service, arguments, events, staged = reader()
    assert await service.execute(*arguments) is staged
    assert events == ["guard acquired", "report rechecked", "session rechecked", "guard released"]


async def test_original_source_revocation_prevents_release_and_unwinds_guard():
    service, arguments, events, _ = reader(enabled=False)
    with pytest.raises(NotFound):
        await service.execute(*arguments)
    assert events == ["guard acquired", "guard released"]


async def test_original_session_revocation_prevents_release_and_unwinds_guard():
    service, arguments, events, _ = reader(session_error=Unauthenticated())
    with pytest.raises(Unauthenticated):
        await service.execute(*arguments)
    assert events == ["guard acquired", "report rechecked", "session rechecked", "guard released"]


@pytest.mark.parametrize("field", ["owner_id", "team_id", "id"])
async def test_original_provenance_mismatch_is_rejected_before_release_guard(field):
    service, arguments, events, staged = reader()
    setattr(staged.document, field, uuid4())
    with pytest.raises(NotFound):
        await service.execute(*arguments)
    assert events == []
