"""Journal intent is durable before mutation, and uncertainty survives rollback or commit."""

from unittest.mock import AsyncMock, Mock

import pytest

from ase.adapters.persistence.models import ReportRow
from ase.adapters.persistence.private_review_models import PrivateDataReviewRow
from ase.domain.errors import Conflict
from ase.domain.private_removal import RemovalRequest, RemovalScope, ReviewDecision, ReviewPurpose
from private_removal_helpers import preview, report
from recovery_helpers import journal as journal  # noqa: PLC0414


async def reviewed(container, admin, user, journal):
    async with container.session_factory() as session:
        return await container.private_removal(session, journal).review(
            admin,
            user.id,
            ReviewDecision.REMOVE,
            ReviewPurpose.RIGHTS_REQUEST,
            0,
        )


async def test_stale_revision_does_not_poison_external_history(container, admin, user, journal):
    await reviewed(container, admin, user, journal)
    before = journal.inspect()
    with pytest.raises(Conflict, match="review changed"):
        await reviewed(container, admin, user, journal)
    assert journal.inspect() == before


@pytest.mark.parametrize("operation", ["review", "apply"])
async def test_finalisation_failure_keeps_committed_change_and_pending_intent(
    container,
    admin,
    user,
    journal,
    monkeypatch,
    operation,
):
    target, _ = await report(container, user)
    request = RemovalRequest(user.id, RemovalScope.REPORT, target.id)
    if operation == "apply":
        await reviewed(container, admin, user, journal)
        plan = await preview(container, admin, request)
    monkeypatch.setattr(journal, "complete", Mock(side_effect=OSError("synthetic failure")))
    with pytest.raises(Conflict, match=r"database committed.*unconfirmed"):
        if operation == "review":
            await reviewed(container, admin, user, journal)
        else:
            async with container.session_factory() as session:
                await container.private_removal(session, journal).apply(
                    admin, request, plan.fingerprint
                )
    result = journal.inspect()
    assert len(result["unresolved_intents"]) == 1
    assert result["events"][-1]["status"] == "pending"
    async with container.session_factory() as session:
        row = await session.get(PrivateDataReviewRow, user.id)
        assert row.decision == "remove"
        assert (await session.get(ReportRow, target.id) is None) == (operation == "apply")


async def test_intent_failure_prevents_database_change(
    container, admin, user, journal, monkeypatch
):
    monkeypatch.setattr(journal, "begin_review", Mock(side_effect=OSError("synthetic failure")))
    with pytest.raises(OSError):
        await reviewed(container, admin, user, journal)
    async with container.session_factory() as session:
        assert await session.get(PrivateDataReviewRow, user.id) is None
    assert journal.inspect()["events"] == []


@pytest.mark.parametrize("actually_committed", [False, True])
async def test_commit_failure_is_not_inferred_to_mean_rollback(
    container,
    admin,
    user,
    journal,
    actually_committed,
):
    async with container.session_factory() as session:
        service = container.private_removal(session, journal)
        commit = service.uow.commit

        async def uncertain_commit():
            if actually_committed:
                await commit()
            raise OSError("synthetic connection loss")

        service.uow.commit = AsyncMock(side_effect=uncertain_commit)
        with pytest.raises(OSError):
            await service.review(admin, user.id, ReviewDecision.HOLD, ReviewPurpose.QUARTERLY, 0)
    assert len(journal.inspect()["unresolved_intents"]) == 1
    async with container.session_factory() as session:
        assert (await session.get(PrivateDataReviewRow, user.id) is not None) == actually_committed
