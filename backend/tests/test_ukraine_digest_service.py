"""Cadence, retention, metering, administrator refresh and the digest API contract."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from ai_usage_helpers import FakeAccounting
from ase.adapters.persistence.ukraine_digest import SqlUkraineDigestStore
from ase.adapters.security.cipher import FernetCipher
from ase.application.ai_usage_gateway import AllowanceLlmGateway
from ase.application.ports.llm import LlmGatewayError
from ase.application.ukraine_digest import (
    NO_EVIDENCE,
    NO_MODEL,
    RETRY_AFTER,
    DigestStatus,
    UkraineDigestService,
)
from ase.application.ukraine_digest_writer import DigestWriter
from ase.container import Container
from ase.domain.ai_usage import AiAllowanceExceeded, AiAttribution
from ase.domain.errors import Forbidden, RateLimited
from ase.domain.llm import LlmProfile, LlmRole
from ase.domain.ukraine.digest import DIGEST_INTERVAL, DIGEST_RETENTION
from ase.domain.users import Role, User
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    FakeClock,
    bearer,
    login_token,
)
from ukraine_digest_helpers import (
    NOW,
    PERIOD_END,
    FakeAdmission,
    FakeDigestStore,
    FakeRuntime,
    answer,
    board,
    result,
    scripted_gateway,
    service,
)

DIGEST = "/api/conflicts/ukraine/digest"
REFRESH = f"{DIGEST}/refresh"


class Limiter:
    """Counts hits per key so the refresh limits can be exercised without real time."""

    def __init__(self) -> None:
        self.hits: dict[str, int] = {}

    def hit(self, key: str, limit: int, window: int) -> int | None:
        self.hits[key] = self.hits.get(key, 0) + 1
        return None if self.hits[key] <= limit else window


def profile() -> LlmProfile:
    cipher = FernetCipher("a" * 32)
    return LlmProfile(
        id=uuid4(),
        name="Digest fixture",
        base_url="https://model.example/v1",
        model="fixture",
        api_key_encrypted=cipher.encrypt("secret"),
        api_key_hint="cret",
        roles=frozenset({LlmRole.ASSESSMENT}),
        max_output_tokens=4000,
        temperature=0.1,
        enabled=True,
        created_at=NOW,
        updated_at=NOW,
    )


def build(
    *,
    gateway: AsyncMock | None = None,
    with_model: bool = True,
    board_value: object | None = None,
) -> tuple[UkraineDigestService, FakeDigestStore, AsyncMock, FakeAdmission, list, FakeClock]:
    clock = FakeClock(NOW)
    store, admission, audit = FakeDigestStore(), FakeAdmission(), []
    gateway = gateway if gateway is not None else scripted_gateway()
    writer = DigestWriter(gateway, FernetCipher("a" * 32), clock, AsyncMock())
    built = service(
        store=store,
        runtime=FakeRuntime(profile() if with_model else None),
        writer=writer,
        clock=clock,
        limiter=Limiter(),
        admission=admission,
        audit=audit,
        board_value=board_value,  # type: ignore[arg-type]
    )
    return built, store, gateway, admission, audit, clock


def person(role: Role) -> User:
    return User(
        id=uuid4(),
        email=f"{role.value}@example.com",
        display_name=role.value.title(),
        role=role,
        is_active=True,
        password_hash="x",
        failed_login_count=0,
        last_failed_at=None,
        locked_until=None,
        created_at=NOW,
        last_login_at=None,
    )


async def test_one_digest_a_fortnight_is_written_stored_and_reused() -> None:
    digest, store, gateway, admission, _audit, _clock = build()
    await digest.generate()
    assert gateway.complete.await_count == 1 and len(store.saved) == 1
    assert admission.entered == 1
    stored = store.saved[0]
    assert (stored.period_end, stored.model) == (PERIOD_END, "fixture-model")
    assert (stored.prompt_tokens, stored.completion_tokens) == (900, 300)
    assert stored.source_ids and stored.evidence_items > 0
    view = await digest.view()
    assert (view.status, view.stale, view.generating) == (DigestStatus.READY, False, False)
    assert view.interval_days == DIGEST_INTERVAL.days
    # Reading again inside the fortnight starts no further model work.
    await digest.view()
    await digest.drain()
    assert gateway.complete.await_count == 1


async def test_a_reader_after_the_fortnight_starts_exactly_one_generation() -> None:
    digest, store, gateway, _admission, _audit, clock = build()
    await digest.generate()
    clock.advance(DIGEST_INTERVAL + timedelta(minutes=1))
    stale = await digest.view()
    assert stale.stale is True and stale.latest is not None
    second = await digest.view()
    assert second.generating is True
    await digest.drain()
    assert gateway.complete.await_count == 2 and len(store.saved) == 2
    assert (await digest.view()).previous[0].generated_at == store.saved[1].generated_at


async def test_only_the_newest_digests_are_kept() -> None:
    digest, store, _gateway, _admission, _audit, clock = build()
    for _ in range(DIGEST_RETENTION + 3):
        await digest.generate()
        clock.advance(DIGEST_INTERVAL)
    assert len(store.saved) == DIGEST_RETENTION
    view = await digest.view()
    assert len(view.previous) == DIGEST_RETENTION - 1


async def test_no_model_is_an_honest_empty_state_that_is_not_retried_immediately() -> None:
    digest, store, gateway, _admission, _audit, clock = build(with_model=False)
    await digest.generate()
    view = await digest.view()
    assert (view.status, view.reason, view.latest) == (DigestStatus.UNAVAILABLE, NO_MODEL, None)
    assert store.saved == [] and gateway.complete.await_count == 0
    await digest.view()
    await digest.drain()
    assert gateway.complete.await_count == 0
    clock.advance(RETRY_AFTER + timedelta(minutes=1))
    await digest.view()
    await digest.drain()
    assert gateway.complete.await_count == 0


async def test_nothing_collected_in_the_fortnight_says_so_rather_than_calling_a_model() -> None:
    digest, store, gateway, _admission, _audit, _clock = build(
        board_value=board(updates=(), claims=())
    )
    await digest.generate()
    view = await digest.view()
    assert (view.status, view.reason) == (DigestStatus.UNAVAILABLE, NO_EVIDENCE)
    assert gateway.complete.await_count == 0 and store.saved == []


async def test_an_exhausted_allowance_is_reported_without_storing_anything() -> None:
    gateway = AsyncMock()
    gateway.complete.side_effect = AiAllowanceExceeded()
    digest, store, _gateway, _admission, _audit, _clock = build(gateway=gateway)
    await digest.generate()
    view = await digest.view()
    assert view.status is DigestStatus.UNAVAILABLE
    assert "allowance is exhausted" in (view.reason or "")
    assert store.saved == []


async def test_a_provider_failure_is_reported_without_storing_anything() -> None:
    gateway = AsyncMock()
    gateway.complete.side_effect = LlmGatewayError("down")
    digest, store, _gateway, _admission, _audit, _clock = build(gateway=gateway)
    await digest.generate()
    assert (await digest.view()).status is DigestStatus.UNAVAILABLE
    assert store.saved == []


async def test_an_answer_that_fails_the_checks_twice_stores_nothing_and_says_so() -> None:
    gateway = AsyncMock()
    gateway.complete.return_value = result(answer(ids=("e99",)))
    digest, store, _gateway, admission, _audit, _clock = build(gateway=gateway)
    await digest.generate()
    view = await digest.view()
    assert view.status is DigestStatus.VALIDATION_FAILED
    assert "nothing was saved" in (view.reason or "")
    assert store.saved == [] and admission.entered == 0


async def test_the_administrator_refresh_is_authorised_audited_and_rate_limited() -> None:
    digest, _store, gateway, _admission, audit, _clock = build()
    gateway.complete.return_value = result(answer())
    with pytest.raises(Forbidden):
        await digest.refresh(person(Role.USER), "203.0.113.1")
    assert audit == []
    operator = person(Role.ADMIN)
    view = await digest.refresh(operator, "203.0.113.2")
    assert view.generating is True
    assert audit == [(operator.id, "203.0.113.2")]
    await digest.drain()
    await digest.refresh(operator, None)
    await digest.drain()
    with pytest.raises(RateLimited):
        await digest.refresh(operator, None)
    assert len(audit) == 2


async def test_the_model_call_is_metered_as_system_work() -> None:
    accounting = FakeAccounting()
    inner = AsyncMock()
    inner.complete.return_value = result(answer())
    metered = AllowanceLlmGateway(
        inner,
        accounting,  # type: ignore[arg-type]
        attribution=AiAttribution.system_work(),
        profile_id=None,
        purpose_prefix="system",
        strict=False,
    )
    digest, store, _gateway, _admission, _audit, _clock = build()
    digest._writer = DigestWriter(  # type: ignore[attr-defined]
        metered, FernetCipher("a" * 32), FakeClock(NOW), AsyncMock()
    )
    await digest.generate()
    assert len(store.saved) == 1
    attribution, kwargs = accounting.reserved[0]
    assert attribution == AiAttribution.system_work()
    assert kwargs["purpose"] == "system:ukraine_digest"
    assert kwargs["requested_tokens"] > 0


async def test_the_store_keeps_only_the_newest_rows_and_reads_them_back(
    container: Container,
) -> None:
    store = SqlUkraineDigestStore(container.session_factory)
    digest, _memory, _gateway, _admission, _audit, clock = build()
    digest._store = store  # type: ignore[attr-defined]
    for _ in range(DIGEST_RETENTION + 2):
        await digest.generate()
        clock.advance(DIGEST_INTERVAL)
    rows = await store.recent(DIGEST_RETENTION + 5)
    assert len(rows) == DIGEST_RETENTION
    assert rows[0].generated_at > rows[-1].generated_at
    assert rows[0].digest.battlefield.changes[0].source_ids == ["e1"]
    assert {item.id for item in rows[0].citations} == {"e1", "e3", "e6", "e7"}


async def test_the_digest_endpoint_needs_a_session_and_reports_an_honest_empty_state(
    app: FastAPI, client: AsyncClient, container: Container, user: User
) -> None:
    assert (await client.get(DIGEST)).status_code == 401
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    first = await client.get(DIGEST, headers=headers)
    assert first.status_code == 200
    assert first.headers["Cache-Control"] == "private, no-store"
    await container.ukraine_digest.drain()
    body = (await client.get(DIGEST, headers=headers)).json()
    assert body["status"] == "unavailable" and body["reason"] == NO_MODEL
    assert body["latest"] is None and body["previous"] == []
    assert body["interval_days"] == DIGEST_INTERVAL.days


async def test_only_administrators_may_force_a_refresh_and_it_is_audited(
    client: AsyncClient, container: Container, user: User, admin: User
) -> None:
    reader = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    assert (await client.post(REFRESH, headers=reader)).status_code == 403
    operator = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    response = await client.post(REFRESH, headers=operator)
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    await container.ukraine_digest.drain()
    async with container.session_factory() as session:
        entries = await container.repositories(session).audit.list_before(None, 20)
    assert any(entry.action.value == "ukraine_digest_refresh_requested" for entry in entries)
