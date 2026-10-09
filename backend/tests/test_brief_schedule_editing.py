"""A settings edit keeps the subscription's authored revision and retained work."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import UUID

import pytest

from ase.adapters.persistence.subscription_settings import SqlSubscriptionSettings
from ase.application.auditing import Auditor
from ase.domain.audit import AuditAction
from ase.domain.teams import MembershipRole
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from team_helpers import CONTEXT, team_service
from test_research_brief_api import _draft


async def subscription(client, *, team_id=None, enabled=False):
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    draft = {**_draft(), "team_id": str(team_id) if team_id else None}
    saved = await client.post("/api/research/briefs", headers=headers, json=draft)
    assert saved.status_code == 201, saved.text
    brief_id = saved.json()["brief"]["identity"]["id"]
    result = await client.post(
        "/api/schedules/from-brief",
        headers=headers,
        json={"brief_id": brief_id, "brief_revision": 1, "name": "Original", "enabled": enabled},
    )
    assert result.status_code == 201, result.text
    return result.json(), headers, draft


def settings(row, **changes):
    return {
        "expected_revision": row.get("settings_revision", "0" * 64),
        "name": row["name"],
        **{
            key: row[key]
            for key in (
                "timezone",
                "local_hour",
                "local_minute",
                "cadence",
                "weekday",
                "monthday",
                "anchor_month",
            )
        },
        **changes,
    }


async def test_edit_preserves_pinned_brief_paused_state_and_history(client, container, user):
    original, headers, draft = await subscription(client)
    revised = deepcopy(draft)
    revised.update(base_revision=1)
    revised["question"]["main"] = "A later question?"
    assert (
        await client.post(
            f"/api/research/briefs/{original['brief_id']}/revisions", headers=headers, json=revised
        )
    ).status_code == 201
    history = await client.get(f"/api/schedules/{original['id']}/editions", headers=headers)
    changed = await client.put(
        f"/api/schedules/{original['id']}/brief-settings",
        headers=headers,
        json=settings(
            original, name="Renamed", timezone="Europe/London", local_hour=9, local_minute=30
        ),
    )
    assert changed.status_code == 200, changed.text
    row = changed.json()
    assert row["settings_revision"] != original["settings_revision"]
    assert (row["brief_id"], row["brief_revision"], row["enabled"]) == (
        original["brief_id"],
        1,
        False,
    )
    allowed = {
        "name",
        "timezone",
        "local_hour",
        "local_minute",
        "hour_utc",
        "next_run_at",
        "next_three",
        "settings_revision",
    }
    assert {key: value for key, value in row.items() if key not in allowed} == {
        key: value for key, value in original.items() if key not in allowed
    }
    after = await client.get(f"/api/schedules/{original['id']}/editions", headers=headers)
    assert after.json() == history.json()
    assert changed.headers["cache-control"] == "private, no-store"


async def test_stale_edit_conflicts_but_pause_does_not_change_settings_revision(client, user):
    row, headers, _ = await subscription(client, enabled=True)
    path = f"/api/schedules/{row['id']}/brief-settings"
    paused = await client.post(f"/api/schedules/{row['id']}/pause", headers=headers)
    assert paused.status_code == 200
    accepted = await client.put(path, headers=headers, json=settings(row, name="First edit"))
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["enabled"] is False
    assert accepted.json()["next_run_at"] == paused.json()["next_run_at"]
    stale = await client.put(path, headers=headers, json=settings(row, name="Stale edit"))
    assert stale.status_code == 409
    assert "reload" in stale.json()["error"]["message"].lower()


@pytest.mark.parametrize(
    "extra",
    [
        {"brief_revision": 2},
        {"brief_id": "00000000-0000-4000-8000-000000000000"},
        {"question": "Changed"},
        {"enabled": True},
        {"team_id": None},
        {"created_by": None},
        {"collection_policy": "since_last_success"},
        {"window_hours": 100},
    ],
)
async def test_settings_cannot_change_other_subscription_fields(client, user, extra):
    row, headers, _ = await subscription(client)
    result = await client.put(
        f"/api/schedules/{row['id']}/brief-settings", headers=headers, json=settings(row, **extra)
    )
    assert result.status_code == 422


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "   "},
        {"timezone": "Missing/Timezone"},
        {"local_hour": 24},
        {"local_minute": -1},
        {"cadence": "hourly"},
        {"weekday": 7},
        {"monthday": 0},
        {"anchor_month": 13},
        {"local_hour": True},
    ],
)
async def test_invalid_settings_do_not_mutate_subscription(client, user, changes):
    row, headers, _ = await subscription(client)
    result = await client.put(
        f"/api/schedules/{row['id']}/brief-settings", headers=headers, json=settings(row, **changes)
    )
    assert result.status_code == 422
    stored = (await client.get("/api/schedules", headers=headers)).json()["items"][0]
    assert stored == row


@pytest.mark.parametrize(
    ("now", "changes", "expected"),
    [
        (
            datetime(2026, 3, 28, 12, tzinfo=UTC),
            {"timezone": "Europe/London", "cadence": "daily", "local_hour": 1, "local_minute": 30},
            "2026-03-29T01:00:00Z",
        ),
        (
            datetime(2026, 10, 24, 12, tzinfo=UTC),
            {"timezone": "Europe/London", "cadence": "daily", "local_hour": 1, "local_minute": 30},
            "2026-10-25T00:30:00Z",
        ),
        (
            datetime(2026, 1, 31, 12, tzinfo=UTC),
            {"cadence": "monthly", "monthday": 31},
            "2026-02-28T06:00:00Z",
        ),
        (
            datetime(2026, 4, 1, 12, tzinfo=UTC),
            {"cadence": "quarterly", "monthday": 31, "anchor_month": 2},
            "2026-05-31T06:00:00Z",
        ),
    ],
)
async def test_recurrence_edit_recalculates_next_calendar_slot(
    client, container, user, now, changes, expected
):
    container.clock.advance(now - container.clock.now())
    row, headers, _ = await subscription(client)
    result = await client.put(
        f"/api/schedules/{row['id']}/brief-settings", headers=headers, json=settings(row, **changes)
    )
    assert result.status_code == 200, result.text
    assert result.json()["next_run_at"] == expected


async def test_object_authority_and_archived_team_are_checked(client, container, user, admin):
    row, headers, _ = await subscription(client)
    other = await create_user(
        container, email="editor@example.com", password="long-test-passphrase"
    )
    other_headers = bearer(await login_token(client, other.email, "long-test-passphrase"))
    assert (
        await client.put(
            f"/api/schedules/{row['id']}/brief-settings", headers=other_headers, json=settings(row)
        )
    ).status_code == 404
    async with team_service(container) as service:
        team = await service.create(admin, "Shared subscriptions", CONTEXT)
        for member in (user, other):
            await service.set_member(
                admin, team.id, email=member.email, role=MembershipRole.MEMBER, context=CONTEXT
            )
    shared, _, _ = await subscription(client, team_id=team.id)
    path = f"/api/schedules/{shared['id']}/brief-settings"
    forbidden = await client.put(path, headers=other_headers, json=settings(shared))
    assert forbidden.status_code == 403
    async with team_service(container) as service:
        await service.change_role(admin, team.id, other.id, MembershipRole.MANAGER, CONTEXT)
    edited = await client.put(path, headers=other_headers, json=settings(shared, name="Team edit"))
    assert edited.status_code == 200, edited.text
    assert edited.json()["created_by"] == shared["created_by"]
    async with team_service(container) as service:
        await service.remove_member(admin, team.id, other.id, CONTEXT)
    denied = await client.put(
        path, headers=other_headers, json=settings(edited.json(), name="Denied")
    )
    assert denied.status_code == 404
    async with team_service(container) as service:
        await service.update(admin, team.id, name=None, is_active=False, context=CONTEXT)
    archived = await client.put(path, headers=headers, json=settings(edited.json()))
    assert archived.status_code == 403


async def test_session_expiry_before_commit_rolls_back_settings(client, container, user):
    row, headers, _ = await subscription(client)
    original = Auditor.record

    async def delayed(self, action, **kwargs):
        result = await original(self, action, **kwargs)
        if action is AuditAction.SCHEDULE_UPDATED:
            container.clock.advance(timedelta(days=1))
        return result

    with patch.object(Auditor, "record", delayed):
        result = await client.put(
            f"/api/schedules/{row['id']}/brief-settings",
            headers=headers,
            json=settings(row, name="Rollback"),
        )
    assert result.status_code == 401
    async with container.session_factory() as session:
        saved = await container.repositories(session).schedules.get(UUID(row["id"]))
    assert saved.name == row["name"]


async def test_settings_action_rejects_nonbrief_archived_and_missing_subscriptions(client, user):
    row, headers, _ = await subscription(client)
    standard = await client.post(
        "/api/schedules", headers=headers, json={"name": "Standard", "template_id": "intsum"}
    )
    result = await client.put(
        f"/api/schedules/{standard.json()['id']}/brief-settings",
        headers=headers,
        json=settings(standard.json()),
    )
    assert result.status_code == 422
    assert (await client.delete(f"/api/schedules/{row['id']}", headers=headers)).status_code == 204
    assert (
        await client.put(
            f"/api/schedules/{row['id']}/brief-settings", headers=headers, json=settings(row)
        )
    ).status_code == 404
    assert (
        await client.put(
            "/api/schedules/00000000-0000-4000-8000-000000000000/brief-settings",
            headers=headers,
            json=settings(row),
        )
    ).status_code == 404


async def test_conditional_update_conflict_is_reported_without_success(client, user, monkeypatch):
    row, headers, _ = await subscription(client)

    async def changed(*args):
        return None

    monkeypatch.setattr(SqlSubscriptionSettings, "update", changed)
    result = await client.put(
        f"/api/schedules/{row['id']}/brief-settings",
        headers=headers,
        json=settings(row, name="Lost race"),
    )
    assert result.status_code == 409
