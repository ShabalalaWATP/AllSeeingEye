"""The bell lists the caller's own and current teams' alerts from the same seven days as Alerts."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from bell_helpers import BELL, add_alerts, desk_headers, make_alert
from board_subject_helpers import seed_report
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from team_helpers import CONTEXT, team_service
from warning_scope_helpers import WarningActors, create_indicator
from warning_scope_helpers import warning_actors as warning_actors  # noqa: PLC0414


async def _bell(client: AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    response = await client.get(BELL, headers=headers)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    body: dict[str, Any] = response.json()
    return body


async def test_bell_counts_mine_and_my_teams_in_seven_days_before_the_limit(
    client: AsyncClient, container: Container, admin: User, warning_actors: WarningActors
) -> None:
    actors = warning_actors
    headers = await desk_headers(client, actors)
    team = actors.team.id
    mine = make_alert(container, actors.owner.id, hours_ago=30, title="Mine")
    older = make_alert(container, actors.owner.id, hours_ago=24 * 8, title="Too old")
    shared = [make_alert(container, actors.peer.id, team, hours_ago=i + 1) for i in range(6)]
    done = make_alert(container, actors.peer.id, team, acknowledged=True, title="Done")
    foreign = make_alert(container, actors.outsider.id, actors.other.id, title="Foreign")
    private = make_alert(container, actors.peer.id, title="Peer private")
    await add_alerts(container, mine, older, *shared, done, foreign, private)

    body = await _bell(client, headers["owner"])
    assert body["window_days"] == 7
    alerts = body["alerts"]
    # Six team alerts and the owner's own; nothing older, acknowledged or out of scope.
    assert alerts["total"] == 7 and alerts["muted"] is False
    assert [item["id"] for item in alerts["items"]] == [str(item.id) for item in shared[:5]]
    assert all(item["can_acknowledge"] for item in alerts["items"])
    assert alerts["items"][0]["team_name"] == "Warning desk"

    outsider = (await _bell(client, headers["outsider"]))["alerts"]
    assert outsider["total"] == 1 and outsider["items"][0]["id"] == str(foreign.id)

    # The administrator's bell stays on Mine and my teams, never everyone's records.
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    own = make_alert(container, admin.id, title="Admin own")
    await add_alerts(container, own)
    admin_bell = (await _bell(client, admin_headers))["alerts"]
    ids = {item["id"] for item in admin_bell["items"]}
    assert str(private.id) not in ids and str(mine.id) not in ids
    assert admin_bell["total"] == 1 + 6 + 1  # own, Warning desk and Other desk (creator)


async def test_rule_and_kind_mutes_are_per_account_undoable_and_scope_checked(
    client: AsyncClient, container: Container, admin: User, warning_actors: WarningActors
) -> None:
    actors = warning_actors
    headers = await desk_headers(client, actors)
    rule = await create_indicator(container, actors.owner, actors.team.id, name="Rail yard")
    foreign_rule = await create_indicator(container, actors.outsider, actors.other.id)
    noisy = make_alert(container, actors.owner.id, actors.team.id, indicator_id=rule.id)
    other = make_alert(container, actors.owner.id, actors.team.id)
    await add_alerts(container, noisy, other)

    path = f"{BELL}/muted-rules/{rule.id}"
    for _ in range(2):  # Idempotent.
        muted = await client.put(path, headers=headers["owner"])
        assert muted.status_code == 200, muted.text
    rules = muted.json()["muted_rules"]
    assert [(item["indicator_id"], item["name"]) for item in rules] == [(str(rule.id), "Rail yard")]
    owner = (await _bell(client, headers["owner"]))["alerts"]
    assert [item["id"] for item in owner["items"]] == [str(other.id)] and owner["total"] == 1
    # Another member's bell, the rule's Enabled switch and the alert itself are unchanged.
    assert (await _bell(client, headers["peer"]))["alerts"]["total"] == 2
    listed = await client.get("/api/warning/indicators", headers=headers["owner"])
    assert next(i for i in listed.json()["items"] if i["id"] == str(rule.id))["enabled"] is True
    warning = await client.get("/api/warning/alerts", headers=headers["peer"])
    assert {i["id"]: i["acknowledged_at"] for i in warning.json()["items"]}[str(noisy.id)] is None

    assert (
        await client.put(f"{BELL}/muted-rules/{foreign_rule.id}", headers=headers["owner"])
    ).status_code == 404
    assert (
        await client.put(f"{BELL}/muted-rules/{uuid4()}", headers=headers["owner"])
    ).status_code == 404

    undone = await client.delete(path, headers=headers["owner"])
    assert undone.status_code == 200 and undone.json()["muted_rules"] == []
    assert (await client.delete(path, headers=headers["owner"])).status_code == 200
    assert (await _bell(client, headers["owner"]))["alerts"]["total"] == 2

    kinds = await client.put(
        f"{BELL}/preferences", json={"muted_kinds": ["alerts", "alerts"]}, headers=headers["owner"]
    )
    assert kinds.status_code == 200 and kinds.json()["muted_kinds"] == ["alerts"]
    owner_bell = await _bell(client, headers["owner"])
    assert owner_bell["alerts"] == {"items": [], "total": 0, "muted": True}
    assert owner_bell["preferences"]["muted_kinds"] == ["alerts"]
    assert (await _bell(client, headers["peer"]))["preferences"]["muted_kinds"] == []
    bad = await client.put(
        f"{BELL}/preferences", json={"muted_kinds": ["email"]}, headers=headers["owner"]
    )
    assert bad.status_code == 422

    # A rule muted while readable leaves the list once its team is no longer the caller's.
    await client.put(path, headers=headers["owner"])
    async with team_service(container) as service:
        await service.remove_member(admin, actors.team.id, actors.owner.id, CONTEXT)
    gone = await _bell(client, headers["owner"])
    assert gone["preferences"]["muted_rules"] == []


async def test_destinations_recheck_current_access_and_explain_fallbacks(
    client: AsyncClient, container: Container, warning_actors: WarningActors
) -> None:
    actors = warning_actors
    headers = await desk_headers(client, actors)
    report = await seed_report(container, actors.owner.id, actors.team.id)
    with_report = make_alert(container, actors.owner.id, actors.team.id, report_id=report)
    lost_report = make_alert(container, actors.owner.id, actors.team.id, report_id=uuid4())
    monitor = make_alert(container, actors.owner.id, monitor=(uuid4(), uuid4()))
    plain = make_alert(container, actors.owner.id)
    await add_alerts(container, with_report, lost_report, monitor, plain)

    async def destination(alert_id: object, who: str = "owner") -> Any:
        return await client.get(f"{BELL}/alerts/{alert_id}/destination", headers=headers[who])

    found = (await destination(with_report.id)).json()
    assert found["kind"] == "report" and found["available"] is True
    assert found["report_id"] == str(report)
    missing = (await destination(lost_report.id)).json()
    assert missing["kind"] == "report" and missing["available"] is False
    assert missing["report_id"] is None and "no longer available" in missing["message"]
    transition = (await destination(monitor.id)).json()
    assert transition["kind"] == "transition" and transition["available"] is False
    assert transition["monitor_id"] is None and transition["transition_id"] is None
    assert (await destination(plain.id)).json() == {
        "kind": "alerts",
        "available": True,
        "report_id": None,
        "monitor_id": None,
        "transition_id": None,
        "message": None,
    }
    # Unreadable and unknown alerts are indistinguishable.
    assert (await destination(with_report.id, "outsider")).status_code == 404
    assert (await destination(uuid4(), "outsider")).status_code == 404
    assert (await destination(plain.id, "peer")).status_code == 404


async def test_acknowledge_shown_only_touches_listed_eligible_ids_and_reports_failures(
    client: AsyncClient, container: Container, admin: User, warning_actors: WarningActors
) -> None:
    actors = warning_actors
    headers = await desk_headers(client, actors)
    team_alert = make_alert(container, actors.peer.id, actors.team.id)
    own = make_alert(container, actors.owner.id)
    unseen = make_alert(container, actors.owner.id, actors.team.id)
    foreign = make_alert(container, actors.outsider.id, actors.other.id)
    await add_alerts(container, team_alert, own, unseen, foreign)

    ids = [str(team_alert.id), str(own.id), str(foreign.id), str(own.id)]
    result = await client.post(
        f"{BELL}/alerts/acknowledge", json={"alert_ids": ids}, headers=headers["owner"]
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["acknowledged"] == [str(team_alert.id), str(own.id)]
    assert body["failed"] == [{"alert_id": str(foreign.id), "message": "Alert not found."}]
    remaining = (await _bell(client, headers["owner"]))["alerts"]
    assert [item["id"] for item in remaining["items"]] == [str(unseen.id)]
    # Repeating is harmless and the outsider's alert is still waiting for its own team.
    again = await client.post(
        f"{BELL}/alerts/acknowledge", json={"alert_ids": [str(own.id)]}, headers=headers["owner"]
    )
    assert again.json() == {"acknowledged": [str(own.id)], "failed": []}
    assert (await _bell(client, headers["outsider"]))["alerts"]["total"] == 1

    too_many = [str(uuid4()) for _ in range(21)]
    assert (
        await client.post(
            f"{BELL}/alerts/acknowledge", json={"alert_ids": too_many}, headers=headers["owner"]
        )
    ).status_code == 422

    async with team_service(container) as service:
        await service.update(admin, actors.team.id, name=None, is_active=False, context=CONTEXT)
    archived = (await _bell(client, headers["owner"]))["alerts"]["items"]
    assert [(item["id"], item["can_acknowledge"]) for item in archived] == [(str(unseen.id), False)]
    refused = await client.post(
        f"{BELL}/alerts/acknowledge", json={"alert_ids": [str(unseen.id)]}, headers=headers["owner"]
    )
    assert refused.json() == {
        "acknowledged": [],
        "failed": [{"alert_id": str(unseen.id), "message": "Archived teams are read-only."}],
    }
