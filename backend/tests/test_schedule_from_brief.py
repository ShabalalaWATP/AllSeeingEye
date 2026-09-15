"""Brief-linked subscriptions pin exact authored settings and object authority."""

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.research_briefs import SqlResearchBriefRepository
from ase.adapters.persistence.subscription_briefs import load_schedule_brief
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.schedules.brief_link import standing_request_from_brief
from ase.application.schedules.manage import ScheduleInput, build_schedule
from ase.application.schedules.revision_snapshot import (
    request_from_revision,
    revision_from_schedule,
)
from ase.domain.errors import InvalidRequest
from ase.domain.research_brief_scope import BriefObservation
from ase.domain.research_brief_values import BriefValidationError
from ase.domain.subscription_snapshots import canonical_snapshot, decode_snapshot
from ase.domain.teams import MembershipRole
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from report_job_api_helpers import job_settings, prepared, work
from team_helpers import CONTEXT, team_service
from test_research_brief_api import _draft
from test_research_brief_persistence import _brief
from test_subscription_worker_integration import _evidence

__all__ = ["job_settings"]


def _subscription(brief_id: str, revision: int = 1) -> dict[str, object]:
    return {
        "brief_id": brief_id,
        "brief_revision": revision,
        "timezone": "Europe/London",
        "local_hour": 9,
        "local_minute": 30,
        "cadence": "daily",
        "collection_policy": "since_last_success",
    }


async def test_due_job_pins_all_requirements_and_original_brief_revision(
    client, container, user
) -> None:
    _, headers = await prepared(container, client)
    draft = _draft()
    draft["output"]["depth"] = "advanced"
    draft["observation"] = {
        "policy": "relative",
        "lookback_hours": 48,
        "since": None,
        "until": None,
        "time_basis": None,
        "forecast_horizon_days": None,
    }
    draft["question"]["requirements"] = [
        {"id": f"IR-{index}", "question": f"Question {index}?", "required": True, "priority": index}
        for index in range(1, 13)
    ]
    saved = await client.post("/api/research/briefs", json=draft, headers=headers)
    assert saved.status_code == 201, saved.text
    brief_id = saved.json()["brief"]["identity"]["id"]
    created = await client.post(
        "/api/schedules/from-brief", json=_subscription(brief_id), headers=headers
    )
    assert created.status_code == 201, created.text
    schedule = created.json()
    assert (schedule["brief_id"], schedule["brief_revision"]) == (brief_id, 1)
    assert schedule["window_hours"] == 48
    assert schedule["next_three"][0]["local"].endswith("09:30:00+01:00")

    revised = deepcopy(draft)
    revised["base_revision"] = 1
    revised["question"]["main"] = "A new question for later subscriptions?"
    assert (
        await client.post(
            f"/api/research/briefs/{brief_id}/revisions", json=revised, headers=headers
        )
    ).status_code == 201
    due = datetime.fromisoformat(schedule["next_run_at"])
    container.clock.advance(due - container.clock.now() + timedelta(minutes=1))
    assert await container.schedule_runner.run_once() == 1
    assert await container.schedule_runner.run_once() == 0
    async with container.session_factory() as session:
        edition = (await SqlSubscriptionEditionRepository(session).history(UUID(schedule["id"])))[0]
        frozen = await SqlSubscriptionEditionRepository(session).get_revision(
            edition.subscription_id, edition.frozen_revision
        )
        job = await SqlReportJobRepository(session).get(edition.job_id)
    assert frozen is not None and job is not None
    assert frozen.brief_revision_id == UUID(brief_id)
    assert (job.brief_id, job.brief_revision) == (UUID(brief_id), 1)
    restored = request_from_revision(frozen)
    assert [item.id for item in restored.canonical_requirements] == [
        f"IR-{index}" for index in range(1, 13)
    ]
    assert restored.question == draft["question"]["main"]
    assert job.payload["input"]["scope"]["research_until"] == edition.requested.end.isoformat()
    async with container.session_factory() as session:
        current = await container.repositories(session).schedules.get(UUID(schedule["id"]))
        assert current is not None
        access = await container.access_policy(session).background(user.id, None)
        original_brief = await load_schedule_brief(session, access, current)
    assert original_brief is not None
    later = revision_from_schedule(
        current,
        frozen.revision + 1,
        created_at=container.clock.now() + timedelta(days=7),
        brief=original_brief,
    )
    assert later.compatibility_fingerprint == frozen.compatibility_fingerprint
    _evidence(container, "brief-edition")
    await work(container)
    async with container.session_factory() as session:
        saved = await container.repositories(session).reports.get_version(job.report_id, 1)
    assert saved is not None
    assert (saved.brief_id, saved.brief_revision) == (UUID(brief_id), 1)
    assert [item.id for item in saved.canonical_requirements] == [
        f"IR-{index}" for index in range(1, 13)
    ]


