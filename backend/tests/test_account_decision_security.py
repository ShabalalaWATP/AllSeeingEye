"""Account decisions reject stale reviewers and preserve one authoritative outcome."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select

from ase.adapters.persistence.models import AccountRequestRow, PasswordTokenRow
from ase.application.dto import ApprovalResult
from ase.container import Container
from ase.domain.errors import AlreadyDecided, Forbidden
from ase.domain.tokens import TokenPurpose
from ase.domain.users import AccountRequest, RequestStatus, Role
from helpers import ADMIN_PASSWORD, create_user
from token_race_helpers import CONTEXT
from token_race_helpers import race_container as race_container  # noqa: PLC0414


async def pending(container: Container) -> AccountRequest:
    request = AccountRequest(
        id=uuid4(),
        email="candidate@example.com",
        display_name="Candidate",
        reason=None,
        status=RequestStatus.PENDING,
        decided_by=None,
        decided_at=None,
        created_at=container.clock.now(),
    )
    async with container.session_factory() as session:
        await container.repositories(session).requests.add(request)
        await session.commit()
    return request


@pytest.mark.parametrize("approve", [True, False])
@pytest.mark.parametrize("deactivate", [True, False])
async def test_stale_reviewer_cannot_decide_after_role_or_status_change(
    race_container: Container,
    approve: bool,
    deactivate: bool,
) -> None:
    container = race_container
    first = await create_user(
        container, email="first@example.com", password=ADMIN_PASSWORD, role=Role.ADMIN
    )
    second = await create_user(
        container, email="second@example.com", password=ADMIN_PASSWORD, role=Role.ADMIN
    )
    request = await pending(container)
    async with container.session_factory() as session:
        await container.update_user(session).execute(
            first,
            second.id,
            None if deactivate else Role.USER,
            False if deactivate else None,
            CONTEXT,
        )
    async with container.session_factory() as session:
        with pytest.raises(Forbidden):
            if approve:
                await container.approve_request(session).execute(
                    second, request.id, Role.ADMIN, CONTEXT
                )
            else:
                await container.reject_request(session).execute(second, request.id, None, CONTEXT)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        current = await repos.requests.get(request.id)
        assert current and current.status is RequestStatus.PENDING
        assert await repos.users.get_by_email(request.email) is None
        assert await session.scalar(select(PasswordTokenRow)) is None


@pytest.mark.parametrize("decisions", [(True, True), (True, False), (False, False)])
async def test_competing_account_decisions_have_one_consistent_result(
    race_container: Container,
    decisions: tuple[bool, bool],
) -> None:
    container = race_container
    admin = await create_user(
        container, email="reviewer@example.com", password=ADMIN_PASSWORD, role=Role.ADMIN
    )
    request = await pending(container)
    barrier = asyncio.Barrier(2)

    async def decide(approve: bool) -> ApprovalResult | None:
        async with container.session_factory() as session:
            # Keep a stale ORM row alive, as a long-lived request/session could.
            stale = await session.get(AccountRequestRow, request.id)
            assert stale and stale.status == "pending"
            await barrier.wait()
            if approve:
                return await container.approve_request(session).execute(
                    admin, request.id, Role.USER, CONTEXT
                )
            await container.reject_request(session).execute(admin, request.id, None, CONTEXT)
            return None

    outcomes = await asyncio.wait_for(
        asyncio.gather(
            *(decide(approve) for approve in decisions),
            return_exceptions=True,
        ),
        15,
    )
    assert sum(isinstance(result, AlreadyDecided) for result in outcomes) == 1, outcomes
    assert sum(result is None or isinstance(result, ApprovalResult) for result in outcomes) == 1
    async with container.session_factory() as session:
        repos = container.repositories(session)
        current = await repos.requests.get(request.id)
        assert current
        user = await repos.users.get_by_email(request.email)
        tokens = list(await session.scalars(select(PasswordTokenRow)))
        if current.status is RequestStatus.APPROVED:
            assert user and len(tokens) == 1 and tokens[0].user_id == user.id
        else:
            assert current.status is RequestStatus.REJECTED and user is None and not tokens


async def test_stale_credential_version_cannot_approve(race_container: Container) -> None:
    container = race_container
    admin = await create_user(
        container, email="reviewer@example.com", password=ADMIN_PASSWORD, role=Role.ADMIN
    )
    request = await pending(container)
    async with container.session_factory() as session:
        users = container.repositories(session).users
        changed = await users.lock_by_id(admin.id)
        assert changed
        changed.security_version += 1
        await users.save(changed)
        await session.commit()
    async with container.session_factory() as session:
        with pytest.raises(Forbidden):
            await container.approve_request(session).execute(admin, request.id, Role.ADMIN, CONTEXT)


async def test_delivery_runs_after_atomic_approval_without_database_locks(
    race_container: Container,
) -> None:
    container = race_container
    admin = await create_user(
        container, email="reviewer@example.com", password=ADMIN_PASSWORD, role=Role.ADMIN
    )
    request = await pending(container)

    class InspectingSender:
        async def send_link(self, email: str, purpose: TokenPurpose, link: str) -> bool:
            assert email == request.email and purpose is TokenPurpose.ACTIVATION
            async with asyncio.timeout(3), container.session_factory() as observer:
                repos = container.repositories(observer)
                await repos.users.lock_administration()
                current = await repos.requests.get(request.id)
                assert current and current.status is RequestStatus.APPROVED
                assert await repos.users.get_by_email(request.email)
                assert await observer.scalar(select(PasswordTokenRow))
                entries = await repos.audit.list_before(None, 10)
                assert any(entry.action.value == "account_request_approved" for entry in entries)
                await observer.commit()
            return False

    container.email_sender = InspectingSender()
    async with container.session_factory() as session:
        result = await container.approve_request(session).execute(
            admin, request.id, Role.USER, CONTEXT
        )
        assert result.activation_link
