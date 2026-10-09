"""Search and index bind slow work to the session that admitted the request."""

from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from ase.adapters.persistence.report_search import ReportEmbeddingRow, SqlReportEmbeddingRepository
from ase.application.reports import search
from ase.container import Container
from ase.domain.users import User
from helpers import USER_PASSWORD, FakeClock, bearer, login_token
from report_search_helpers import FakeEmbeddings, add_profile, add_report


@pytest.mark.parametrize("operation", ["index", "query"])
@pytest.mark.parametrize("end_session", ["logout", "revoke", "expire", "new_session"])
async def test_search_refuses_session_ended_during_embeddings(
    client: AsyncClient,
    container: Container,
    user: User,
    clock: FakeClock,
    operation: str,
    end_session: str,
) -> None:
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    gateway = FakeEmbeddings()
    container.embedding_gateway = gateway
    async with container.session_factory() as session:
        await add_profile(container, session)
        record, _ = await add_report(container, session, user, title="Private search evidence")
    if operation == "query":
        assert (await client.post("/api/report-search/index", headers=headers)).status_code == 200
    family = (await client.get("/api/me/sessions", headers=headers)).json()["items"][0]["id"]

    async def end() -> None:
        if end_session == "expire":
            clock.advance(timedelta(minutes=container.settings.access_token_minutes))
        elif end_session == "logout":
            response = await client.post(
                "/api/auth/logout", headers={"X-CSRF-Token": client.cookies["ase_csrf"]}
            )
            assert response.status_code == 204
        else:
            response = await client.delete(f"/api/me/sessions/{family}", headers=headers)
            assert response.status_code == 204
            if end_session == "new_session":
                replacement = await login_token(client, user.email, USER_PASSWORD)
                assert (
                    await client.get("/api/me/sessions", headers=bearer(replacement))
                ).status_code == 200

    gateway.during_call = end
    response = await client.post(
        f"/api/report-search/{operation}",
        headers=headers,
        **({"json": {"query": "Private search"}} if operation == "query" else {}),
    )
    assert response.status_code == 401
    assert str(record.id) not in response.text
    assert "Private search evidence" not in response.text
    async with container.session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(ReportEmbeddingRow))
        assert count == int(operation == "query")
    assert (await client.get("/api/me/sessions", headers=headers)).status_code == 401


@pytest.mark.parametrize("operation", ["index", "query"])
async def test_search_preserves_same_family_refresh_during_embeddings(
    client: AsyncClient, container: Container, user: User, operation: str
) -> None:
    token = await login_token(client, user.email, USER_PASSWORD)
    headers = bearer(token)
    gateway = FakeEmbeddings()
    container.embedding_gateway = gateway
    async with container.session_factory() as session:
        await add_profile(container, session)
        record, _ = await add_report(container, session, user)
    if operation == "query":
        assert (await client.post("/api/report-search/index", headers=headers)).status_code == 200

    async def refresh() -> None:
        response = await client.post(
            "/api/auth/refresh", headers={"X-CSRF-Token": client.cookies["ase_csrf"]}
        )
        assert response.status_code == 200
        original = container.issuer.verify(token)
        renewed = container.issuer.verify(response.json()["access_token"])
        assert original.family_id == renewed.family_id

    gateway.during_call = refresh
    response = await client.post(
        f"/api/report-search/{operation}",
        headers=headers,
        **({"json": {"query": "Maritime"}} if operation == "query" else {}),
    )
    assert response.status_code == 200
    assert response.json()["indexed"] == 1
    if operation == "query":
        assert response.json()["items"][0]["report"]["id"] == str(record.id)


async def test_search_checks_expiry_after_threaded_ranking(
    client: AsyncClient,
    container: Container,
    user: User,
    clock: FakeClock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    container.embedding_gateway = FakeEmbeddings()
    async with container.session_factory() as session:
        await add_profile(container, session)
        await add_report(container, session, user)
    assert (await client.post("/api/report-search/index", headers=headers)).status_code == 200
    ranked = search.ranked

    def expired_ranking(*args):
        result = ranked(*args)
        clock.advance(timedelta(minutes=container.settings.access_token_minutes))
        return result

    monkeypatch.setattr(search, "ranked", expired_ranking)
    response = await client.post(
        "/api/report-search/query", headers=headers, json={"query": "Maritime"}
    )
    assert response.status_code == 401


async def test_index_does_not_commit_vectors_if_token_expires_during_persistence(
    client: AsyncClient,
    container: Container,
    user: User,
    clock: FakeClock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    container.embedding_gateway = FakeEmbeddings()
    async with container.session_factory() as session:
        await add_profile(container, session)
        await add_report(container, session, user)
    save = SqlReportEmbeddingRepository.save

    async def expiry_after_save(repository, entry):
        result = await save(repository, entry)
        clock.advance(timedelta(minutes=container.settings.access_token_minutes))
        return result

    monkeypatch.setattr(SqlReportEmbeddingRepository, "save", expiry_after_save)
    response = await client.post("/api/report-search/index", headers=headers)
    assert response.status_code == 401
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(ReportEmbeddingRow)) == 0
