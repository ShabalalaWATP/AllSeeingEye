"""Saved research configuration round trips and reaches the scheduled report request."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient

from ase.application.schedules.manage import ScheduleInput, build_schedule
from ase.application.schedules.report_request import scheduled_report_request
from ase.container import Container
from ase.domain.errors import InvalidRequest
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token

NOW = datetime(2026, 9, 6, tzinfo=UTC)
OPTIONS = {
    "name": "Weekly port question",
    "template_id": "ask",
    "question": "What changed at the port?",
    "research_mode": "detailed",
    "research_languages": ["en", "uk"],
    "research_focus": "company",
    "research_subject": "Example Port",
    "cadence": "weekly",
}


@pytest.mark.parametrize("mode", list(ResearchMode))
async def test_saved_question_round_trip_update_and_scheduled_request(
    client: AsyncClient, container: Container, user: User, mode: ResearchMode
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    options = {**OPTIONS, "research_mode": mode.value}
    created = await client.post("/api/schedules", json=options, headers=bearer(token))
    assert created.status_code == 201, created.text
    for key, value in options.items():
        assert created.json()[key] == value
    schedule_id = created.json()["id"]
    edited = await client.put(
        f"/api/schedules/{schedule_id}",
        json={**options, "question": "What changed this week?", "research_languages": ["EN", "en"]},
        headers=bearer(token),
    )
    assert edited.status_code == 200
    assert edited.json()["research_languages"] == ["en"]
    listed = await client.get("/api/schedules", headers=bearer(token))
    assert listed.json()["items"][0]["question"] == "What changed this week?"
    async with container.session_factory() as session:
        schedule = (await container.list_schedules(session).execute(user))[0]
    request = scheduled_report_request(schedule)
    assert schedule.created_by == user.id and request.automation is True
    assert request.question == "What changed this week?"
    assert request.research_mode is mode
    assert request.research_languages == ("en",)
    assert request.research_focus is ResearchFocus.COMPANY
    assert request.research_subject == "Example Port"


@pytest.mark.parametrize(
    "changes",
    [
        {"question": " "},
        {"question": "x" * 1001},
        {"research_languages": []},
        {"research_languages": ["en"] * 9},
        {"research_languages": ["en;bad"]},
        {"research_subject": "x" * 301},
        {"research_subject": " "},
        {"research_subject": None},
        {"research_mode": "unbounded"},
        {"research_focus": "private"},
        {"research_focus": "document"},
        {"research_focus": "media"},
        {"country_iso": "GB"},
    ],
)
async def test_invalid_research_config_is_rejected(
    client: AsyncClient, user: User, changes: dict[str, object]
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.post(
        "/api/schedules", json={**OPTIONS, **changes}, headers=bearer(token)
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "changes",
    [
        {"question": " "},
        {"question": "x" * 1001},
        {"research_languages": ()},
        {"research_languages": ("en;bad",)},
        {"research_subject": "x" * 301},
        {"research_mode": "unknown"},
        {"research_focus": "unknown"},
        {"research_focus": ResearchFocus.DOCUMENT},
        {"research_focus": ResearchFocus.MEDIA},
    ],
)
def test_application_boundary_validates_research_config(changes: dict[str, object]) -> None:
    values = {
        "name": "Research",
        "template_id": "ask",
        "question": "Question?",
        "research_mode": ResearchMode.QUICK,
        **changes,
    }
    with pytest.raises(InvalidRequest):
        build_schedule(
            ScheduleInput(**values), schedule_id=uuid4(), owner=uuid4(), created=NOW, now=NOW
        )


@pytest.mark.parametrize("focus", ["document", "media"])
async def test_schedule_update_cannot_depend_on_expiring_upload(
    client: AsyncClient, user: User, focus: str
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    created = await client.post("/api/schedules", json=OPTIONS, headers=bearer(token))
    assert created.status_code == 201
    response = await client.put(
        f"/api/schedules/{created.json()['id']}",
        json={**OPTIONS, "research_focus": focus},
        headers=bearer(token),
    )
    assert response.status_code == 422
    listed = await client.get("/api/schedules", headers=bearer(token))
    assert listed.json()["items"][0]["research_focus"] == "company"
