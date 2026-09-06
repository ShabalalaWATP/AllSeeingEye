"""Secret-bearing admin responses recheck authority after their committed action."""

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from ase.adapters.persistence.models import PasswordTokenRow
from ase.container import Container
from ase.domain.users import AccountRequest, RequestStatus, Role, User
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    FakeClock,
    bearer,
    create_user,
    csrf_headers,
    login_token,
)


class PausedDelivery:
    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def send_link(self, _email, _purpose, _link) -> bool:
        self.entered.set()
        await self.release.wait()
        return False


async def revoke(
    transition: str,
    client: AsyncClient,
    container: Container,
    admin: User,
    clock: FakeClock,
) -> None:
    if transition == "logout":
        assert (
            await client.post("/api/auth/logout", headers=csrf_headers(client))
        ).status_code == 204
    elif transition == "expiry":
        clock.advance(timedelta(minutes=16))
    elif transition == "role_without_version":
        async with container.session_factory() as session:
            users = container.repositories(session).users
            current = await users.get_by_id(admin.id)
            assert current is not None
            current.role = Role.MANAGER
            await users.save(current)
            await session.commit()
    else:
        await create_user(
            container, email="operator@example.com", password=ADMIN_PASSWORD, role=Role.ADMIN
        )
        operator = await login_token(client, "operator@example.com", ADMIN_PASSWORD)
        response = await client.patch(
            f"/api/admin/users/{admin.id}", json={"role": "manager"}, headers=bearer(operator)
        )
        assert response.status_code == 200


@pytest.mark.parametrize("operation", ["approve", "reset"])
@pytest.mark.parametrize("transition", ["demotion", "role_without_version", "logout", "expiry"])
async def test_secret_response_rechecks_original_admin_after_commit(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
    clock: FakeClock,
    monkeypatch,
    operation: str,
    transition: str,
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    pause = PausedDelivery()
    request_id = uuid4()
    target_email = user.email
    if operation == "approve":
        target_email = "candidate@example.com"
        request = AccountRequest(
            request_id,
            target_email,
            "Candidate",
            None,
            RequestStatus.PENDING,
            None,
            None,
            clock.now(),
        )
        async with container.session_factory() as session:
            await container.repositories(session).requests.add(request)
            await session.commit()
        container.email_sender = pause
        path, body = f"/api/admin/account-requests/{request_id}/approve", {"role": "user"}
    else:
        # Reset has no email call. Pause only the hand-off of its real committed result,
        # modelling revocation after its commit await and before response serialisation.
        factory = container.issue_reset_link

        def delayed_factory(session):
            delegate = factory(session)

            class DelayedResult:
                async def execute(self, *args):
                    result = await delegate.execute(*args)
                    pause.entered.set()
                    await pause.release.wait()
                    return result

            return DelayedResult()

        monkeypatch.setattr(container, "issue_reset_link", delayed_factory)
        path, body = f"/api/admin/users/{user.id}/reset-link", None
    pending = asyncio.create_task(client.post(path, json=body, headers=headers))
    try:
        await asyncio.wait_for(pause.entered.wait(), 5)
        await revoke(transition, client, container, admin, clock)
    finally:
        pause.release.set()
    response = await asyncio.wait_for(pending, 5)
    assert response.status_code == (403 if transition == "role_without_version" else 401)
    assert "activation_link" not in response.json() and "reset_link" not in response.json()
    assert "no-store" in response.headers.get("cache-control", "")
    # Returning no secret must not undo or duplicate the already authorised transaction.
    async with container.session_factory() as session:
        repositories = container.repositories(session)
        saved = await repositories.users.get_by_email(target_email)
        assert saved is not None and saved.is_active
        tokens = list(
            await session.scalars(
                select(PasswordTokenRow).where(PasswordTokenRow.user_id == saved.id)
            )
        )
        assert len(tokens) == 1 and tokens[0].used_at is None
        expected_action = "reset_link_issued"
        if operation == "approve":
            decision = await repositories.requests.get(request_id)
            assert decision is not None and decision.status is RequestStatus.APPROVED
            expected_action = "account_request_approved"
        audit = await repositories.audit.list_before(None, 100)
        assert sum(entry.action.value == expected_action for entry in audit) == 1
