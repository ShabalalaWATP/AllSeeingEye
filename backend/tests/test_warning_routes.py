"""Warning: the evaluator's routes (store, stream, notifier, report) and the webhook guard."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
from httpx import AsyncClient

from ase.adapters.notify.webhook import WebhookNotifier
from ase.adapters.persistence.warning import SqlWarningStore
from ase.api.routers.stream import serialise
from ase.application.warning.evaluator import IndicatorEvaluator
from ase.container import Container
from ase.domain.users import User
from ase.domain.warning import Alert, Indicator, alert_from, evaluate
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE, ScriptedGateway, good_body
from test_warning import NOW, indicator
from tracker_helpers import conflict_events


class RecordingNotifier:
    def __init__(self) -> None:
        self.calls: list[UUID] = []

    async def notify(self, alert: Alert, indicator: Indicator) -> bool:
        self.calls.append(alert.id)
        return True


async def test_evaluator_fires_routes_and_cools_down(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment"]})
    body = {
        "name": "Kharkiv strikes", "countries": ["ua"], "keywords": ["Kharkiv"],
        "window_minutes": 10080, "cooldown_minutes": 60, "report_template": "intsum",
    }  # fmt: skip
    created = await client.post("/api/warning/indicators", json=body, headers=bearer(token))
    assert created.status_code == 201, created.text
    container.store.upsert(conflict_events(container.clock.now()))
    container.llm = ScriptedGateway(json.dumps(good_body()))
    notifier = RecordingNotifier()
    evaluator = IndicatorEvaluator(
        container.store,
        SqlWarningStore(container.session_factory, container.access_policy),
        container.bus,
        notifier,
        container.clock,
        reporter=container.alert_report,
    )
    subscription = container.bus.subscribe()
    fired = await evaluator.run_once()
    assert [alert.count for alert in fired] == [1]
    message = await anext(aiter(subscription))
    subscription.close()
    assert message.kind == "alert"
    payload = serialise(message, frozenset())
    assert payload is not None and payload["title"] == "Kharkiv strikes: 1 item in the last 7 d"
    assert notifier.calls == [fired[0].id]

    alerts = await client.get("/api/warning/alerts", headers=bearer(admin_token))
    assert alerts.status_code == 200
    items = alerts.json()["items"]
    assert len(items) == 1 and alerts.json()["unacknowledged"] == 1
    assert items[0]["report_id"] is not None
    report = await client.get(f"/api/reports/{items[0]['report_id']}", headers=bearer(token))
    assert report.status_code == 200 and report.json()["report"]["scope"]["country"] == "UA"
    assert await evaluator.run_once() == []  # still cooling down

    acked = await client.post(f"/api/warning/alerts/{items[0]['id']}/ack", headers=bearer(token))
    assert acked.status_code == 200 and acked.json()["acknowledged_at"] is not None
    again = await client.post(f"/api/warning/alerts/{items[0]['id']}/ack", headers=bearer(token))
    assert again.json()["acknowledged_by"] == acked.json()["acknowledged_by"]
    unknown = await client.post(f"/api/warning/alerts/{uuid4()}/ack", headers=bearer(token))
    assert unknown.status_code == 404
    unacked = await client.get("/api/warning/alerts?hours=1", headers=bearer(token))
    assert unacked.json()["unacknowledged"] == 0


async def test_webhook_posts_to_public_hosts_only() -> None:
    seen: list[tuple[str, dict[str, Any]]] = []
    status = 200

    def handler(request: httpx.Request) -> httpx.Response:
        if status == 599:
            raise httpx.ConnectError("boom")
        seen.append((request.headers.get("host", ""), json.loads(request.content)))
        return httpx.Response(status)

    events = {e.title: e for e in conflict_events(NOW)}
    shelling = replace(events["Shelling in Kharkiv"], published_at=NOW - timedelta(hours=1))
    rule = indicator()
    firing = evaluate(rule, [shelling], NOW, None)
    assert firing is not None
    alert = alert_from(rule, firing, uuid4(), NOW)
    transport = httpx.MockTransport(handler)
    public = WebhookNotifier("http://93.184.216.34/hook", "ase-test", transport=transport)
    assert await public.notify(alert, rule) is True
    assert seen[0][0] == "93.184.216.34" and seen[0][1]["indicator"]["name"] == "Kharkiv strikes"
    assert seen[0][1]["kind"] == "alert" and seen[0][1]["count"] == 1
    loopback = WebhookNotifier("http://127.0.0.1/hook", "ase-test", transport=transport)
    assert await loopback.notify(alert, rule) is False and len(seen) == 1
    status = 500
    assert await public.notify(alert, rule) is False
    status = 599
    assert await public.notify(alert, rule) is False
