"""Edition change events are atomic, deduplicated and scoped in-app reads."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.schedules.revision_snapshot import revision_from_schedule
from ase.container.subscription_publication import queue_in_app_change
from ase.domain.subscription_editions import (
    EditionCoverage,
    EditionQuality,
    EditionTrigger,
    EditionWorkflow,
    ObservationInterval,
    SubscriptionEdition,
)
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from test_schedule_changes import mark, refresh, save_report, schedule_for


async def test_change_event_is_once_and_only_visible_in_current_schedule_scope(
    client, container, user
) -> None:
    schedule = await schedule_for(container, user)
    baseline, _ = await save_report(container, user)
    await mark(container, schedule, baseline)
    schedule = await refresh(container, user, schedule.id)
    changed, version = await save_report(container, user, changed=True)
    await mark(container, schedule, changed)
    schedule = await refresh(container, user, schedule.id)
    assert schedule.last_change.status == "changed"

    now = container.clock.now()
    async with container.session_factory() as session:
        ledger = SqlSubscriptionEditionRepository(session)
        frozen = revision_from_schedule(schedule, 1)
        await ledger.add_revision(frozen)
        pending = await ledger.reserve(
            SubscriptionEdition(
                id=uuid4(),
                subscription_id=schedule.id,
                trigger=EditionTrigger.SCHEDULED,
                due_at_utc=now,
                request_uuid=None,
                frozen_revision=1,
                requested=ObservationInterval(now - timedelta(days=1), now),
                effective_intervals=(),
                gaps=(),
                compatibility_fingerprint=frozen.compatibility_fingerprint,
                baseline_version_id=None,
                workflow=EditionWorkflow.PENDING,
                report_quality=EditionQuality.ABSENT,
                coverage=EditionCoverage.UNKNOWN,
                created_at=now,
                updated_at=now,
            )
        )
        published = replace(
            pending,
            workflow=EditionWorkflow.COMPLETED,
            report_quality=EditionQuality.READY,
            job_id=uuid4(),
            report_id=changed.id,
            version_id=version.id,
            revision=2,
        )
        await queue_in_app_change(session, ledger, published, now)
        await queue_in_app_change(session, ledger, published, now)
        assert len(await ledger.deliveries(pending.id)) == 1
        await session.commit()

    owner = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    other = await create_user(
        container, email="event-outsider@example.com", password="another-long-passphrase"
    )
    outsider = bearer(await login_token(client, other.email, "another-long-passphrase"))
    endpoint = f"/api/schedules/{schedule.id}/events"
    assert (await client.get(endpoint, headers=outsider)).status_code == 404
    response = await client.get(endpoint, headers=owner)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["edition_id"] == str(pending.id)
    assert items[0]["event_kind"] == "material_change"
