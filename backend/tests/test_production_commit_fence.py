"""The job completion fence shares the report, claims and audit transaction."""

import asyncio

import pytest
from sqlalchemy import func, select

from ase.adapters.persistence.models import AuditLogRow
from ase.application.dto import RequestContext
from ase.application.reports.production_result import ProductionResult
from ase.application.reports.save_production import SaveProduction
from report_documents_helpers import document_records
from test_automatic_claim_storage import pending_for


@pytest.mark.parametrize("outcome", ["success", "error", "cancel"])
async def test_fence_runs_after_writes_and_failure_rolls_everything_back(container, user, outcome):
    record, version = document_records(user.id)
    pending = pending_for(container, user, version)
    callbacks = []
    async with container.session_factory() as session:
        r = container.repositories(session)
        save = SaveProduction(
            r.reports, r.claims, container.access_policy(session), container._auditor(r), r.uow
        )

        async def fence():
            assert await r.reports.get(record.id) is not None
            assert (await r.claims.scope_usage(user.id, None))[0] == len(pending.revisions)
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(AuditLogRow)
                    .where(AuditLogRow.subject == str(record.id))
                )
                == 1
            )
            callbacks.append(True)
            if outcome == "error":
                raise RuntimeError("Job lease changed")
            if outcome == "cancel":
                raise asyncio.CancelledError()

        async def run():
            await save.save(
                user,
                record,
                ProductionResult(version, pending),
                RequestContext(),
                creating=True,
                automation=False,
                before_commit=fence,
            )

        if outcome == "success":
            await run()
        else:
            with pytest.raises(RuntimeError if outcome == "error" else asyncio.CancelledError):
                await run()
        assert not session.in_transaction()
    assert callbacks == [True]
    async with container.session_factory() as session:
        r = container.repositories(session)
        assert (await r.reports.get(record.id) is not None) is (outcome == "success")
        assert (await r.claims.scope_usage(user.id, None))[0] == (
            len(pending.revisions) if outcome == "success" else 0
        )
        assert await session.scalar(
            select(func.count())
            .select_from(AuditLogRow)
            .where(AuditLogRow.subject == str(record.id))
        ) == (1 if outcome == "success" else 0)
