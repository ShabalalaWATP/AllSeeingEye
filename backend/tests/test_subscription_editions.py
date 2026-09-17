"""Edition identity and optimistic fencing across independent SQLite sessions."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.schedules.manage import ScheduleInput
from ase.application.schedules.revision_snapshot import (
    request_from_revision,
    revision_from_schedule,
)
from ase.container import Container
from ase.domain.errors import Conflict
from ase.domain.subscription_editions import (
    EditionAttempt,
    EditionCoverage,
    EditionDelivery,
    EditionQuality,
    EditionTrigger,
    EditionWorkflow,
    ObservationInterval,
    SubscriptionEdition,
    SubscriptionLineage,
    scheduled_edition_id,
)
from ase.domain.subscription_snapshots import canonical_snapshot
from ase.domain.users import User
from helpers import create_user
from team_helpers import CONTEXT


async def _revision(container: Container, owner: User):
    async with container.session_factory() as session:
        schedule = await container.create_schedule(session).execute(
            owner,
            # The window follows the cadence, so this daily case states it.
            ScheduleInput(
                name="Daily research", template_id="intsum", country_iso="UA", cadence="daily"
            ),
            CONTEXT,
        )
    revision = revision_from_schedule(schedule, 1)
    async with container.session_factory() as session:
        await SqlSubscriptionEditionRepository(session).add_revision(revision)
        await session.commit()
    return schedule, revision


def _edition(schedule, revision, *, trigger=EditionTrigger.SCHEDULED, request_uuid=None):
    due = schedule.next_run_at
    requested = ObservationInterval(due - timedelta(days=1), due)
    return SubscriptionEdition(
        id=uuid4(),
        subscription_id=schedule.id,
        trigger=trigger,
        due_at_utc=due if trigger in (EditionTrigger.SCHEDULED, EditionTrigger.CATCH_UP) else None,
        request_uuid=request_uuid,
        frozen_revision=revision.revision,
        requested=requested,
        effective_intervals=(requested,),
        gaps=(),
        compatibility_fingerprint=revision.compatibility_fingerprint,
        baseline_version_id=None,
        workflow=EditionWorkflow.PENDING,
        report_quality=EditionQuality.ABSENT,
        coverage=EditionCoverage.UNKNOWN,
        created_at=due,
        updated_at=due,
    )


async def _reserve(container: Container, edition: SubscriptionEdition) -> SubscriptionEdition:
    async with container.session_factory() as session:
        result = await SqlSubscriptionEditionRepository(session).reserve(edition)
        await session.commit()
    return result


def test_due_slot_identity_uses_utc_instant() -> None:
    subscription_id = uuid4()
    due = datetime(2026, 9, 14, 9, tzinfo=UTC)
    assert scheduled_edition_id(subscription_id, due) == scheduled_edition_id(
        subscription_id, due.astimezone(timezone(timedelta(hours=1)))
    )


async def test_revision_snapshot_restores_exact_scope_and_rejects_tampering(
    container: Container, user: User
) -> None:
    schedule, revision = await _revision(container, user)
    restored = request_from_revision(revision)
    assert restored.country_iso == schedule.country_iso
    assert restored.window_hours == 24
    assert restored.automation is True
    altered = json.loads(revision.request_snapshot)
    altered["scope"]["country"] = "GB"
    with pytest.raises(ValueError, match="scope changed"):
        request_from_revision(replace(revision, request_snapshot=canonical_snapshot(altered)))


async def test_scheduled_slot_is_idempotent_and_rejects_conflicting_payload(
    container: Container, user: User
) -> None:
    schedule, revision = await _revision(container, user)
    first = await _reserve(container, _edition(schedule, revision))
    replay = await _reserve(container, _edition(schedule, revision))
    assert replay.id == first.id
    assert replay.job_request_key == first.job_request_key
    changed = replace(
        _edition(schedule, revision),
        requested=ObservationInterval(
            first.requested.start - timedelta(hours=1), first.requested.end
        ),
    )
    with pytest.raises(Conflict, match="different frozen inputs"):
        await _reserve(container, changed)
    later = replace(
        _edition(schedule, revision),
        due_at_utc=schedule.next_run_at + timedelta(days=1),
    )
    with pytest.raises(Conflict, match="active edition"):
        await _reserve(container, later)
    async with container.session_factory() as session:
        repo = SqlSubscriptionEditionRepository(session)
        active = await repo.active(schedule.id)
        history = await repo.history(schedule.id)
    assert active == first and history == [first]


async def test_manual_request_uuid_is_scoped_to_subscription(
    container: Container, user: User
) -> None:
    other = await create_user(
        container, email="another@example.com", password="another-long-passphrase"
    )
    left, left_revision = await _revision(container, user)
    right, right_revision = await _revision(container, other)
    caller_uuid = uuid4()
    first = await _reserve(
        container,
        _edition(left, left_revision, trigger=EditionTrigger.RUN_NOW, request_uuid=caller_uuid),
    )
    second = await _reserve(
        container,
        _edition(right, right_revision, trigger=EditionTrigger.RUN_NOW, request_uuid=caller_uuid),
    )
    assert first.id != second.id
    assert first.job_request_key != second.job_request_key
    assert caller_uuid not in {first.job_request_key, second.job_request_key}
    replay = await _reserve(
        container,
        _edition(left, left_revision, trigger=EditionTrigger.RUN_NOW, request_uuid=caller_uuid),
    )
    assert replay.id == first.id
    conflicting = replace(
        _edition(left, left_revision, trigger=EditionTrigger.RUN_NOW, request_uuid=caller_uuid),
        requested=ObservationInterval(
            first.requested.start - timedelta(hours=1), first.requested.end
        ),
    )
    with pytest.raises(Conflict, match="different frozen inputs"):
        await _reserve(container, conflicting)


async def test_cosmetic_revision_snapshot_preserves_compatibility(
    container: Container, user: User
) -> None:
    schedule, revision = await _revision(container, user)
    renamed = revision_from_schedule(replace(schedule, name="Renamed"), 2)
    assert renamed.compatibility_fingerprint == revision.compatibility_fingerprint
    changed = revision_from_schedule(replace(schedule, question="A different question?"), 2)
    assert changed.compatibility_fingerprint != revision.compatibility_fingerprint


async def test_optimistic_revision_conflict_and_malformed_outcome(
    container: Container, user: User
) -> None:
    schedule, revision = await _revision(container, user)
    first = await _reserve(container, _edition(schedule, revision))
    updated = replace(
        first,
        workflow=EditionWorkflow.BLOCKED,
        safe_reason="source_unavailable",
        revision=2,
        updated_at=first.updated_at + timedelta(minutes=1),
    )
    async with container.session_factory() as session:
        repo = SqlSubscriptionEditionRepository(session)
        assert await repo.advance(updated, expected_revision=1) == updated
        await session.commit()
    async with container.session_factory() as session:
        repo = SqlSubscriptionEditionRepository(session)
        assert await repo.advance(updated, expected_revision=1) is None
        assert await repo.get(first.id) == updated
    with pytest.raises(ValueError, match="Unknown edition"):
        replace(first, report_quality="success")
    with pytest.raises(ValueError, match="safe codes"):
        replace(first, safe_reason="provider token=secret")


async def test_lineage_keeps_analytical_baseline_separate_from_coverage(
    container: Container, user: User
) -> None:
    schedule, revision = await _revision(container, user)
    interval = ObservationInterval(schedule.next_run_at - timedelta(days=1), schedule.next_run_at)
    lineage = SubscriptionLineage(
        schedule.id,
        revision.compatibility_fingerprint,
        None,
        (interval,),
        interval.end,
        interval.end,
    )
    async with container.session_factory() as session:
        repo = SqlSubscriptionEditionRepository(session)
        assert await repo.save_lineage(lineage, expected_revision=None) == lineage
        await session.commit()
    changed = replace(
        lineage,
        complete_cutoff=interval.end,
        updated_at=interval.end + timedelta(minutes=1),
        revision=2,
    )
    async with container.session_factory() as session:
        repo = SqlSubscriptionEditionRepository(session)
        assert await repo.save_lineage(changed, expected_revision=1) == changed
        await session.commit()
    async with container.session_factory() as session:
        repo = SqlSubscriptionEditionRepository(session)
        assert await repo.save_lineage(changed, expected_revision=1) is None
        assert await repo.get_lineage(schedule.id) == changed


async def test_attempt_and_delivery_history_are_bounded_and_idempotent(
    container: Container, user: User
) -> None:
    schedule, revision = await _revision(container, user)
    edition = await _reserve(container, _edition(schedule, revision))
    attempt = EditionAttempt(
        uuid4(),
        edition.id,
        None,
        1,
        "admission",
        edition.created_at,
        edition.created_at,
        "blocked",
        None,
        None,
        None,
    )
    delivery = EditionDelivery(
        uuid4(),
        edition.id,
        "in_app",
        None,
        "edition_ready",
        uuid4(),
        "pending",
        0,
        edition.created_at,
        edition.created_at,
    )
    async with container.session_factory() as session:
        repo = SqlSubscriptionEditionRepository(session)
        await repo.add_attempt(attempt)
        await repo.add_delivery(delivery)
        await session.commit()
    async with container.session_factory() as session:
        repo = SqlSubscriptionEditionRepository(session)
        assert await repo.attempts(edition.id) == [attempt]
        assert await repo.deliveries(edition.id) == [delivery]
        with pytest.raises(ValueError, match="bounded"):
            await repo.history(schedule.id, limit=101)
