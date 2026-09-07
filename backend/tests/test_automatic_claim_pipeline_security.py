"""Late revocation, cancellation and quotas are enforced in the real report pipeline."""

import asyncio

import pytest
from sqlalchemy import func, select, update

from ase.adapters.persistence.models import LlmUsageRow, ReportRow, UserRow
from ase.application.reports import automatic_claim_storage as storage_module
from ase.application.reports.request import ReportRequest
from ase.domain.claim_generation import ClaimGenerationStatus
from ase.domain.errors import NotFound, Unauthenticated
from team_helpers import CONTEXT, team_service
from test_automatic_claim_pipeline import ClaimGateway, prepare
from test_report_team_scope import team_for


class HookedClaimGateway(ClaimGateway):
    def __init__(self, hook):
        super().__init__()
        self.hook = hook

    async def complete(self, base_url, api_key, model, request):
        if request.schema_name == "claim_proposals":
            await self.hook()
        return await super().complete(base_url, api_key, model, request)


async def test_account_revoked_during_claim_call_cannot_save(container, user):
    await prepare(container, user)

    async def revoke():
        async with container.session_factory() as session:
            await session.execute(
                update(UserRow).where(UserRow.id == user.id).values(is_active=False)
            )
            await session.commit()

    container.llm = HookedClaimGateway(revoke)
    async with container.session_factory() as session:
        with pytest.raises(Unauthenticated):
            await container.generate_report(session).execute(
                user, ReportRequest("ask", question="What changed?"), CONTEXT
            )
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(ReportRow)) == 0


async def test_team_membership_removed_during_claim_call_cannot_save(container, user, admin):
    await prepare(container, user)
    team = await team_for(container, admin, user)

    async def remove():
        async with team_service(container) as service:
            await service.remove_member(admin, team.id, user.id, CONTEXT)

    container.llm = HookedClaimGateway(remove)
    async with container.session_factory() as session:
        with pytest.raises(NotFound):
            await container.generate_report(session).execute(
                user, ReportRequest("ask", question="What changed?", team_id=team.id), CONTEXT
            )
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(ReportRow)) == 0


async def test_claim_call_cancellation_leaves_no_report_or_buffered_usage(container, user):
    await prepare(container, user)
    entered = asyncio.Event()

    async def pause():
        entered.set()
        await asyncio.Event().wait()

    container.llm = HookedClaimGateway(pause)
    async with container.session_factory() as session:
        task = asyncio.create_task(
            container.generate_report(session).execute(
                user, ReportRequest("ask", question="What changed?"), CONTEXT
            )
        )
        await asyncio.wait_for(entered.wait(), 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not session.in_transaction()
    async with container.session_factory() as session:
        for table in (ReportRow, LlmUsageRow):
            assert await session.scalar(select(func.count()).select_from(table)) == 0


async def test_quota_exceeded_receipt_is_frozen_with_report(container, user, monkeypatch):
    await prepare(container, user)

    async def consume_capacity():
        monkeypatch.setattr(storage_module, "MAX_SCOPE_CLAIMS", 1)

    container.llm = HookedClaimGateway(consume_capacity)
    async with container.session_factory() as session:
        record, version = await container.generate_report(session).execute(
            user, ReportRequest("ask", question="What changed?"), CONTEXT
        )
        assert version.claim_generation.status is ClaimGenerationStatus.QUOTA_EXCEEDED
        assert not version.claim_generation.revision_ids
    async with container.session_factory() as session:
        r = container.repositories(session)
        stored = await r.reports.get_version(record.id, 1)
        assert stored.claim_generation == version.claim_generation
        assert stored.claim_generation.model_origin is not None
        assert await r.claims.scope_usage(user.id, None) == (0, 0)
        assert any(row.purpose == "claim_proposals" for row in await r.llm_usage.list_recent(10))
