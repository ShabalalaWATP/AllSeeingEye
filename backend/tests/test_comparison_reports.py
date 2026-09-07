"""The comparison chooser reaches older reports with scoped, literal title search."""

from dataclasses import replace
from uuid import uuid4

import pytest

from helpers import USER_PASSWORD, bearer, login_token
from report_documents_helpers import document_records


async def test_paging_reaches_old_reports_and_search_does_not_treat_wildcards_as_code(
    client, container, user, admin
):
    ids = []
    async with container.session_factory() as session:
        repo = container.repositories(session).reports
        for index in range(55):
            report, version = document_records(user.id)
            report = replace(report, title=f"Captured {index:02d} report")
            ids.append(str(report.id))
            await repo.add(report, version)
        for owner, title in [(user.id, "Literal 100%_report"), (admin.id, "Private 100%_report")]:
            report, version = document_records(owner)
            await repo.add(replace(report, title=title), version)
        await session.commit()
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    path = "/api/annotation-comparisons/reports"
    pages = [
        await client.get(path, headers=headers, params={"limit": 20, "offset": offset})
        for offset in (0, 20, 40)
    ]
    assert all(response.status_code == 200 for response in pages)
    all_ids = [row["id"] for response in pages for row in response.json()["items"]]
    assert len(all_ids) == len(set(all_ids)) == 56
    assert set(ids).issubset(all_ids)
    assert all(response.json()["total"] == 56 for response in pages)
    literal = await client.get(path, headers=headers, params={"q": "100%_"})
    assert literal.status_code == 200
    assert literal.json()["total"] == 1
    assert literal.json()["items"][0]["title"] == "Literal 100%_report"
    assert literal.headers["cache-control"] == "private, no-store"
    absent = await client.get(path, headers=headers, params={"q": str(uuid4())})
    assert absent.json()["total"] == 0 and absent.json()["items"] == []


@pytest.mark.parametrize(
    "params", [{"limit": 51}, {"offset": -1}, {"offset": 1000001}, {"q": "x" * 121}]
)
async def test_invalid_chooser_bounds_are_rejected(client, user, params):
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.get(
        "/api/annotation-comparisons/reports", headers=headers, params=params
    )
    assert response.status_code == 422


async def test_chooser_requires_current_authenticated_session(client):
    response = await client.get("/api/annotation-comparisons/reports")
    assert response.status_code == 401
