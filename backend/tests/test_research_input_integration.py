"""Real app wiring and isolated parser, with synthetic uploads and an isolated test database."""

from uuid import UUID

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token


async def test_real_upload_exceeds_normal_json_cap_without_entering_shared_store(
    client: AsyncClient, container: Container, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    content = b"A synthetic private document passage. " * 2000
    assert len(content) > 64 * 1024
    response = await client.post(
        "/api/research/inputs?filename=private-fixture.txt",
        content=content,
        headers={**bearer(token), "Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 201, response.text
    receipt = response.json()
    stored = container.research_inputs.read(user, UUID(receipt["id"]))
    assert stored.receipt.extracted_characters == len(content)
    assert all(container.store.get(event.id) is None for event in stored.events)
    assert receipt["previews"] == []
