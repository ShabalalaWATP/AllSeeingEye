"""Authorised identity decisions retain exact evidence, history and caller transactions."""

from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from ase.adapters.persistence.identity_models import IdentityDecisionRow, IdentityRevisionRow
from ase.adapters.persistence.models import ReportRow, ReportVersionRow
from ase.application.reports import identities as service_module
from ase.application.reports.identities import IdentityReviewInput
from ase.domain.errors import Conflict, InvalidRequest, NotFound, Unauthenticated
from ase.domain.identity_review import IdentityDisposition
from report_documents_helpers import document_records
from team_helpers import CONTEXT
from test_identity_review import arguments
from test_saved_map_views import claims_for

VALUE = IdentityReviewInput("E1", IdentityDisposition.UNRESOLVED, "Registry identity is ambiguous.")


async def seed_report(container, user):
    args = arguments()
    record, _ = document_records(user.id)
    version = args["version"]
    record.id = version.report_id
    record.scope = {"research_focus": "company", "research_subject": "中国公司 000123"}
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    return record, version


async def create(container, claims, record):
    async with container.session_factory() as session:
        return await container.report_identities(session).create(
            claims, record.id, 1, VALUE, CONTEXT
        )


async def test_create_correct_and_read_history_preserves_report(client, container, user):
    claims = await claims_for(client, container, user)
    record, version = await seed_report(container, user)
    first = await create(container, claims, record)
    assert first.subject == record.scope["research_subject"]
    async with container.session_factory() as session:
        service = container.report_identities(session)
        second = await service.update(
            claims,
            first.decision_id,
            first.id,
            replace(VALUE, disposition=IdentityDisposition.REJECTED),
            CONTEXT,
        )
        assert second.number == 2 and second.previous_id == first.id
        assert (await service.get(claims, first.decision_id, first.id))[1] == first
        assert (await service.get(claims, first.decision_id))[1] == second
        assert await service.list(claims, record.id, 1) == ((second,), 1)
        assert await service.list(claims, record.id, 1, offset=1) == ((), 1)
        retained = await container.repositories(session).reports.get_version(record.id, 1)
        assert retained == version
        with pytest.raises(Conflict, match="newer"):
            await service.update(claims, first.decision_id, first.id, VALUE, CONTEXT)


async def test_duplicate_candidate_returns_conflict_without_new_rows(client, container, user):
    claims = await claims_for(client, container, user)
    record, _ = await seed_report(container, user)
    first = await create(container, claims, record)
    with pytest.raises(Conflict, match="already"):
        await create(container, claims, record)
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(IdentityDecisionRow)) == 1
        assert await session.scalar(select(func.count()).select_from(IdentityRevisionRow)) == 1
        assert (await container.report_identities(session).get(claims, first.decision_id))[
            1
        ] == first


@pytest.mark.parametrize("operation", ["get", "list", "create", "update"])
async def test_stale_session_is_rejected(client, container, user, operation):
    claims = await claims_for(client, container, user)
    record, _ = await seed_report(container, user)
    first = await create(container, claims, record)
    stale = replace(claims, security_version=claims.security_version + 1)
    async with container.session_factory() as session:
        service = container.report_identities(session)
        with pytest.raises(Unauthenticated):
            if operation == "get":
                await service.get(stale, first.decision_id)
            elif operation == "list":
                await service.list(stale, record.id, 1)
            elif operation == "create":
                await service.create(stale, record.id, 1, VALUE, CONTEXT)
            else:
                await service.update(stale, first.decision_id, first.id, VALUE, CONTEXT)


@pytest.mark.parametrize("change", ["subject", "evidence", "candidate", "index"])
async def test_changed_anchor_or_corrupt_history_rejected(client, container, user, change):
    claims = await claims_for(client, container, user)
    record, _ = await seed_report(container, user)
    first = await create(container, claims, record)
    async with container.session_factory() as session:
        if change == "subject":
            await session.execute(
                update(ReportRow)
                .where(ReportRow.id == record.id)
                .values(scope={"research_focus": "company", "research_subject": "Another company"})
            )
        elif change == "evidence":
            await session.execute(
                update(ReportVersionRow)
                .where(ReportVersionRow.id == first.report_version_id)
                .values(evidence=[])
            )
        elif change == "candidate":
            await session.execute(
                update(IdentityDecisionRow)
                .where(IdentityDecisionRow.id == first.decision_id)
                .values(candidate_label="E2")
            )
        else:
            await session.execute(
                update(IdentityRevisionRow)
                .where(IdentityRevisionRow.id == first.id)
                .values(number=2)
            )
        await session.commit()
        service = container.report_identities(session)
        with pytest.raises(Conflict):
            await service.get(claims, first.decision_id)
        with pytest.raises(Conflict):
            await service.update(claims, first.decision_id, first.id, VALUE, CONTEXT)


@pytest.mark.parametrize("quota", ["count", "bytes"])
async def test_quota_rejects_before_storage(client, container, user, monkeypatch, quota):
    claims = await claims_for(client, container, user)
    record, _ = await seed_report(container, user)
    monkeypatch.setattr(
        service_module, "MAX_SCOPE_DECISIONS" if quota == "count" else "MAX_SCOPE_BYTES", 0
    )
    with pytest.raises(InvalidRequest, match="limit"):
        await create(container, claims, record)
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(IdentityDecisionRow)) == 0


async def test_audit_failure_rolls_back_creation(client, container, user):
    claims = await claims_for(client, container, user)
    record, _ = await seed_report(container, user)
    async with container.session_factory() as session:
        service = container.report_identities(session)
        service.auditor.record = AsyncMock(side_effect=RuntimeError("audit unavailable"))
        with pytest.raises(RuntimeError, match="audit unavailable"):
            await service.create(claims, record.id, 1, VALUE, CONTEXT)
        assert await session.scalar(select(func.count()).select_from(IdentityDecisionRow)) == 0
        assert await session.scalar(select(func.count()).select_from(IdentityRevisionRow)) == 0


@pytest.mark.parametrize(
    "scope",
    [
        {},
        {"research_focus": "company"},
        {"research_focus": "general", "research_subject": "Ambiguous organisation"},
    ],
)
async def test_no_explicit_company_subject_cannot_create(client, container, user, scope):
    claims = await claims_for(client, container, user)
    record, _ = await seed_report(container, user)
    async with container.session_factory() as session:
        await session.execute(
            update(ReportRow).where(ReportRow.id == record.id).values(scope=scope)
        )
        await session.commit()
    with pytest.raises(InvalidRequest, match="explicit company"):
        await create(container, claims, record)


async def test_other_personal_owner_is_hidden(client, container, user):
    claims = await claims_for(client, container, user)
    record, _ = await seed_report(container, user)
    first = await create(container, claims, record)
    async with container.session_factory() as session:
        await session.execute(
            update(ReportRow).where(ReportRow.id == record.id).values(created_by=uuid4())
        )
        await session.commit()
        service = container.report_identities(session)
        with pytest.raises(NotFound):
            await service.get(claims, first.decision_id)
        with pytest.raises(NotFound):
            await service.list(claims, record.id, 1)
