"""Shared report reading does not grant permission to overwrite another owner's product."""

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token
from report_documents_helpers import document_records


async def test_other_user_can_read_but_cannot_regenerate_an_admin_report(
    client: AsyncClient,
    container: Container,
    user: User,
    admin: User,
) -> None:
    record, version = document_records(admin.id)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    root = f"/api/reports/{record.id}"
    assert (await client.get(root, headers=headers)).status_code == 200
    denied = await client.post(f"{root}/versions", headers=headers)
    assert denied.status_code == 403
    assert (await client.get(root, headers=headers)).json()["report"]["latest_version"] == 1
    async with container.session_factory() as session:
        assert await container.repositories(session).llm_usage.list_recent(10) == []
    # The owner passes the object gate and reaches the missing-model check.
    owner = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    assert (await client.post(f"{root}/versions", headers=owner)).status_code == 409