async def test_brief_subscription_requires_current_personal_or_team_scope(
    client, container, user, admin
) -> None:
    owner_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    owner_headers = bearer(owner_token)
    private = await client.post("/api/research/briefs", json=_draft(), headers=owner_headers)
    assert private.status_code == 201
    private_id = private.json()["brief"]["identity"]["id"]
    other = await create_user(
        container, email="subscription-other@example.com", password="another-long-passphrase"
    )
    other_headers = bearer(await login_token(client, other.email, "another-long-passphrase"))
    denied = await client.post(
        "/api/schedules/from-brief", json=_subscription(private_id), headers=other_headers
    )
    assert denied.status_code == 404
    missing = await client.post(
        "/api/schedules/from-brief", json=_subscription(private_id, 2), headers=owner_headers
    )
    assert missing.status_code == 404

    async with team_service(container) as service:
        team = await service.create(admin, "Brief subscriptions", CONTEXT)
        await service.set_member(
            admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
        await service.set_member(
            admin, team.id, email=other.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
    team_draft = {**_draft(), "team_id": str(team.id)}
    shared = await client.post("/api/research/briefs", json=team_draft, headers=owner_headers)
    assert shared.status_code == 201, shared.text
    shared_id = shared.json()["brief"]["identity"]["id"]
    accepted = await client.post(
        "/api/schedules/from-brief", json=_subscription(shared_id), headers=other_headers
    )
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["team_id"] == str(team.id)


async def test_unsupported_or_transient_brief_is_rejected_before_schedule_creation(
    client, container, user
) -> None:
    _, headers = await prepared(container, client)
    cases = []
    transient = _draft()
    transient["private_inputs"] = [
        {
            "kind": "session",
            "input_id": str(uuid4()),
            "report_id": None,
            "report_version": None,
            "expires_at": None,
            "disclose_to_provider": False,
        }
    ]
    cases.append(transient)
    unsupported = _draft()
    unsupported["lens"]["audience"] = "Sensitive audience instructions"
    cases.append(unsupported)
    for index, draft in enumerate(cases):
        saved = await client.post("/api/research/briefs", json=draft, headers=headers)
        assert saved.status_code == 201, (index, saved.text)
        brief_id = saved.json()["brief"]["identity"]["id"]
        blocked = await client.post(
            "/api/schedules/from-brief", json=_subscription(brief_id), headers=headers
        )
        assert blocked.status_code == 422, blocked.text
        assert "Sensitive audience instructions" not in blocked.text
        if index == 1:
            assert "lens.audience" in blocked.json()["error"]["fields"]
            once = await client.post(
                "/api/report-jobs/from-brief",
                json={"request_id": str(uuid4()), "brief_id": brief_id, "revision": 1},
                headers=headers,
            )
            assert once.status_code == 422
            assert "lens.audience" in once.json()["error"]["fields"]
    schedules = await client.get("/api/schedules", headers=headers)
    assert schedules.json()["items"] == []


def test_explicit_historical_brief_cannot_become_a_repeating_window() -> None:
    brief = _brief()
    fixed = replace(
        brief,
        observation=BriefObservation(
            policy="explicit",
            since=datetime(2026, 8, 1, tzinfo=UTC),
            until=datetime(2026, 8, 31, tzinfo=UTC),
        ),
    )
    with pytest.raises(BriefValidationError, match="relative or template-default"):
        standing_request_from_brief(fixed, now=datetime(2026, 9, 1, tzinfo=UTC))


def test_old_subscription_snapshot_without_requirement_metadata_still_restores() -> None:
    now = datetime(2026, 9, 1, tzinfo=UTC)
    schedule = build_schedule(
        ScheduleInput(name="Original", template_id="intsum"),
        schedule_id=uuid4(),
        owner=uuid4(),
        created=now,
        now=now,
    )
    revision = revision_from_schedule(schedule, 1)
    snapshot = decode_snapshot(revision.request_snapshot)
    snapshot["request"].pop("canonical_requirements")
    old = replace(revision, request_snapshot=canonical_snapshot(snapshot))
    assert request_from_revision(old).canonical_requirements == ()


async def test_direct_update_cannot_change_a_pinned_brief_subscription(container, user) -> None:
    brief = _brief(owner_id=user.id)
    async with container.session_factory() as session:
        await SqlResearchBriefRepository(session).add_revision(brief, actor_id=user.id)
        await session.commit()
    request = standing_request_from_brief(brief, now=container.clock.now())
    async with container.session_factory() as session:
        schedule = await container.create_schedule(session).execute(
            user,
            ScheduleInput(
                name="Pinned",
                template_id=request.template_id,
                question=request.question,
                research_mode=request.research_mode,
                window_hours=request.window_hours,
                brief_id=brief.identity.id,
                brief_revision=1,
            ),
            CONTEXT,
        )
    async with container.session_factory() as session:
        with pytest.raises(InvalidRequest, match="revision-safe"):
            await container.update_schedule(session).execute(
                user,
                schedule.id,
                ScheduleInput(
                    name="Forged",
                    template_id="ask",
                    question="A different analytical scope",
                    research_mode=request.research_mode,
                    brief_id=brief.identity.id,
                    brief_revision=1,
                ),
                CONTEXT,
            )
    async with container.session_factory() as session:
        stored = await container.repositories(session).schedules.get(schedule.id)
    assert stored is not None and stored.name == "Pinned"
