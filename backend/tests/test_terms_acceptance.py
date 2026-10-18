"""Account requests must accept the Terms, approval carries that over, and accounts accept
again on their next visit after a version change."""

from __future__ import annotations

from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from ase.adapters.persistence.models import AccountRequestRow, AuditLogRow
from ase.application.auth import terms as terms_module
from ase.container import Container
from ase.domain.terms import CURRENT_TERMS_VERSION
from ase.domain.users import User
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    FakeClock,
    bearer,
    csrf_headers,
    login_token,
)

REQUEST = {"email": "newcomer@example.com", "display_name": "New Comer"}
ACCEPTANCE = "/api/me/terms-acceptance"


async def _count(container: Container, model: type, *conditions: object) -> int:
    async with container.session_factory() as session:
        return int(await session.scalar(select(func.count()).select_from(model).where(*conditions)))


@pytest.mark.parametrize("terms", [{}, {"accept_terms": False}])
async def test_request_without_acceptance_is_refused_by_the_api(
    client: AsyncClient, container: Container, user: User, terms: dict[str, bool]
) -> None:
    # A new address and an existing account's address get the same field error.
    for email in ("newcomer@example.com", USER_EMAIL):
        response = await client.post(
            "/api/auth/request-account", json={**REQUEST, "email": email, **terms}
        )
        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "validation_error"
        assert set(error["fields"]) == {"accept_terms"}
    assert await _count(container, AccountRequestRow) == 0
    assert await _count(container, AuditLogRow, AuditLogRow.action == "account_requested") == 0


async def test_request_records_acceptance_and_approval_carries_it_to_the_account(
    client: AsyncClient, container: Container, admin: User, clock: FakeClock
) -> None:
    requested_at = clock.now()
    response = await client.post(
        "/api/auth/request-account", json={**REQUEST, "accept_terms": True}
    )
    assert response.status_code == 202
    clock.advance(timedelta(hours=2))
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    listed = (await client.get("/api/admin/account-requests", headers=bearer(token))).json()
    [item] = listed["items"]
    assert item["terms_version"] == CURRENT_TERMS_VERSION
    assert item["terms_accepted_at"].startswith(requested_at.isoformat()[:19])
    approved = await client.post(
        f"/api/admin/account-requests/{item['id']}/approve", json={}, headers=bearer(token)
    )
    assert approved.status_code == 200
    terms = approved.json()["user"]["terms"]
    assert terms["accepted_version"] == CURRENT_TERMS_VERSION
    assert terms["accepted_at"] == item["terms_accepted_at"]
    assert terms["acceptance_required"] is False
    async with container.session_factory() as session:
        stored = await container.repositories(session).users.get_by_email(REQUEST["email"])
    assert stored is not None and stored.terms_accepted_at == requested_at


async def test_an_account_without_acceptance_must_accept_and_repeats_change_nothing(
    client: AsyncClient, container: Container, user: User, clock: FakeClock
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    me = (await client.get("/api/me", headers=bearer(token))).json()
    assert me["terms"] == {
        "current_version": CURRENT_TERMS_VERSION,
        "accepted_version": None,
        "accepted_at": None,
        "acceptance_required": True,
    }
    accepted_at = clock.now()
    response = await client.post(
        ACCEPTANCE, json={"version": CURRENT_TERMS_VERSION}, headers=bearer(token)
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["acceptance_required"] is False
    clock.advance(timedelta(minutes=5))
    again = await client.post(
        ACCEPTANCE, json={"version": CURRENT_TERMS_VERSION}, headers=bearer(token)
    )
    assert again.json() == response.json()
    me = (await client.get("/api/me", headers=bearer(token))).json()
    assert me["terms"]["acceptance_required"] is False
    async with container.session_factory() as session:
        stored = await container.repositories(session).users.get_by_id(user.id)
        audit = (
            await session.scalars(select(AuditLogRow).where(AuditLogRow.action == "terms_accepted"))
        ).all()
    assert stored is not None and stored.terms_accepted_at == accepted_at
    assert [(row.actor_user_id, row.details) for row in audit] == [
        (user.id, {"terms_version": CURRENT_TERMS_VERSION, "previous_version": None})
    ]


async def test_a_version_change_asks_again_and_refuses_a_stale_acceptance(
    client: AsyncClient, container: Container, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await client.post(ACCEPTANCE, json={"version": CURRENT_TERMS_VERSION}, headers=bearer(token))
    monkeypatch.setattr(terms_module, "CURRENT_TERMS_VERSION", "2099-01-01")
    me = (await client.get("/api/me", headers=bearer(token))).json()
    assert me["terms"]["current_version"] == "2099-01-01"
    assert me["terms"]["accepted_version"] == CURRENT_TERMS_VERSION
    assert me["terms"]["acceptance_required"] is True
    stale = await client.post(
        ACCEPTANCE, json={"version": CURRENT_TERMS_VERSION}, headers=bearer(token)
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "conflict"
    current = await client.post(ACCEPTANCE, json={"version": "2099-01-01"}, headers=bearer(token))
    assert current.json()["accepted_version"] == "2099-01-01"
    assert await _count(container, AuditLogRow, AuditLogRow.action == "terms_accepted") == 2


async def test_acceptance_needs_a_live_session_and_strict_input(
    client: AsyncClient, user: User
) -> None:
    body = {"version": CURRENT_TERMS_VERSION}
    assert (await client.post(ACCEPTANCE, json=body)).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    extra = await client.post(ACCEPTANCE, json={**body, "user_id": "x"}, headers=bearer(token))
    assert extra.status_code == 422
    await client.post("/api/auth/logout", headers=csrf_headers(client))
    ended = await client.post(ACCEPTANCE, json=body, headers=bearer(token))
    assert ended.status_code == 401
