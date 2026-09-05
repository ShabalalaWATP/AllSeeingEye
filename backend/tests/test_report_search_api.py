"""Authenticated semantic search API with a fake embeddings endpoint."""

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from helpers import bearer
from report_search_helpers import FakeEmbeddings, add_profile, add_report


async def test_search_api_auth_validation_index_query_and_usage(
    client: AsyncClient, container: Container, user: User
) -> None:
    assert (await client.get("/api/report-search")).status_code == 401
    assert (await client.post("/api/report-search/index")).status_code == 401
    assert (await client.post("/api/report-search/query", json={"query": "x"})).status_code == 401
    headers = bearer(container.issuer.issue(user).token)
    status = await client.get("/api/report-search", headers=headers)
    assert status.status_code == 200 and not status.json()["available"]
    unavailable = await client.post("/api/report-search/index", headers=headers)
    assert unavailable.status_code == 409 and unavailable.json()["error"]["code"] == "no_model"
    for body in (
        {"query": "  "},
        {"query": "x" * 501},
        {"query": "x", "limit": 21},
        {"query": "x", "url": "http://private"},
    ):
        assert (
            await client.post("/api/report-search/query", headers=headers, json=body)
        ).status_code == 422
    container.embedding_gateway = FakeEmbeddings()
    async with container.session_factory() as session:
        await add_profile(container, session)
        record, _ = await add_report(container, session, user)
    index = await client.post("/api/report-search/index", headers=headers)
    assert index.status_code == 200 and index.json()["indexed"] == 1
    found = await client.post(
        "/api/report-search/query", headers=headers, json={"query": "Merchant shipping"}
    )
    assert found.status_code == 200
    assert found.json()["items"][0]["report"]["id"] == str(record.id)
    assert found.json()["items"][0]["score"] == 1
    assert "vector" not in found.text and "test-key" not in found.text
