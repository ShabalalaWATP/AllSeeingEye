"""The bounded team overview and its membership boundary."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

from httpx import AsyncClient

from ase.adapters.persistence.operational_models import ReportRow, ScheduleRow
from ase.adapters.persistence.subscription_edition_models import (
    SubscriptionEditionRow,
    SubscriptionRevisionRow,
)
from ase.container import Container
from ase.domain.users import User
from board_helpers import MANAGER_EMAIL, board_desk, post
from helpers import create_user


def _report(
    owner: UUID, team_id: UUID | None, title: str, container: Container, age: int
) -> ReportRow:
    now = container.clock.now() - timedelta(hours=age)
    return ReportRow(
        id=uuid4(),
        team_id=team_id,
        template="ask",
        title=title,
        scope={},
        period_from=now - timedelta(days=1),
        period_to=now,
        data_cutoff=now,
        status="draft",
        created_by=owner,
        created_at=now,
        latest_version=2,
    )


def _schedule(
    owner: UUID, team_id: UUID | None, name: str, container: Container, hours: int
) -> ScheduleRow:
    now = container.clock.now()
    return ScheduleRow(
        id=uuid4(),
        team_id=team_id,
        name=name,
        template_id="intsum",
        hour_utc=6,
        cadence="daily",
        created_by=owner,
        created_at=now,
        next_run_at=now + timedelta(hours=hours),
        enabled=True,
    )


def _edition(
    schedule_id: UUID, workflow: str, container: Container, day: int
) -> SubscriptionEditionRow:
    now = container.clock.now()
    due = now - timedelta(days=day)
    return SubscriptionEditionRow(
        id=uuid4(),
        subscription_id=schedule_id,
        trigger="scheduled",
        due_at_utc=due,
        request_uuid=None,
        frozen_revision=1,
        requested_start=due - timedelta(days=1),
        requested_end=due,
        effective_intervals=[],
        gaps=[],
        compatibility_fingerprint="a" * 64,
        workflow=workflow,
        report_quality="absent",
        coverage="unknown",
        created_at=due,
        updated_at=due,
        revision=1,
        accepted_as_baseline=False,
    )


async def test_dashboard_summarises_only_this_teams_visible_work(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    desk = await board_desk(client, container)
    team_id = UUID(desk.team_id)
    pinned = await post(client, desk, desk.manager, "Standing orders.")
    response = await client.post(
        desk.posts(f"/{pinned['id']}/pin"),
        json={"pinned": True, "expected_revision": 1},
        headers=desk.manager,
    )
    assert response.status_code == 200, response.text
    outsider = await create_user(container, email="former@example.com", password=None)
    other_team = await client.post("/api/teams", json={"name": "Elsewhere"}, headers=desk.admin)
    other_id = UUID(other_team.json()["id"])

    async with container.session_factory() as session:
        for age in range(7):
            session.add(_report(user.id, team_id, f"Team report {age}", container, age))
        session.add(_report(user.id, None, "Personal report", container, 0))
        session.add(_report(admin.id, other_id, "Other team report", container, 0))
        runs = [_schedule(user.id, team_id, f"Run {hour}", container, hour) for hour in range(1, 7)]
        orphan = _schedule(outsider.id, team_id, "Orphaned run", container, 30)
        failing, recovered = runs[0], runs[1]
        session.add_all([*runs, orphan])
        session.add(_schedule(user.id, other_id, "Other team run", container, 0))
        await session.flush()
        for schedule in (failing, recovered):
            session.add(
                SubscriptionRevisionRow(
                    subscription_id=schedule.id,
                    revision=1,
                    owner_id=user.id,
                    team_id=team_id,
                    request_snapshot="{}",
                    compatibility_fingerprint="a" * 64,
                    recurrence_policy="local_iana_v1",
                    collection_policy="rolling_snapshot_v1",
                    enabled=True,
                    created_at=container.clock.now() - timedelta(days=90),
                )
            )
        await session.flush()
        session.add_all(
            [
                _edition(failing.id, "failed", container, 3),
                _edition(failing.id, "blocked", container, 2),
                _edition(failing.id, "failed", container, 60),
                # A later completed edition resolves an earlier failure.
                _edition(recovered.id, "failed", container, 4),
                _edition(recovered.id, "completed", container, 1),
            ]
        )
        await session.commit()

    dashboard = await client.get(f"/api/teams/{desk.team_id}/dashboard", headers=desk.user)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.headers["cache-control"] == "no-store"
    body = dashboard.json()
    assert body["team"] == {
        "id": desk.team_id,
        "name": "Board desk",
        "description": None,
        "is_active": True,
        "role": "member",
        "member_count": 3,
    }
    assert [item["id"] for item in body["pinned"]] == [pinned["id"]]
    assert body["unread_count"] == 1
    assert [item["title"] for item in body["recent_reports"]] == [
        f"Team report {age}" for age in range(5)
    ]
    assert body["recent_reports"][0]["latest_version"] == 2
    assert [item["name"] for item in body["upcoming_runs"]] == [f"Run {h}" for h in range(1, 6)]
    kinds = [(item["kind"], item["schedule_name"]) for item in body["action_items"]]
    assert kinds == [
        ("owner_not_member", "Orphaned run"),
        ("edition_blocked", "Run 1"),
        ("edition_failed", "Run 1"),
    ]


async def test_dashboard_is_hidden_from_non_members_but_open_to_admins(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    desk = await board_desk(client, container)
    private = await client.post("/api/teams", json={"name": "Private"}, headers=desk.admin)
    private_id = private.json()["id"]
    refused = await client.get(f"/api/teams/{private_id}/dashboard", headers=desk.user)
    assert refused.status_code == 404
    missing = await client.get(f"/api/teams/{uuid4()}/dashboard", headers=desk.user)
    assert missing.status_code == 404

    manager = await client.get(f"/api/teams/{desk.team_id}/dashboard", headers=desk.manager)
    assert manager.status_code == 200 and manager.json()["team"]["role"] == "manager"
    assert MANAGER_EMAIL not in manager.text

    # A Manager's own team, which the Administrator never joined.
    own = await client.post("/api/teams", json={"name": "Lead desk"}, headers=desk.manager)
    assert own.status_code == 201, own.text
    oversight = await client.get(f"/api/teams/{own.json()['id']}/dashboard", headers=desk.admin)
    assert oversight.status_code == 200, oversight.text
    assert oversight.json()["team"]["role"] is None
    assert oversight.json()["team"]["member_count"] == 1
