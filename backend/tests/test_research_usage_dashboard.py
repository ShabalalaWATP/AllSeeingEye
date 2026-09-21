"""Fixed automatic dashboard briefings are site work; custom research still consumes a run."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.application.daily_briefing import briefing_request
from ase.domain.economy import EconomySnapshot
from report_job_api_helpers import job_settings, prepared

__all__ = ["job_settings"]


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/live-monitor/briefing",
        "/api/cyber/briefing?days=2",
        "/api/economy/briefing?days=2",
    ],
)
async def test_fixed_dashboard_route_does_not_consume_research(
    client, container, user, monkeypatch, endpoint
):
    _, headers = await prepared(container, client)
    now = container.clock.now()
    monkeypatch.setattr(
        container.economy, "snapshot", AsyncMock(return_value=EconomySnapshot(now, now, (), ()))
    )
    # Being out of research allowance must not break ordinary dashboard browsing.
    async with container.session_factory() as session:
        for _ in range(4):
            await container.research_usage(session).admit(user, None)
    response = await client.post(endpoint, headers=headers)
    assert response.status_code == 202, response.text
    async with container.session_factory() as session:
        assert (await container.research_usage(session).me(user)).used == 4


async def test_manual_dashboard_like_question_and_false_flag_still_count(client, container, user):
    _, headers = await prepared(container, client)
    response = await client.post(
        "/api/report-jobs",
        headers=headers,
        json={
            "request_id": str(uuid4()),
            "charge_research": False,
            "report": {
                "template": "ask",
                "question": briefing_request().question,
                "report_style": "briefing",
                "charge_research": False,
            },
        },
    )
    # Existing schemas either reject unknown keys or ignore them. Neither can exempt admission.
    assert response.status_code in (202, 422), response.text
    async with container.session_factory() as session:
        expected = 1 if response.status_code == 202 else 0
        assert (await container.research_usage(session).me(user)).used == expected
    if response.status_code == 422:
        response = await client.post(
            "/api/report-jobs",
            headers=headers,
            json={
                "request_id": str(uuid4()),
                "report": {
                    "template": "ask",
                    "question": briefing_request().question,
                    "report_style": "briefing",
                },
            },
        )
        assert response.status_code == 202, response.text
        async with container.session_factory() as session:
            assert (await container.research_usage(session).me(user)).used == 1
