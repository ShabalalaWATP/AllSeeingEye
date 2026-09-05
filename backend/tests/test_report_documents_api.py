"""Authentication, version lookup and safe binary response headers for report documents."""

from dataclasses import replace
from uuid import uuid4

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token
from report_documents_helpers import document_records


async def test_exports_and_comparison_authentication_versions_headers_and_shared_read_policy(
    client: AsyncClient, container: Container, user: User, admin: User
) -> None:
    record, version = document_records(admin.id)
    record.latest_version = 2
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.reports.add(record, version)
        await repos.reports.add_version(record, replace(version, id=uuid4(), number=2))
        await session.commit()
    root = f"/api/reports/{record.id}"
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    for format, mime in (
        ("pdf", "application/pdf"),
        ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ):
        assert (await client.get(f"{root}/export/{format}")).status_code == 401
        response = await client.get(f"{root}/export/{format}?version=1", headers=bearer(token))
        assert response.status_code == 200, response.text
        assert response.headers["content-type"] == mime
        assert response.headers["cache-control"] == "private, no-store"
        assert (
            response.headers["content-disposition"]
            == f'attachment; filename="report-{record.id}-v1.{format}"'
        )
        assert (
            await client.get(f"{root}/export/{format}?version=9", headers=bearer(token))
        ).status_code == 404
    assert (await client.get(f"{root}/export/pdf", headers=bearer(admin_token))).status_code == 200
    assert (await client.get(f"{root}/export/html", headers=bearer(token))).status_code == 422
    assert (
        await client.get(f"{root}/export/pdf?version=0", headers=bearer(token))
    ).status_code == 422
    assert (await client.get(f"{root}/diff?from_version=1&to_version=2")).status_code == 401
    compared = await client.get(f"{root}/diff?from_version=1&to_version=2", headers=bearer(token))
    assert compared.status_code == 200 and compared.json() == {
        "from_version": 1,
        "to_version": 2,
        "changes": [],
    }
    assert (
        await client.get(f"{root}/diff?from_version=1&to_version=9", headers=bearer(token))
    ).status_code == 404
    assert (
        await client.get(f"{root}/diff?from_version=0&to_version=2", headers=bearer(token))
    ).status_code == 422
