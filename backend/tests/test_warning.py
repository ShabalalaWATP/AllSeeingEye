"""Warning: indicator rules and their ownership through the API."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from httpx import AsyncClient

from ase.container import Container
from ase.domain.events import BoundingBox, Category
from ase.domain.users import User
from ase.domain.warning import Indicator, alert_from, describe_window, evaluate
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    bearer,
    create_user,
    login_token,
)
from tracker_helpers import conflict_events

NOW = datetime(2026, 9, 5, 12, tzinfo=UTC)


def indicator(**overrides: Any) -> Indicator:
    base: dict[str, Any] = {
        "id": uuid4(), "name": "Kharkiv strikes", "description": "", "plan_id": None,
        "countries": ("UA",), "bbox": None, "categories": (Category.CONFLICT,),
        "keywords": ("Kharkiv",), "threshold": 1, "window_minutes": 360, "cooldown_minutes": 60,
        "severity_floor": 0.0, "report_template": None, "enabled": True, "created_by": uuid4(),
        "created_at": NOW, "updated_at": NOW,
    }  # fmt: skip
    base.update(overrides)
    return Indicator(**base)


def test_evaluation_rules() -> None:
    events = {e.title: e for e in conflict_events(NOW)}
    shelling = replace(events["Shelling in Kharkiv"], published_at=NOW - timedelta(hours=1))
    talks = replace(events["Talks in Kyiv"], published_at=NOW - timedelta(hours=1))
    rule = indicator()
    assert rule.matches(shelling) and not rule.matches(talks)
    firing = evaluate(rule, [shelling, talks], NOW, None)
    assert firing is not None and firing.count == 1 and firing.countries == ("UA",)
    assert evaluate(rule, [shelling], NOW, NOW - timedelta(minutes=30)) is None  # cooling down
    assert evaluate(rule, [shelling], NOW, NOW - timedelta(hours=2)) is not None
    assert evaluate(indicator(threshold=2), [shelling], NOW, None) is None
    assert evaluate(indicator(enabled=False), [shelling], NOW, None) is None
    stale = replace(shelling, published_at=NOW - timedelta(days=2))
    assert evaluate(rule, [stale], NOW, None) is None
    box = indicator(countries=(), bbox=BoundingBox(30, 44, 41, 53), keywords=(), categories=())
    assert box.matches(shelling) and not box.matches(talks)  # the talks item has no point
    assert not indicator(countries=("SD",)).matches(shelling)
    assert not indicator(severity_floor=1.0).matches(shelling)
    assert indicator(countries=(), keywords=(), categories=()).matches(talks)
    alert = alert_from(rule, firing, uuid4(), NOW)
    assert alert.title == "Kharkiv strikes: 1 item in the last 6 h"
    assert alert.event_ids == (shelling.id,) and alert.summary == "Shelling in Kharkiv"
    assert describe_window(90) == "90 min" and describe_window(1440) == "1 d"


async def test_indicators_are_owned_and_validated(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    body = {"name": "Kharkiv strikes", "countries": ["ua"], "keywords": ["Kharkiv"]}
    bad = await client.post(
        "/api/warning/indicators", json={**body, "report_template": "nope"}, headers=bearer(token)
    )
    assert bad.status_code == 422
    unknown_plan = await client.post(
        "/api/warning/indicators", json={**body, "plan_id": str(uuid4())}, headers=bearer(token)
    )
    assert unknown_plan.status_code == 422
    created = await client.post("/api/warning/indicators", json=body, headers=bearer(token))
    assert created.status_code == 201, created.text
    assert created.json()["countries"] == ["UA"] and created.json()["window_minutes"] == 60
    indicator_id = created.json()["id"]

    await create_user(container, email="second@example.com", password="another-long-passphrase")
    second = await login_token(client, "second@example.com", "another-long-passphrase")
    forbidden = await client.put(
        f"/api/warning/indicators/{indicator_id}", json=body, headers=bearer(second)
    )
    assert forbidden.status_code == 404
    edited = await client.put(
        f"/api/warning/indicators/{indicator_id}",
        json={**body, "enabled": False, "threshold": 3},
        headers=bearer(admin_token),
    )
    assert edited.status_code == 200 and edited.json()["threshold"] == 3
    assert edited.json()["created_by"] == created.json()["created_by"]
    listed = await client.get("/api/warning/indicators", headers=bearer(second))
    assert listed.json()["items"] == []
    missing = await client.delete(f"/api/warning/indicators/{uuid4()}", headers=bearer(token))
    assert missing.status_code == 404
    deleted = await client.delete(f"/api/warning/indicators/{indicator_id}", headers=bearer(token))
    assert deleted.status_code == 204
    remaining = await client.get("/api/warning/indicators", headers=bearer(token))
    assert remaining.json() == {"items": []}
