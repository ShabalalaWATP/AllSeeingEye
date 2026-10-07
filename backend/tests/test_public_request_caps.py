"""Installation-wide caps on account and reset requests, and a bounded review queue."""

from __future__ import annotations

from dataclasses import replace

import pytest
from httpx import AsyncClient

from ase.application.dto import RequestContext
from ase.container import Container
from ase.domain.audit import AuditAction
from ase.domain.errors import RateLimited
from ase.domain.users import RequestStatus
from helpers import USER_EMAIL


def _context(index: int) -> RequestContext:
    return RequestContext(ip=f"203.0.113.{index + 1}")


async def _request_account(container: Container, email: str, index: int) -> None:
    async with container.session_factory() as session:
        await container.request_account(session).execute(email, "Requester", None, _context(index))


async def test_request_account_global_cap_applies_across_clients(container: Container) -> None:
    container.limits = replace(container.limits, request_account_global=3)
    for index in range(3):
        await _request_account(container, f"person{index}@example.com", index)
    with pytest.raises(RateLimited) as refused:
        await _request_account(container, "person-late@example.com", 50)
    assert refused.value.retry_after == container.limits.hourly_window_seconds


async def test_forgot_password_global_cap_applies_across_clients(container: Container) -> None:
    container.limits = replace(container.limits, forgot_global=2)
    for index in range(2):
        async with container.session_factory() as session:
            await container.forgot_password(session).execute(
                f"reset{index}@example.com", _context(index), send_email=False
            )
    async with container.session_factory() as session:
        with pytest.raises(RateLimited):
            await container.forgot_password(session).execute(
                "reset-late@example.com", _context(60), send_email=False
            )


async def test_full_review_queue_stores_nothing_and_answers_uniformly(
    client: AsyncClient, container: Container
) -> None:
    container.limits = replace(container.limits, pending_account_requests_max=2)
    accepted = await client.post(
        "/api/auth/request-account",
        json={"email": "first@example.com", "display_name": "First"},
    )
    await _request_account(container, "second@example.com", 1)
    queued_out = await client.post(
        "/api/auth/request-account",
        json={"email": "third@example.com", "display_name": "Third"},
    )
    assert accepted.status_code == queued_out.status_code == 202
    assert accepted.json() == queued_out.json()
    async with container.session_factory() as session:
        repos = container.repositories(session)
        pending = await repos.requests.list_by_status(RequestStatus.PENDING)
        assert sorted(item.email for item in pending) == [
            "first@example.com",
            "second@example.com",
        ]
        assert await repos.requests.count_pending() == 2
        entries = await repos.audit.list_before(None, 20)
    requested = [entry for entry in entries if entry.action is AuditAction.ACCOUNT_REQUESTED]
    by_subject = {entry.subject: entry.details for entry in requested}
    assert by_subject["third@example.com"] == {"duplicate": False, "queue_full": True}
    assert by_subject["first@example.com"] == {"duplicate": False, "queue_full": False}


async def test_full_queue_and_existing_accounts_look_the_same(
    client: AsyncClient, container: Container, user: object
) -> None:
    container.limits = replace(container.limits, pending_account_requests_max=1)
    await _request_account(container, "only@example.com", 2)
    existing = await client.post(
        "/api/auth/request-account", json={"email": USER_EMAIL, "display_name": "Existing"}
    )
    dropped = await client.post(
        "/api/auth/request-account", json={"email": "new@example.com", "display_name": "New"}
    )
    assert existing.status_code == dropped.status_code == 202
    assert existing.json() == dropped.json()
