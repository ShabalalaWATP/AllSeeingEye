"""Reporting periods must match frozen selection and the persisted current record."""

from dataclasses import replace
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from ase.adapters.persistence.reports import SqlReportRepository
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.reports.production import Producer
from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import TEMPLATES
from ase.container import Container
from ase.domain.users import User
from feeds_helpers import make_event
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, FakeClock, bearer, login_token
from production_integration_helpers import RecordingUsage, production_job, production_record
from report_helpers import PROFILE, ScriptedGateway


@pytest.mark.parametrize("hours, expected", [(1, {"recent"}), (168, {"recent", "older", "week"})])
async def test_custom_period_controls_frozen_evidence(
    container: Container, user: User, hours, expected
):
    now = container.clock.now()
    store = InMemoryEventStore()
    store.upsert(
        [
            make_event(event_id, title=event_id, published_at=now - timedelta(hours=age))
            for event_id, age in [("recent", 0.5), ("older", 2), ("week", 100)]
        ]
    )
    job = replace(
        production_job(user, container.cipher),
        template=TEMPLATES["intsum"],
        request=ReportRequest("intsum", window_hours=hours),
        window=timedelta(hours=hours),
        now=now,
    )
    producer = Producer(
        store=store,
        source_profiles={},
        cipher=container.cipher,
        gateway=ScriptedGateway("{}"),
        usage=RecordingUsage(),
    )

    async def no_optional_profile(role):
        return None

    version = await producer.produce(job, no_optional_profile)
    assert {item.title for item in version.evidence} == expected


async def test_new_version_persists_current_period_without_rewriting_history(
    container: Container,
    user: User,
):
    job = production_job(user, container.cipher)
    producer = Producer(
        store=InMemoryEventStore(),
        source_profiles={},
        cipher=container.cipher,
        gateway=ScriptedGateway("{}"),
        usage=RecordingUsage(),
    )

    async def no_optional_profile(role):
        return None

    first = await producer.produce(job, no_optional_profile)
    record = production_record(job, first)
    async with container.session_factory() as session:
        repositories = container.repositories(session)
        await repositories.llm_profiles.add(job.profile)
        await repositories.reports.add(record, first)
        await session.commit()

    later = job.now + timedelta(hours=5)
    second = replace(first, id=uuid4(), number=2, created_at=later, markdown="Second version")
    record.latest_version = 2
    record.period_from = later - job.window
    record.period_to = record.data_cutoff = later
    async with container.session_factory() as session:
        await SqlReportRepository(session).add_version(record, second)
        await session.commit()

    async with container.session_factory() as session:
        repository = SqlReportRepository(session)
        saved = await repository.get(record.id)
        assert saved is not None
        assert (saved.period_from, saved.period_to, saved.data_cutoff) == (
            later - job.window,
            later,
            later,
        )
        assert saved.created_at == job.now
        original = await repository.get_version(record.id, 1)
        assert original is not None
        assert original.created_at == first.created_at
        assert original.markdown == first.markdown


async def test_custom_window_regeneration_via_api_uses_current_evidence_and_dates(
    client: AsyncClient,
    container: Container,
    admin: User,
    clock: FakeClock,
) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    headers = bearer(token)
    profile = await client.post("/api/admin/llm/profiles", json=PROFILE, headers=headers)
    assert profile.status_code == 201
    container.llm = ScriptedGateway("{}", "{}", "{}", "{}")
    original_now = clock.now()
    container.store.upsert(
        [
            make_event(
                "inside",
                title="Inside original window",
                published_at=original_now - timedelta(minutes=55),
            ),
            make_event(
                "outside",
                title="Outside requested window",
                published_at=original_now - timedelta(hours=2),
            ),
        ]
    )
    created = await client.post(
        "/api/reports",
        json={"template": "intsum", "window_hours": 1},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    first = created.json()
    assert [item["title"] for item in first["version"]["evidence"]] == ["Inside original window"]

    clock.advance(timedelta(minutes=10))
    container.store.upsert([make_event("current", title="New reporting", published_at=clock.now())])
    report_id = first["report"]["id"]
    updated = await client.post(f"/api/reports/{report_id}/versions", headers=headers)
    assert updated.status_code == 201, updated.text
    assert [item["title"] for item in updated.json()["version"]["evidence"]] == ["New reporting"]
    read = await client.get(f"/api/reports/{report_id}", headers=headers)
    assert read.status_code == 200
    record = read.json()["report"]
    assert record["scope"]["window_hours"] == 1
    assert datetime.fromisoformat(record["period_from"]) == clock.now() - timedelta(hours=1)
    assert datetime.fromisoformat(record["period_to"]) == clock.now()
    history = await client.get(f"/api/reports/{report_id}?version=1", headers=headers)
    assert history.status_code == 200
    assert history.json()["version"]["evidence"] == first["version"]["evidence"]
    assert datetime.fromisoformat(history.json()["version"]["period_to"]) == original_now
    assert datetime.fromisoformat(history.json()["version"]["period_from"]) == (
        original_now - timedelta(hours=1)
    )
    assert datetime.fromisoformat(read.json()["version"]["data_cutoff"]) == clock.now()
