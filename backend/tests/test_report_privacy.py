"""Personal reports never leak through alternate read/export/search routes."""

import pytest
from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from helpers import USER_PASSWORD, bearer, login_token
from report_search_helpers import add_report


@pytest.mark.parametrize(
    "suffix",
    [
        "",
        "?version=1",
        "/markdown",
        "/export/pdf",
        "/export/docx",
        "/diff?from_version=1&to_version=1",
    ],
)
async def test_private_report_alternate_reads_denied(
    client: AsyncClient, container: Container, admin: User, user: User, suffix: str
) -> None:
    async with container.session_factory() as session:
        record, _ = await add_report(container, session, admin, "Private analyst question")
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.get(f"/api/reports/{record.id}{suffix}", headers=headers)
    assert response.status_code == 404
    assert "Private analyst question" not in response.text


async def test_private_reports_filtered_before_limit_and_search_counts(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    async with container.session_factory() as session:
        own, _ = await add_report(container, session, user)
        await add_report(container, session, admin, "Private report")
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.get("/api/reports?limit=1", headers=headers)
    assert [item["id"] for item in response.json()["items"]] == [str(own.id)]
    response = await client.get("/api/report-search", headers=headers)
    assert response.json()["total"] == 1
