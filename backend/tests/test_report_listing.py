"""Report sections page their visible records, including legacy origin classification."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.domain.teams import MembershipRole
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from report_documents_helpers import document_records
from team_helpers import CONTEXT, team_service


async def seed_reports(container, owner, scopes, *, team_id=None):
    record, version = document_records(owner)
    records = []
    async with container.session_factory() as session:
        repository = container.repositories(session).reports
        for index, scope in enumerate(scopes):
            item = replace(
                record,
                id=uuid4(),
                title=f"Report {index}",
                scope=scope,
                team_id=team_id,
                created_at=record.created_at + timedelta(minutes=index),
            )
            await repository.add(item, replace(version, id=uuid4(), report_id=item.id))
            records.append(item)
        await session.commit()
    return records


async def test_origin_and_visibility_are_applied_before_pagination(client, container, user, admin):
    own = await seed_reports(
        container,
        user.id,
        [{"origin": "research"}] * 3 + [{"origin": "subscription"}] * 50,
    )
    await seed_reports(container, admin.id, [{"origin": "research"}] * 55)
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    response = await client.get("/api/reports?origin=research&limit=2", headers=headers)
    assert response.status_code == 200
    page = response.json()
    assert [row["id"] for row in page["items"]] == [str(own[2].id), str(own[1].id)]
    assert (page["offset"], page["limit"], page["has_more"]) == (0, 2, True)
    last = (
        await client.get("/api/reports?origin=research&limit=2&offset=2", headers=headers)
    ).json()
    assert [row["id"] for row in last["items"]] == [str(own[0].id)]
    assert (last["offset"], last["has_more"]) == (2, False)
    exhausted = await client.get("/api/reports?origin=research&offset=3", headers=headers)
    assert exhausted.json()["items"] == [] and not exhausted.json()["has_more"]
    unfiltered = (await client.get("/api/reports", headers=headers)).json()
    assert len(unfiltered["items"]) == 50 and unfiltered["has_more"]


async def test_legacy_origins_and_explicit_origin_take_precedence(client, container, user):
    scopes = [
        {},
        {"origin": None},
        {"origin": "unknown"},
        {"research_focus": "media"},
        {"origin": "unknown", "research_focus": "media"},
        {"origin": "research", "research_focus": "media"},
        {"origin": "subscription", "research_focus": "media"},
        {"origin": "geolocation"},
    ]
    records = await seed_reports(container, user.id, scopes)
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    for origin, indices in (
        ("research", [5, 2, 1, 0]),
        ("geolocation", [7, 4, 3]),
        ("subscription", [6]),
    ):
        page = (await client.get(f"/api/reports?origin={origin}", headers=headers)).json()
        assert [row["id"] for row in page["items"]] == [str(records[index].id) for index in indices]
        assert page["has_more"] is False


async def test_every_page_checks_current_team_membership(client, container, user, admin):
    async with team_service(container) as service:
        team = await service.create(admin, "Report desk", CONTEXT)
    await seed_reports(container, admin.id, [{"origin": "research"}] * 3, team_id=team.id)
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    url = "/api/reports?origin=research&limit=1&offset=1"
    assert (await client.get(url, headers=headers)).json()["items"] == []
    async with team_service(container) as service:
        await service.set_member(
            admin,
            team.id,
            email=user.email,
            role=MembershipRole.MEMBER,
            context=CONTEXT,
        )
    visible = (await client.get(url, headers=headers)).json()
    assert len(visible["items"]) == 1 and visible["has_more"]
    async with team_service(container) as service:
        await service.remove_member(admin, team.id, user.id, CONTEXT)
    hidden = (await client.get(url, headers=headers)).json()
    assert hidden["items"] == [] and not hidden["has_more"]


@pytest.mark.parametrize("query", ["origin=unknown", "offset=-1", "limit=0", "limit=201"])
async def test_invalid_pagination_and_origin_are_rejected(client, user, query):
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    assert (await client.get(f"/api/reports?{query}", headers=headers)).status_code == 422
