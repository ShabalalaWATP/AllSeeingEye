"""File-backed SQLite races for board revisions and the pin cap."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.session import create_engine, create_session_factory
from ase.adapters.persistence.team_board import SqlTeamBoardRepository
from ase.adapters.persistence.teams import SqlTeamRepository
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.teams.board import TeamBoardService
from ase.application.teams.board_moderation import TeamBoardModerationService
from ase.container.repositories import build_repositories
from ase.domain.errors import Conflict
from ase.domain.team_board import TeamBoardPost
from ase.domain.teams import MembershipRole, Team, TeamMembership
from ase.domain.users import Role, User
from helpers import FakeClock

NOW = datetime(2026, 9, 15, 9, tzinfo=UTC)
CONTEXT = RequestContext(ip="127.0.0.1")


def _user(role: Role = Role.USER) -> User:
    return User(
        uuid4(),
        f"{uuid4().hex[:8]}@example.com",
        "Analyst",
        role,
        True,
        None,
        0,
        None,
        None,
        NOW,
        None,
    )


async def _seed(
    tmp_path: Path, posts: int
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession], User, UUID, list[UUID]]:
    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'board.db'}")
    factory = create_session_factory(engine)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    manager = _user()
    team_id = uuid4()
    ids = [uuid4() for _ in range(posts)]
    async with factory() as session:
        repos = build_repositories(session)
        await repos.users.add(manager)
        teams = SqlTeamRepository(session)
        await teams.add(Team(team_id, "Race desk", True, manager.id, NOW, NOW))
        await teams.put_membership(TeamMembership(team_id, manager.id, MembershipRole.MANAGER, NOW))
        board = SqlTeamBoardRepository(session)
        for post_id in ids:
            await board.add(TeamBoardPost(post_id, team_id, manager.id, "Note", NOW, NOW))
        await session.commit()
    return engine, factory, manager, team_id, ids


def _services(session: AsyncSession) -> tuple[TeamBoardService, TeamBoardModerationService]:
    repos = build_repositories(session)
    clock = FakeClock(NOW)
    arguments = (
        SqlTeamBoardRepository(session),
        SqlTeamRepository(session),
        repos.users,
        clock,
        Auditor(repos.audit, clock),
        repos.uow,
    )
    return TeamBoardService(*arguments), TeamBoardModerationService(*arguments)


async def test_file_backed_conditional_update_refuses_the_stale_writer(tmp_path: Path) -> None:
    engine, factory, _, _team_id, (post_id,) = await _seed(tmp_path, 1)

    async def attempt(text: str) -> bool:
        async with factory() as session:
            board = SqlTeamBoardRepository(session)
            current = await board.get(post_id)
            assert current is not None
            saved = await board.save_if_revision(replace(current, text=text, revision=2), 1)
            await session.commit()
            return saved

    assert sorted(await asyncio.gather(attempt("First"), attempt("Second"))) == [False, True]
    await engine.dispose()


async def test_file_backed_concurrent_edits_with_one_revision_have_one_winner(
    tmp_path: Path,
) -> None:
    engine, factory, manager, team_id, (post_id,) = await _seed(tmp_path, 1)

    async def edit(text: str) -> str:
        async with factory() as session:
            board, _ = _services(session)
            try:
                await board.edit(manager, team_id, post_id, text, 1, CONTEXT)
                return "saved"
            except Conflict:
                return "conflict"

    outcomes = await asyncio.gather(edit("First"), edit("Second"))
    assert sorted(outcomes) == ["conflict", "saved"]
    async with factory() as session:
        stored = await SqlTeamBoardRepository(session).get(post_id)
    assert stored is not None and stored.revision == 2
    await engine.dispose()


async def test_file_backed_concurrent_pins_cannot_exceed_the_cap(tmp_path: Path) -> None:
    engine, factory, manager, team_id, ids = await _seed(tmp_path, 4)
    async with factory() as session:
        board = SqlTeamBoardRepository(session)
        for post_id in ids[:2]:
            current = await board.get(post_id)
            assert current is not None
            assert await board.save_if_revision(replace(current, is_pinned=True, revision=2), 1)
        await session.commit()

    async def pin(post_id: UUID) -> str:
        async with factory() as session:
            _, moderation = _services(session)
            try:
                await moderation.pin(manager, team_id, post_id, True, 1, None, CONTEXT)
                return "pinned"
            except Conflict:
                return "refused"

    outcomes = await asyncio.gather(pin(ids[2]), pin(ids[3]))
    assert sorted(outcomes) == ["pinned", "refused"]
    async with factory() as session:
        assert await SqlTeamBoardRepository(session).pinned_count(team_id) == 3
    await engine.dispose()
