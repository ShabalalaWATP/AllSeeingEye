"""Filtered, cursor-paged research progress with briefing exclusion (KAN-87, KAN-94)."""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.application.report_jobs.listing import (
    JOB_STATUS_GROUPS,
    decode_job_cursor,
    encode_job_cursor,
    job_origin,
)
from ase.application.report_jobs.views import job_view
from ase.domain.access import Visibility
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from report_job_helpers import NOW, job, saved
from report_job_helpers import job_storage as _job_storage  # noqa: F401

USAGE = {
    "calls": 0,
    "max_calls": 40,
    "output_tokens": 0,
    "output_allowance": 1,
    "uncertain_calls": 0,
}


def payload(origin=None, *, focus=None, completed=0, total=0):
    scope = {} if origin is None else {"origin": origin}
    if focus is not None:
        scope["research_focus"] = focus
    return {
        "schema_version": 1,
        "summary": {
            "completed_sections": completed,
            "total_sections": total,
            "model": "fixture-model",
            "reasoning_effort": None,
            "usage": USAGE,
        },
        "input": {"scope": scope},
    }


def listed(owner, minutes, **changes):
    at = NOW + timedelta(minutes=minutes)
    return job(**({"payload": payload()} | changes), owner_id=owner, created_at=at, updated_at=at)


def test_status_groups_are_documented_partitions_of_every_job_state():
    groups = {key: set(value) for key, value in JOB_STATUS_GROUPS.items()}
    assert groups == {
        "running": {"queued", "running"},
        "attention": {"paused", "failed"},
        "finished": {"completed", "needs_review"},
    }


def test_detail_views_classify_from_the_frozen_scope():
    assert job_view(job(payload=payload("briefing")), detail=True)["origin"] == "briefing"
    assert job_origin(payload("subscription", focus="media")) == "subscription"
    assert job_origin(payload("unknown", focus="media")) == "geolocation"
    assert job_origin({"schema_version": 1, "summary": {}}) == "research"
    assert job_origin({"input": {"scope": None}}) == "research"


def test_cursor_round_trips_and_rejects_tampering():
    identity = uuid4()
    cursor = encode_job_cursor(NOW, identity)
    assert decode_job_cursor(cursor) == (NOW, identity)
    for value in ("", "not-a-cursor", cursor[:-2], "x" * 300):
        with pytest.raises(ValueError):
            decode_job_cursor(value)


async def test_filters_apply_before_limits_and_old_paused_work_is_reachable(job_storage):
    _, factory = job_storage
    owner, stranger = uuid4(), uuid4()
    old_paused = await saved(factory, listed(owner, 0, status="paused", stage="paused"))
    for minute in range(1, 130):
        await saved(factory, listed(owner, minute, status="completed", stage="completed"))
    await saved(factory, listed(stranger, 200, status="paused", stage="paused"))
    async with factory() as session:
        repository = SqlReportJobRepository(session)
        visibility = Visibility(owner, False, ())
        rows = await repository.list_page(
            visibility, limit=20, statuses=JOB_STATUS_GROUPS["attention"]
        )
        assert [row.id for row in rows] == [old_paused.id]
        assert all(row.payload["summary"]["origin"] == "research" for row in rows)
        finished = await repository.list_page(visibility, limit=100)
        assert len(finished) == 100 and old_paused.id not in {row.id for row in finished}


async def test_cursor_pages_have_stable_order_with_tied_timestamps(job_storage):
    _, factory = job_storage
    owner = uuid4()
    rows = [await saved(factory, listed(owner, 0)) for _ in range(5)]
    rows += [await saved(factory, listed(owner, -1)) for _ in range(3)]
    expected = sorted(rows[:5], key=lambda row: str(row.id)) + sorted(
        rows[5:], key=lambda row: str(row.id)
    )
    seen: list[UUID] = []
    after = None
    async with factory() as session:
        repository = SqlReportJobRepository(session)
        while True:
            page = await repository.list_page(Visibility(owner, False, ()), limit=3, after=after)
            seen += [row.id for row in page]
            if len(page) < 3:
                break
            after = (page[-1].created_at, page[-1].id)
            # A newer job arriving mid-traversal cannot shift or repeat later pages.
            await repository.add(listed(owner, 10))
    assert seen == [row.id for row in expected]


async def test_briefings_are_hidden_unless_explicitly_requested(job_storage):
    _, factory = job_storage
    owner = uuid4()
    requested = await saved(factory, listed(owner, 0))
    legacy = await saved(factory, listed(owner, -1, payload=payload(None, focus="media")))
    briefings = [
        await saved(factory, listed(owner, minute, payload=payload("briefing")))
        for minute in range(1, 4)
    ]
    async with factory() as session:
        repository = SqlReportJobRepository(session)
        visibility = Visibility(owner, False, ())
        default = await repository.list_page(visibility, limit=2)
        assert [row.id for row in default] == [requested.id, legacy.id]
        assert [row.payload["summary"]["origin"] for row in default] == ["research", "geolocation"]
        everything = await repository.list_page(visibility, limit=10, include_briefings=True)
        assert {row.id for row in everything} == {requested.id, legacy.id} | {
            row.id for row in briefings
        }


async def api_jobs(container, user_id, rows):
    async with container.session_factory() as session:
        repository = SqlReportJobRepository(session)
        for row in rows:
            await repository.add(row)
        await session.commit()


async def test_progress_api_pages_filters_and_reveals_briefings(client, container, user):
    attention = listed(user.id, 0, status="failed", stage="failed")
    briefing = listed(user.id, 5, payload=payload("briefing", completed=1, total=4))
    finished = [listed(user.id, minute, status="completed", stage="completed") for minute in (1, 2)]
    await api_jobs(container, user.id, [attention, briefing, *finished])
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))

    first = (await client.get("/api/report-jobs?limit=1", headers=headers)).json()
    assert [row["id"] for row in first["items"]] == [str(finished[1].id)]
    assert first["items"][0]["origin"] == "research" and first["next_cursor"]
    second = await client.get(
        "/api/report-jobs", params={"limit": 2, "cursor": first["next_cursor"]}, headers=headers
    )
    assert [row["id"] for row in second.json()["items"]] == [
        str(finished[0].id),
        str(attention.id),
    ]
    assert second.json()["next_cursor"] is None

    needing = (await client.get("/api/report-jobs?status=attention", headers=headers)).json()
    assert [row["id"] for row in needing["items"]] == [str(attention.id)]
    running = (await client.get("/api/report-jobs?status=running", headers=headers)).json()
    assert running["items"] == []
    revealed = (
        await client.get("/api/report-jobs?status=running&include_briefings=true", headers=headers)
    ).json()
    assert [(row["id"], row["origin"]) for row in revealed["items"]] == [
        (str(briefing.id), "briefing")
    ]


async def test_progress_api_keeps_scope_and_rejects_invalid_queries(client, container, user):
    other = await create_user(container, email="other-jobs@example.com", password=USER_PASSWORD)
    private = listed(other.id, 0, payload=payload("briefing"))
    await api_jobs(container, other.id, [private])
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    hidden = await client.get("/api/report-jobs?include_briefings=true", headers=headers)
    assert hidden.json() == {"items": [], "next_cursor": None}
    assert (await client.get(f"/api/report-jobs/{private.id}", headers=headers)).status_code == 404
    for query in ("status=unknown", "cursor=bad", "limit=0", "limit=51"):
        response = await client.get(f"/api/report-jobs?{query}", headers=headers)
        assert response.status_code == 422, query
