"""Admission policy runs without SQL or a container and preserves its lock boundary."""

from asyncio import CancelledError
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from ase.application.access import AccessContext
from ase.application.dto import RequestContext
from ase.application.schedules.subscription_enqueue import SubscriptionAdmission
from ase.domain.errors import Unauthenticated
from ase.domain.report_jobs import ReportJob
from ase.domain.schedules import Schedule
from ase.domain.subscription_editions import EditionWorkflow
from ase.domain.users import Role, User
from helpers import FakeClock


def _memory_admission():
    now = datetime(2026, 9, 20, tzinfo=UTC)
    actor = User(
        uuid4(), "owner@example.com", "Owner", Role.USER, True, None, 0, None, None, now, None
    )
    schedule = Schedule(
        uuid4(),
        "Daily",
        "intsum",
        "UA",
        None,
        0,
        "daily",
        0,
        24,
        True,
        actor.id,
        now,
        now + timedelta(days=1),
    )
    context = AccessContext(actor, {}, {})
    events = []
    editions = {}
    revisions = {}
    guarded = False

    async def reserve(edition):
        editions[edition.id] = edition
        return edition

    async def advance(edition, **_kwargs):
        return await reserve(edition)

    async def add_revision(revision):
        revisions[(revision.subscription_id, revision.revision)] = revision
        return revision

    ledger = SimpleNamespace(
        get=AsyncMock(side_effect=editions.get),
        latest_revision=AsyncMock(return_value=None),
        get_lineage=AsyncMock(return_value=None),
        active=AsyncMock(return_value=None),
        add_revision=AsyncMock(side_effect=add_revision),
        get_revision=AsyncMock(
            side_effect=lambda identity, revision: revisions.get((identity, revision))
        ),
        reserve=AsyncMock(side_effect=reserve),
        advance=AsyncMock(side_effect=advance),
    )
    candidate = Mock(spec=ReportJob, brief_id=None, brief_revision=None)

    async def prepare(*_args):
        assert not guarded, "Preparation must finish before the admission guard."
        events.append("prepare")
        return candidate

    async def admit(*_args, check_session, **_kwargs):
        assert guarded
        await check_session()
        events.append("admit")
        return SimpleNamespace(id=uuid4(), status="queued")

    transaction = SimpleNamespace(
        ledger=ledger,
        access=SimpleNamespace(
            context=AsyncMock(return_value=context), background=AsyncMock(return_value=context)
        ),
        jobs=SimpleNamespace(
            prepare_candidate=AsyncMock(side_effect=prepare),
            admit_prepared=AsyncMock(side_effect=admit),
        ),
        auditor=SimpleNamespace(record=AsyncMock()),
        schedule=AsyncMock(return_value=schedule),
        brief=AsyncMock(return_value=None),
        rollback=AsyncMock(),
        commit=AsyncMock(),
    )

    @asynccontextmanager
    async def transactions():
        yield transaction

    @asynccontextmanager
    async def guard():
        nonlocal guarded
        guarded = True
        events.append("lock")
        try:
            yield
        finally:
            guarded = False
            events.append("unlock")

    service = SubscriptionAdmission(transactions, Mock(), FakeClock(now), guard)
    return service, transaction, actor, schedule, events


async def test_manual_admission_uses_only_ports_and_prepares_outside_lock():
    service, transaction, actor, schedule, events = _memory_admission()
    checked = []

    async def check(unit):
        assert unit is transaction
        checked.append(unit)

    request_id = uuid4()
    edition = await service.run_now(schedule.id, request_id, actor, RequestContext(), check)
    assert edition.workflow is EditionWorkflow.QUEUED
    assert events == ["prepare", "lock", "admit", "unlock"]
    assert len(checked) == 3
    transaction.commit.assert_awaited_once()
    # Idempotent repeats release the stored edition without preparing another job.
    assert await service.run_now(schedule.id, request_id, actor, RequestContext(), check) == edition
    transaction.jobs.prepare_candidate.assert_awaited_once()


@pytest.mark.parametrize("error_type", [Unauthenticated, CancelledError])
async def test_interrupted_admission_rolls_back_and_releases_lock(error_type):
    service, transaction, actor, schedule, events = _memory_admission()
    checks = 0

    async def revoke_after_prepare(_unit):
        nonlocal checks
        checks += 1
        if checks > 1:
            raise error_type()

    with pytest.raises(error_type):
        await service.run_now(schedule.id, uuid4(), actor, RequestContext(), revoke_after_prepare)
    transaction.commit.assert_not_awaited()
    # Preparation closes its read transaction; admission separately unwinds on failure.
    assert transaction.rollback.await_count == 2
    assert events == ["prepare", "lock", "unlock"]
