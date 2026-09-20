"""Waiting board writers reload revoked authority after acquiring the shared guard."""

import asyncio

import pytest

from ase.adapters.persistence.teams import SqlTeamRepository
from ase.adapters.persistence.users import SqlUserRepository
from ase.container.repositories import build_repositories
from ase.domain.errors import InvalidRequest, NotFound, Unauthenticated
from test_team_board_concurrency import CONTEXT, _seed, _services


@pytest.mark.parametrize("action", ["create", "edit", "remove", "pin"])
@pytest.mark.parametrize("revocation", ["membership", "security_version", "archive"])
async def test_waiting_board_writer_rechecks_authority(tmp_path, monkeypatch, action, revocation):
    engine, factory, member, team_id, (post_id,) = await _seed(tmp_path, 1)
    reached, release = asyncio.Event(), asyncio.Event()
    original = SqlUserRepository.lock_administration

    async def pause(self):
        if asyncio.current_task().get_name() == "waiting-board":
            reached.set()
            await release.wait()
        await original(self)

    monkeypatch.setattr(SqlUserRepository, "lock_administration", pause)

    async def mutate():
        async with factory() as session:
            board, moderation = _services(session)
            if action == "create":
                return await board.create(member, team_id, "Rejected note", None, CONTEXT)
            if action == "edit":
                return await board.edit(member, team_id, post_id, "Rejected edit", 1, CONTEXT)
            if action == "remove":
                return await moderation.remove(member, team_id, post_id, 1, None, CONTEXT)
            return await moderation.pin(member, team_id, post_id, True, 1, None, CONTEXT)

    pending = asyncio.create_task(mutate(), name="waiting-board")
    try:
        await asyncio.wait_for(reached.wait(), 5)
        async with factory() as session:
            repos = build_repositories(session)
            await repos.users.lock_administration()
            current = await repos.users.lock_by_id(member.id)
            teams = SqlTeamRepository(session)
            team = await teams.get_for_update(team_id)
            if revocation == "membership":
                await teams.remove_membership(team_id, member.id)
            elif revocation == "security_version":
                current.security_version += 1
                await repos.users.save(current)
            else:
                team.is_active = False
                await teams.save(team)
            await session.commit()
        release.set()
        with pytest.raises((NotFound, Unauthenticated, InvalidRequest)):
            await asyncio.wait_for(pending, 5)
    finally:
        release.set()
        await asyncio.gather(pending, return_exceptions=True)
        await engine.dispose()
