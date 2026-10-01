"""Revocation during a copy and concurrent copies leave no partly accessible team report."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from ase.adapters.persistence.models import ReportRow
from ase.adapters.persistence.report_team_copies import SqlReportTeamCopyRepository
from ase.adapters.persistence.report_team_copy_models import ReportTeamCopyRow
from ase.domain.errors import AppError
from ase.domain.report_team_copy import ReportTeamCopy, copy_for_team, plan_team_copy
from feeds_helpers import NOW
from team_copy_helpers import count, seed_personal, team_with
from team_helpers import CONTEXT, team_service


async def _copy(container, user, record, team, before_save):
    async with container.session_factory() as session:
        current = await container.repositories(session).users.get_by_id(user.id)
        return await container.report_team_copies(session).copy(
            current, record.id, 1, team.id, (), CONTEXT, before_save
        )


async def _concurrent_copy(container, user, record, version, team):
    """Commit the same copy from another transaction, as a racing request would."""
    team_record, team_version = copy_for_team(
        record,
        version,
        report_id=uuid4(),
        version_id=uuid4(),
        team_id=team.id,
        copied_by=user.id,
        now=NOW,
    )
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(team_record, team_version)
        await SqlReportTeamCopyRepository(session).add(
            ReportTeamCopy(
                uuid4(),
                team_record.id,
                team.id,
                record.id,
                version.id,
                version.number,
                user.id,
                NOW,
                plan_team_copy(record, version).content_sha256,
                (),
                (),
            )
        )
        await session.commit()
    return team_record.id


async def test_membership_revoked_during_the_copy_stops_it(container, user, admin):
    team = await team_with(container, admin, user)
    record, _ = await seed_personal(container, user.id, private_input=False)

    async def revoke() -> None:
        async with container.session_factory() as session:
            current = await container.repositories(session).users.get_by_id(admin.id)
        async with team_service(container) as service:
            await service.remove_member(current, team.id, user.id, CONTEXT)

    with pytest.raises(AppError):
        await _copy(container, user, record, team, revoke)
    assert await count(container, select(func.count()).select_from(ReportRow)) == 1
    assert await count(container, select(func.count()).select_from(ReportTeamCopyRow)) == 0


async def test_archive_during_the_copy_stops_it(container, user, admin):
    team = await team_with(container, admin, user)
    record, _ = await seed_personal(container, user.id, private_input=False)

    async def archive() -> None:
        async with container.session_factory() as session:
            current = await container.repositories(session).users.get_by_id(admin.id)
        async with team_service(container) as service:
            await service.update(current, team.id, name=None, is_active=False, context=CONTEXT)

    with pytest.raises(AppError):
        await _copy(container, user, record, team, archive)
    assert await count(container, select(func.count()).select_from(ReportTeamCopyRow)) == 0


async def test_a_concurrent_copy_is_returned_instead_of_a_duplicate(container, user, admin):
    team = await team_with(container, admin, user)
    record, version = await seed_personal(container, user.id, private_input=False)
    winner: list = []

    async def race() -> None:
        winner.append(await _concurrent_copy(container, user, record, version, team))

    result = await _copy(container, user, record, team, race)
    assert result.created is False and result.copy.report_id == winner[0]
    assert await count(container, select(func.count()).select_from(ReportTeamCopyRow)) == 1


async def test_a_unique_conflict_rolls_back_the_losing_copy(container, user, admin, monkeypatch):
    team = await team_with(container, admin, user)
    record, version = await seed_personal(container, user.id, private_input=False)
    original = SqlReportTeamCopyRepository.find
    calls = {"count": 0}

    async def stale_find(self, source_version_id, team_id):
        calls["count"] += 1
        # The second check misses the racing commit, so only the constraint catches it.
        if calls["count"] == 2:
            return None
        return await original(self, source_version_id, team_id)

    monkeypatch.setattr(SqlReportTeamCopyRepository, "find", stale_find)
    winner: list = []

    async def race() -> None:
        winner.append(await _concurrent_copy(container, user, record, version, team))

    result = await _copy(container, user, record, team, race)
    assert result.created is False and result.copy.report_id == winner[0]
    # The source and the winning copy only; the losing team report was rolled back.
    assert await count(container, select(func.count()).select_from(ReportRow)) == 2
