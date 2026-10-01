"""One saved-report view across origins: filtered, paged and bounded on the server."""

import pytest

import ase.application.reports.access as report_access
from ase.domain.teams import MembershipRole
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from team_helpers import CONTEXT, team_service
from test_report_listing import seed_reports

MIXED = [
    {"origin": "research"},
    {"origin": "subscription"},
    {"origin": "geolocation"},
    {},
    {"research_focus": "media"},
]


async def test_requested_work_lists_every_origin_with_its_label(client, container, user, admin):
    own = await seed_reports(container, user.id, MIXED)
    await seed_reports(container, admin.id, [{"origin": "research"}] * 4)
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    page = (await client.get("/api/reports?group=requested", headers=headers)).json()
    assert [row["id"] for row in page["items"]] == [str(row.id) for row in reversed(own)]
    assert [row["origin"] for row in page["items"]] == [
        "geolocation",
        "research",
        "geolocation",
        "subscription",
        "research",
    ]
    assert page["has_more"] is False


async def test_pages_are_stable_and_complete_across_origins(client, container, user):
    own = await seed_reports(container, user.id, MIXED * 3)
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    seen: list[str] = []
    offset = 0
    while True:
        page = (
            await client.get(
                f"/api/reports?group=requested&limit=4&offset={offset}", headers=headers
            )
        ).json()
        seen.extend(row["id"] for row in page["items"])
        if not page["has_more"]:
            break
        offset += 4
    assert seen == [str(row.id) for row in reversed(own)]


async def test_single_origin_rows_also_carry_their_origin(client, container, user):
    await seed_reports(container, user.id, MIXED)
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    page = (await client.get("/api/reports?origin=geolocation", headers=headers)).json()
    assert {row["origin"] for row in page["items"]} == {"geolocation"}
    assert len(page["items"]) == 2


async def test_discovery_covers_only_the_latest_bounded_window(
    client, container, user, monkeypatch
):
    monkeypatch.setattr(report_access, "DISCOVERY_WINDOW", 5)
    own = await seed_reports(container, user.id, MIXED + MIXED)
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    first = (await client.get("/api/reports?group=requested&limit=3", headers=headers)).json()
    assert len(first["items"]) == 3 and first["has_more"] is True
    last = (
        await client.get("/api/reports?group=requested&limit=3&offset=3", headers=headers)
    ).json()
    assert [row["id"] for row in last["items"]] == [str(own[6].id), str(own[5].id)]
    assert last["has_more"] is False
    beyond = (await client.get("/api/reports?group=requested&offset=5", headers=headers)).json()
    assert beyond["items"] == [] and beyond["has_more"] is False
    # Section views keep reaching older reports.
    section = (await client.get("/api/reports?origin=research&offset=3", headers=headers)).json()
    assert len(section["items"]) == 1


async def test_membership_changes_apply_to_discovery(client, container, user, admin):
    async with team_service(container) as service:
        team = await service.create(admin, "Discovery desk", CONTEXT)
    await seed_reports(container, admin.id, MIXED, team_id=team.id)
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    url = "/api/reports?group=requested"
    assert (await client.get(url, headers=headers)).json()["items"] == []
    async with team_service(container) as service:
        await service.set_member(
            admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
    assert len((await client.get(url, headers=headers)).json()["items"]) == 5
    async with team_service(container) as service:
        await service.remove_member(admin, team.id, user.id, CONTEXT)
    assert (await client.get(url, headers=headers)).json()["items"] == []


@pytest.mark.parametrize("query", ["group=everything", "group=requested&origin=research", "group="])
async def test_invalid_groups_are_rejected(client, user, query):
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    assert (await client.get(f"/api/reports?{query}", headers=headers)).status_code == 422


async def test_requested_work_never_includes_automatic_briefings(client, container, user):
    # KAN-87 briefings are a server-assigned origin; the requested group must leave them out
    # before pagination, while the explicit briefing filter still finds them.
    records = await seed_reports(
        container,
        user.id,
        [{"origin": "research"}] + [{"origin": "briefing", "briefing": "daily"}] * 3,
    )
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    requested = (await client.get("/api/reports?group=requested&limit=1", headers=headers)).json()
    assert [row["id"] for row in requested["items"]] == [str(records[0].id)]
    assert requested["has_more"] is False
    briefings = (await client.get("/api/reports?origin=briefing", headers=headers)).json()
    assert {row["origin"] for row in briefings["items"]} == {"briefing"}
    assert len(briefings["items"]) == 3
