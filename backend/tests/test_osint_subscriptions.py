"""Subscription intervals, scope compatibility and durable novelty without invented changes."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from ase.adapters.persistence.models import ScheduleRow
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.reports.selection import select_evidence
from ase.application.reports.subscription_baseline import load_subscription_baseline
from ase.application.reports.subscription_updates import content_signature, update_guidance
from ase.application.reports.templates import EvidenceStrategy
from ase.application.schedules.manage import ScheduleInput, build_schedule
from ase.application.schedules.report_request import scheduled_report_request
from ase.container import Container
from ase.domain.errors import Forbidden, InvalidRequest, NotFound
from ase.domain.evidence import EvidenceItem
from ase.domain.reports import ReportStatus
from ase.domain.research import ResearchMode
from ase.domain.schedules import next_run_after
from ase.domain.users import User
from feeds_helpers import NOW, make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from report_documents_helpers import document_records
from test_schedule_changes import mark, refresh, save_report, schedule_for


@pytest.mark.parametrize(
    "cadence,anchor,expected",
    [
        ("quarterly", 2, datetime(2026, 5, 31, 6, tzinfo=UTC)),
        ("semiannual", 2, datetime(2026, 8, 31, 6, tzinfo=UTC)),
        ("annual", 2, datetime(2027, 2, 28, 6, tzinfo=UTC)),
    ],
)
def test_calendar_cadences_keep_month_and_day_anchor(cadence, anchor, expected):
    now = datetime(2026, 2, 28, 6, tzinfo=UTC)
    assert next_run_after(now, 6, cadence, monthday=31, anchor_month=anchor) == expected
    # Missed runs advance to the next anchor, rather than drifting from today's month.
    assert (
        next_run_after(now + timedelta(days=12), 6, cadence, monthday=31, anchor_month=anchor)
        == expected
    )


def test_annual_leap_anchor_recovers_february_29():
    run = datetime(2027, 2, 28, 6, tzinfo=UTC)
    assert next_run_after(run, 6, "annual", monthday=29, anchor_month=2) == datetime(
        2028, 2, 29, 6, tzinfo=UTC
    )
    with pytest.raises(ValueError):
        next_run_after(run, 6, "annual", anchor_month=13)


AREA = {
    "geometry": {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 50], [1, 50], [1, 51], [0, 51], [0, 50]]],
                },
            }
        ],
    }
}


async def test_subscription_area_roundtrip_and_calendar_options(client: AsyncClient, user: User):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.post(
        "/api/schedules",
        headers=bearer(token),
        json={
            "name": "Coastal update",
            "template_id": "ask",
            "question": "What changed here?",
            "research_mode": "quick",
            "cadence": "semiannual",
            "anchor_month": 3,
            "monthday": 31,
            "research_area": AREA,
            "disclose_area_to_provider": True,
            "avoid_repetition": True,
        },
    )
    assert response.status_code == 201, response.text
    value = response.json()
    assert value["anchor_month"] == 3 and value["cadence"] == "semiannual"
    assert value["research_area"]["geometry"]["features"][0]["geometry"]["type"] == "Polygon"
    assert value["disclose_area_to_provider"] is True and value["avoid_repetition"] is True
    listed = (await client.get("/api/schedules", headers=bearer(token))).json()["items"][0]
    assert listed == value


@pytest.mark.parametrize(
    "changes",
    [
        {"hazard": "invented"},
        {"anchor_month": 0},
        {"avoid_repetition": "yes"},
        {"research_area": AREA, "country_iso": "GB"},
        {"research_area": AREA, "conflict_id": "ukraine"},
        {"research_area": AREA, "disclose_area_to_provider": False},
    ],
)
async def test_invalid_subscription_scope_rejected(client: AsyncClient, user: User, changes):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.post(
        "/api/schedules",
        headers=bearer(token),
        json={
            "name": "Update",
            "template_id": "ask",
            "question": "What changed?",
            "research_mode": "quick",
            **changes,
        },
    )
    assert response.status_code == 422


def test_content_comparison_survives_recapture_and_detects_changed_facts():
    event = make_event(title="A port closes", summary="The port closed today")
    frozen = EvidenceItem.from_event("E1", event, NOW, source_name="Test", independence_key="test")
    assert content_signature(event) == content_signature(frozen)
    recaptured = replace(
        event,
        id="new-id",
        observed_at=NOW + timedelta(days=1),
        url="https://example.com/mirror",
        content_hash="random",
    )
    assert content_signature(recaptured) == content_signature(frozen)
    assert content_signature(replace(event, summary="The port reopened")) != content_signature(
        frozen
    )


def test_new_relevant_evidence_wins_budget_without_excluding_context():
    store = InMemoryEventStore()
    old = make_event("old", title="Port access update", summary="Port closed")
    new = make_event("new", title="Port reopened", summary="Operations resume")
    unrelated = make_event("unrelated", title="Football match", summary="Local football result")
    store.upsert([old, new, unrelated])
    selected = select_evidence(
        store,
        {},
        EvidenceStrategy(frozenset(), 48, 1, 10),
        now=NOW,
        terms=("port",),
        seen_content_signatures=frozenset({content_signature(old)}),
    )
    assert [item.event_id for item in selected.items] == [new.id]
    wider = select_evidence(
        store,
        {},
        EvidenceStrategy(frozenset(), 48, 2, 10),
        now=NOW,
        terms=("port",),
        seen_content_signatures=frozenset({content_signature(old)}),
    )
    assert [item.event_id for item in wider.items] == [new.id, old.id]


def test_update_guidance_states_no_change_and_deleted_baseline_limits():
    _, previous = document_records()
    guidance = update_guidance(previous, previous.evidence)
    assert "New or changed captured items: none" in guidance
    assert "No material update was identified" in guidance
    assert "Never claim nothing happened" in guidance
    deleted = update_guidance(None, (), previous_missing=True)
    assert "previous report is unavailable" in deleted


@pytest.mark.parametrize("status", [ReportStatus.READY, ReportStatus.FAILED])
async def test_empty_and_failed_editions_preserve_novelty_history(
    container: Container, user: User, status
):
    schedule = await schedule_for(container, user)
    first, _ = await save_report(container, user)
    await mark(container, schedule, first)
    baseline = await refresh(container, user, schedule.id)
    assert baseline.seen_content_signatures and baseline.baseline_report_id == first.id
    empty, version = document_records(user.id)
    empty.status = status
    version = replace(version, evidence=(), status=status)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(empty, version)
        await session.commit()
    await mark(container, baseline, empty)
    updated = await refresh(container, user, schedule.id)
    assert updated.seen_content_signatures == baseline.seen_content_signatures
    assert updated.baseline_report_id == first.id
    request = scheduled_report_request(updated)
    assert request.subscription_previous_report_id == first.id
    assert request.subscription_seen_signatures == baseline.seen_content_signatures


async def test_subscription_history_is_bounded_and_scope_changes_clear_it(
    container: Container, user: User
):
    schedule = await schedule_for(container, user)
    async with container.session_factory() as session:
        row = await session.get(ScheduleRow, schedule.id)
        row.research_options = {
            **row.research_options,
            "seen_content_signatures": [f"{n:064x}" for n in range(500)],
        }
        await session.commit()
    schedule = await refresh(container, user, schedule.id)
    report, _ = await save_report(container, user)
    await mark(container, schedule, report)
    updated = await refresh(container, user, schedule.id)
    assert len(updated.seen_content_signatures) == 500
    changed = build_schedule(
        ScheduleInput(
            name="Other",
            template_id="ask",
            question="Other topic?",
            research_mode=ResearchMode.QUICK,
        ),
        schedule_id=updated.id,
        owner=user.id,
        created=NOW,
        now=NOW,
        previous=updated,
    )
    assert changed.seen_content_signatures == () and changed.baseline_report_id is None


async def test_baseline_never_crosses_personal_scope_and_deleted_baseline_is_explicit(
    container: Container, user: User
):
    schedule = await schedule_for(container, user)
    foreign, _ = document_records(uuid4())
    # A fake repository isolates the authorisation boundary without inserting an orphan owner.

    repository = SimpleNamespace(get=AsyncMock(return_value=foreign), get_version=AsyncMock())
    request = scheduled_report_request(replace(schedule, last_report_id=foreign.id))
    async with container.session_factory() as session:
        with pytest.raises((Forbidden, InvalidRequest, NotFound)):
            await load_subscription_baseline(
                container.access_policy(session), repository, user, request
            )
        repository.get_version.assert_not_called()
        repository.get.return_value = None
        assert (
            await load_subscription_baseline(
                container.access_policy(session), repository, user, request
            )
            is None
        )
