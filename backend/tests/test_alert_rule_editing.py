"""KAN-88: alert rules are edited with an optimistic revision guard and never silently widened."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select

from ase.adapters.persistence.models import AuditLogRow
from ase.application.direction.plans import PirInput, PlanInput
from ase.container import Container
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from team_helpers import CONTEXT
from test_exact_reusable_areas import triangle

RULE: dict[str, Any] = {
    "name": "Kharkiv strikes",
    "description": "From the weekly assessment.",
    "countries": ["UA"],
    "categories": ["conflict"],
    "keywords": ["Kharkiv"],
    "threshold": 2,
    "window_minutes": 360,
    "cooldown_minutes": 90,
    "severity_floor": 0.4,
    "report_template": "intsum",
}


def _editable(saved: dict[str, Any]) -> dict[str, Any]:
    """The request an edit form sends back: every saved value plus the revision it read."""
    keys = (*RULE, "plan_id", "bbox", "enabled", "team_id")
    return {key: saved[key] for key in keys} | {"expected_updated_at": saved["updated_at"]}


async def _create(client: AsyncClient, token: str, **changes: Any) -> dict[str, Any]:
    created = await client.post(
        "/api/warning/indicators", json={**RULE, **changes}, headers=bearer(token)
    )
    assert created.status_code == 201, created.text
    return dict(created.json())


async def _audit(container: Container) -> list[tuple[str, dict[str, Any]]]:
    async with container.session_factory() as session:
        rows = await session.scalars(select(AuditLogRow).order_by(AuditLogRow.id))
        return [(row.action, row.details) for row in rows if row.action.startswith("indicator")]


async def test_edit_round_trip_keeps_fields_that_were_not_edited(
    client: AsyncClient, container: Container, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    saved = await _create(client, token)
    edited = await client.put(
        f"/api/warning/indicators/{saved['id']}",
        json=_editable(saved) | {"threshold": 5},
        headers=bearer(token),
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()
    for key in ("description", "cooldown_minutes", "severity_floor", "report_template"):
        assert body[key] == saved[key]
    assert body["threshold"] == 5
    assert datetime.fromisoformat(body["updated_at"]) > datetime.fromisoformat(saved["updated_at"])
    assert (await _audit(container))[-1] == (
        "indicator_updated",
        {"name": "Kharkiv strikes", "changed": ["threshold"]},
    )


async def test_stale_and_missing_revisions_are_refused(
    client: AsyncClient, container: Container, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    saved = await _create(client, token)
    url = f"/api/warning/indicators/{saved['id']}"
    unguarded = {
        key: value for key, value in _editable(saved).items() if key != "expected_updated_at"
    }
    assert (await client.put(url, json=unguarded, headers=bearer(token))).status_code == 422
    first = await client.put(url, json=_editable(saved) | {"threshold": 3}, headers=bearer(token))
    assert first.status_code == 200
    second = await client.put(url, json=_editable(saved) | {"threshold": 7}, headers=bearer(token))
    assert second.status_code == 409
    assert "changed after you opened it" in second.json()["error"]["message"]
    current = await client.get("/api/warning/indicators", headers=bearer(token))
    assert current.json()["items"][0]["threshold"] == 3


async def test_removing_a_restriction_needs_explicit_confirmation(
    client: AsyncClient, container: Container, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    saved = await _create(client, token)
    url = f"/api/warning/indicators/{saved['id']}"
    widened = _editable(saved) | {"countries": [], "categories": []}
    refused = await client.put(url, json=widened, headers=bearer(token))
    assert refused.status_code == 422
    error = refused.json()["error"]
    assert set(error["fields"]) == {"countries", "categories"}
    assert "unrestricted" in error["message"]
    narrowed = await client.put(
        url, json=_editable(saved) | {"countries": ["UA", "BY"]}, headers=bearer(token)
    )
    assert narrowed.status_code == 200
    confirmed = await client.put(
        url,
        json=_editable(narrowed.json()) | {"countries": [], "confirm_wider_scope": True},
        headers=bearer(token),
    )
    assert confirmed.status_code == 200 and confirmed.json()["countries"] == []


async def test_values_are_rejected_rather_than_silently_truncated(
    client: AsyncClient, container: Container, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    for change in (
        {"countries": ["France"]},
        {"countries": ["U1"]},
        {"keywords": ["x" * 61]},
        {"categories": ["politics and war"]},
        {"cooldown_minutes": 1441},
    ):
        response = await client.post(
            "/api/warning/indicators", json={**RULE, **change}, headers=bearer(token)
        )
        assert response.status_code == 422, change
    listed = await client.get("/api/warning/indicators", headers=bearer(token))
    assert listed.json()["items"] == []


async def test_linked_plan_problems_are_actionable_and_never_reveal_other_plans(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    async with container.session_factory() as session:
        own = await container.create_plan(session).execute(
            user, PlanInput("Own plan", pirs=(PirInput("What changed?"),)), CONTEXT
        )
        other = await container.create_plan(session).execute(
            admin, PlanInput("Admin plan", pirs=(PirInput("What changed?"),)), CONTEXT
        )
    saved = await _create(client, token, plan_id=str(own.id))
    messages = []
    for plan_id in (uuid4(), other.id):
        response = await client.put(
            f"/api/warning/indicators/{saved['id']}",
            json=_editable(saved) | {"plan_id": str(plan_id)},
            headers=bearer(token),
        )
        assert response.status_code == 422
        assert set(response.json()["error"]["fields"]) == {"plan_id"}
        messages.append(response.json()["error"]["message"])
    assert messages[0] == messages[1]
    assert "Choose another plan" in messages[0]
    async with container.session_factory() as session:
        await container.delete_plan(session).execute(user, own.id, CONTEXT)
    # Pausing never needs the missing plan, but resuming it must not run without one.
    url = f"/api/warning/indicators/{saved['id']}"
    paused = await client.put(
        url, json=_editable(saved) | {"enabled": False}, headers=bearer(token)
    )
    assert paused.status_code == 200, paused.text
    resumed = await client.put(
        url, json=_editable(paused.json()) | {"enabled": True}, headers=bearer(token)
    )
    assert resumed.status_code == 422 and resumed.json()["error"]["message"] == messages[0]


async def test_an_exact_shape_survives_a_pause_round_trip(
    client: AsyncClient, container: Container, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    created = await client.post(
        "/api/warning/indicators",
        json={"name": "Exact", "research_area": {"geometry": triangle().geometry.to_collection()}},
        headers=bearer(token),
    )
    saved = created.json()
    paused = await client.put(
        f"/api/warning/indicators/{saved['id']}",
        json={
            "name": "Exact",
            "research_area": {"geometry": saved["research_area"]["geometry"]},
            "enabled": False,
            "expected_updated_at": saved["updated_at"],
        },
        headers=bearer(token),
    )
    assert paused.status_code == 200, paused.text
    assert paused.json()["research_area"] == saved["research_area"]
