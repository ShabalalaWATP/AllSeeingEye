"""KAN-88 and KAN-119: pausing stops evaluation, resuming never replays, scope is rechecked."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select

from ase.adapters.persistence.models import AuditLogRow
from ase.adapters.persistence.warning import SqlWarningStore
from ase.application.warning.evaluator import IndicatorEvaluator
from ase.container import Container
from ase.domain.users import User
from ase.domain.warning import Alert, Indicator, evaluate
from helpers import USER_PASSWORD, bearer, login_token
from team_helpers import CONTEXT, team_service
from test_warning import NOW, indicator
from tracker_helpers import conflict_events
from warning_scope_helpers import WarningActors
from warning_scope_helpers import warning_actors as warning_actors  # noqa: PLC0414

RULE: dict[str, Any] = {
    "name": "Kharkiv strikes",
    "countries": ["UA"],
    "keywords": ["Kharkiv"],
    "window_minutes": 10080,
}


class QuietNotifier:
    async def notify(self, alert: Alert, indicator: Indicator) -> bool:
        return True


def _evaluator(container: Container) -> IndicatorEvaluator:
    return IndicatorEvaluator(
        container.store,
        SqlWarningStore(container.session_factory, container.access_policy),
        container.bus,
        QuietNotifier(),
        container.clock,
    )


def _edit(saved: dict[str, Any], **changes: Any) -> dict[str, Any]:
    keys = ("name", "countries", "keywords", "window_minutes", "team_id", "enabled")
    return (
        {key: saved[key] for key in keys} | {"expected_updated_at": saved["updated_at"]} | changes
    )


async def _actions(container: Container) -> list[str]:
    async with container.session_factory() as session:
        rows = await session.scalars(select(AuditLogRow.action).order_by(AuditLogRow.id))
        return [action for action in rows if action.startswith("indicator")]


def test_a_resumed_rule_counts_only_what_was_published_after_it_resumed() -> None:
    events = {e.title: e for e in conflict_events(NOW)}
    before = replace(events["Shelling in Kharkiv"], published_at=NOW - timedelta(hours=2))
    after = replace(before, id="after", published_at=NOW - timedelta(minutes=5))
    rule = indicator(resumed_at=NOW - timedelta(hours=1))
    assert evaluate(rule, [before], NOW, None) is None
    firing = evaluate(rule, [before, after], NOW, None)
    assert firing is not None and firing.count == 1
    assert evaluate(replace(rule, resumed_at=None), [before, after], NOW, None) is not None
    assert evaluate(replace(rule, enabled=False), [after], NOW, None) is None


async def test_paused_rules_raise_nothing_and_resuming_does_not_replay(
    client: AsyncClient, container: Container, warning_actors: WarningActors
) -> None:
    actors = warning_actors
    token = await login_token(client, actors.owner.email, USER_PASSWORD)
    created = await client.post(
        "/api/warning/indicators",
        json={**RULE, "team_id": str(actors.team.id)},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    url = f"/api/warning/indicators/{created.json()['id']}"
    paused = await client.put(url, json=_edit(created.json(), enabled=False), headers=bearer(token))
    assert paused.status_code == 200 and paused.json()["enabled"] is False
    container.store.upsert(conflict_events(container.clock.now()))
    evaluator = _evaluator(container)
    assert await evaluator.run_once() == []

    container.clock.advance(timedelta(minutes=10))
    resumed = await client.put(url, json=_edit(paused.json(), enabled=True), headers=bearer(token))
    assert resumed.status_code == 200 and resumed.json()["enabled"] is True
    assert await evaluator.run_once() == []  # activity from the paused period is not replayed

    container.clock.advance(timedelta(minutes=1))
    fresh = replace(conflict_events(container.clock.now())[0], id="fresh-kharkiv")
    container.store.upsert([fresh])
    fired = await evaluator.run_once()
    assert [alert.count for alert in fired] == [1]
    assert await _actions(container) == [
        "indicator_created",
        "indicator_paused",
        "indicator_resumed",
    ]


async def test_pause_and_resume_recheck_current_team_access(
    client: AsyncClient, container: Container, admin: User, warning_actors: WarningActors
) -> None:
    actors = warning_actors
    owner = await login_token(client, actors.owner.email, USER_PASSWORD)
    outsider = await login_token(client, actors.outsider.email, USER_PASSWORD)
    peer = await login_token(client, actors.peer.email, USER_PASSWORD)
    created = await client.post(
        "/api/warning/indicators",
        json={**RULE, "team_id": str(actors.team.id)},
        headers=bearer(owner),
    )
    url = f"/api/warning/indicators/{created.json()['id']}"
    pause = _edit(created.json(), enabled=False)
    assert (await client.put(url, json=pause, headers=bearer(outsider))).status_code == 404
    assert (await client.put(url, json=pause, headers=bearer(peer))).status_code == 403
    paused = await client.put(url, json=pause, headers=bearer(owner))
    assert paused.status_code == 200
    async with team_service(container) as service:
        await service.update(admin, actors.team.id, name=None, is_active=False, context=CONTEXT)
    resume = _edit(paused.json(), enabled=True)
    assert (await client.put(url, json=resume, headers=bearer(owner))).status_code == 403
    async with team_service(container) as service:
        await service.update(admin, actors.team.id, name=None, is_active=True, context=CONTEXT)
        await service.remove_member(admin, actors.team.id, actors.owner.id, CONTEXT)
    assert (await client.put(url, json=resume, headers=bearer(owner))).status_code == 404
    assert await _actions(container) == ["indicator_created", "indicator_paused"]


async def test_a_team_draft_saves_only_in_a_team_the_author_still_belongs_to(
    client: AsyncClient, container: Container, admin: User, warning_actors: WarningActors
) -> None:
    actors = warning_actors
    token = await login_token(client, actors.owner.email, USER_PASSWORD)
    async with team_service(container) as service:
        await service.remove_member(admin, actors.team.id, actors.owner.id, CONTEXT)
    lost = await client.post(
        "/api/warning/indicators",
        json={**RULE, "team_id": str(actors.team.id)},
        headers=bearer(token),
    )
    assert lost.status_code == 404
    listed = await client.get("/api/warning/indicators", headers=bearer(token))
    assert listed.json()["items"] == []  # no silent fallback to a personal rule
    foreign = await client.post(
        "/api/warning/indicators",
        json={**RULE, "team_id": str(actors.other.id)},
        headers=bearer(token),
    )
    assert foreign.status_code == 404
