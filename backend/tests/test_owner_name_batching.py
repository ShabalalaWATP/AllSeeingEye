"""Owner labels stay scoped to requested IDs and use bounded, minimal SQL reads."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import event

from ase.container import Container
from ase.domain.users import User


@contextmanager
def user_selects(container: Container) -> Iterator[list[tuple[str, Any]]]:
    statements: list[tuple[str, Any]] = []

    def capture(
        connection: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append((statement, parameters))

    event.listen(container.engine.sync_engine, "before_cursor_execute", capture)
    try:
        yield statements
    finally:
        event.remove(container.engine.sync_engine, "before_cursor_execute", capture)


@pytest.mark.parametrize("count", [1, 50, 200, 401])
async def test_owner_labels_batch_only_requested_display_names(
    container: Container, user: User, count: int
) -> None:
    owners = [
        replace(user, id=uuid4(), email=f"owner-{index}@example.invalid", display_name=str(index))
        for index in range(count)
    ]
    async with container.session_factory() as session:
        repository = container.repositories(session).users
        for owner in owners:
            await repository.add(owner)
        await session.commit()
    async with container.session_factory() as session:
        with user_selects(container) as statements:
            names = await container.access_policy(session).owner_names(
                user, (owner.id for owner in owners for _ in range(2))
            )
    assert names == {owner.id: owner.display_name for owner in owners}
    assert len(statements) == (count + 199) // 200
    for statement, parameters in statements:
        assert "password_hash" not in statement
        assert "security_version" not in statement
        assert len(parameters) <= 200


async def test_empty_and_actor_only_labels_do_not_query(container: Container, user: User) -> None:
    actor = replace(user, display_name="Already authorised actor")
    async with container.session_factory() as session:
        policy = container.access_policy(session)
        with user_selects(container) as statements:
            assert await policy.owner_names(actor, []) == {}
            assert await policy.owner_names(actor, [actor.id, actor.id]) == {
                actor.id: actor.display_name
            }
        assert not statements


async def test_missing_and_inactive_owner_semantics_are_preserved(
    container: Container, user: User
) -> None:
    inactive = replace(
        user,
        id=uuid4(),
        email="inactive@example.invalid",
        display_name="Former owner",
        is_active=False,
    )
    unrelated = replace(user, id=uuid4(), email="unrelated@example.invalid")
    async with container.session_factory() as session:
        repository = container.repositories(session).users
        await repository.add(inactive)
        await repository.add(unrelated)
        await session.commit()
    async with container.session_factory() as session:
        names = await container.access_policy(session).owner_names(
            user, [user.id, inactive.id, uuid4()]
        )
    assert names == {user.id: user.display_name, inactive.id: inactive.display_name}
    assert unrelated.id not in names
