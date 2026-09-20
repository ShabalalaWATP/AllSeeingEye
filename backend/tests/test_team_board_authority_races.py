"""Board mutations and membership revocation must share one transaction guard."""

import asyncio

import pytest

from ase.adapters.persistence.team_board import SqlTeamBoardRepository
from ase.adapters.persistence.teams import SqlTeamRepository
from ase.application.auditing import Auditor
from ase.application.teams.service import TeamService
from ase.container.repositories import build_repositories
from ase.domain.errors import NotFound
from ase.domain.teams import MembershipRole, TeamMembership
from ase.domain.users import Role
from helpers import FakeClock
from test_team_board_concurrency import CONTEXT, NOW, _seed, _services, _user


@pytest.mark.parametrize("action", ["create", "edit", "remove", "pin", "mark_read"])
async def test_membership_removal_waits_for_authorised_board_commit(tmp_path, monkeypatch, action):
    engine, factory, member, team_id, (post_id,) = await _seed(tmp_path, 1)
    admin = _user(Role.ADMIN)
    async with factory() as session:
        repos = build_repositories(session)
        await repos.users.add(admin)
        await SqlTeamRepository(session).put_membership(
            TeamMembership(team_id, admin.id, MembershipRole.MANAGER, NOW)
        )
        await session.commit()

    checked, release = asyncio.Event(), asyncio.Event()
    method = {"create": "add", "mark_read": "put_cursor"}.get(action, "save_if_revision")
    original = getattr(SqlTeamBoardRepository, method)

    async def pause_before_write(self, *args, **kwargs):
        checked.set()
        await release.wait()
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(SqlTeamBoardRepository, method, pause_before_write)

    async def mutate():
        async with factory() as session:
            board, moderation = _services(session)
            if action == "create":
                return await board.create(member, team_id, "Authorised note", None, CONTEXT)
            if action == "edit":
                return await board.edit(member, team_id, post_id, "Authorised edit", 1, CONTEXT)
            if action == "remove":
                return await moderation.remove(member, team_id, post_id, 1, None, CONTEXT)
            if action == "mark_read":
                return await board.mark_read(member, team_id, post_id)
            return await moderation.pin(member, team_id, post_id, True, 1, None, CONTEXT)

    async def revoke():
        async with factory() as session:
            repos = build_repositories(session)
            clock = FakeClock(NOW)
            teams = TeamService(
                SqlTeamRepository(session),
                repos.users,
                clock,
                Auditor(repos.audit, clock),
                repos.uow,
            )
            await teams.remove_member(admin, team_id, member.id, CONTEXT)

    writer = asyncio.create_task(mutate())
    revoker = None
    try:
        await asyncio.wait_for(checked.wait(), 5)
        revoker = asyncio.create_task(revoke())
        # A competing revocation must wait until this already-authorised mutation
        # commits. Without the guard it finishes while the writer is paused here.
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(asyncio.shield(revoker), 0.15)
        release.set()
        await asyncio.wait_for(writer, 5)
        await asyncio.wait_for(revoker, 5)
        with pytest.raises(NotFound):
            await mutate()
    finally:
        release.set()
        await asyncio.gather(writer, *([revoker] if revoker else []), return_exceptions=True)
        await engine.dispose()


async def test_archived_board_still_allows_read_tracking(tmp_path):
    engine, factory, member, team_id, (post_id,) = await _seed(tmp_path, 1)
    try:
        async with factory() as session:
            teams = SqlTeamRepository(session)
            team = await teams.get(team_id)
            team.is_active = False
            await teams.save(team)
            await session.commit()
        async with factory() as session:
            board, _ = _services(session)
            assert await board.mark_read(member, team_id, post_id) == 0
        async with factory() as session:
            cursor = await SqlTeamBoardRepository(session).get_cursor(team_id, member.id)
            assert cursor is not None and cursor.last_read_post_id == post_id
    finally:
        await engine.dispose()
