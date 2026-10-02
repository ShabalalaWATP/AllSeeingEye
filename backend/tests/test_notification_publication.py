"""Real edition publication owns mail intents and their rollback, policy and replay boundaries."""

from dataclasses import replace

import pytest
from sqlalchemy import select

from ase.adapters.persistence.mfa import SqlMfaRepository
from ase.adapters.persistence.notification_delivery import SqlEditionDeliveryStore
from ase.adapters.persistence.notification_preferences import SqlNotificationPreferences
from ase.adapters.persistence.operational_models import AlertRow, ScheduleRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_edition_models import (
    SubscriptionDeliveryRow,
    SubscriptionEditionComparisonRow,
)
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.account.notification_dispatch import NotificationDispatcher
from ase.application.schedules.revision_snapshot import revision_from_schedule
from ase.container.subscription_publication import publish_subscription_edition
from ase.domain.notification_delivery import (
    EditionEmailPolicy,
    EmailPreferences,
    SubscriptionEmailPreferences,
)
from ase.domain.subscription_editions import EditionWorkflow
from report_documents_helpers import document_records
from report_job_helpers import job
from test_notification_delivery import Sender
from test_schedule_changes import mark, refresh, schedule_for
from test_subscription_comparison_projection import evidence
from test_subscription_comparison_projection import version as comparison_version
from test_subscription_editions import _edition


async def save_report(container, user, *, changed=False):
    report, _ = document_records(user.id)
    version = replace(
        comparison_version(item=evidence(digest=("b" if changed else "a") * 64)),
        report_id=report.id,
        created_at=container.clock.now(),
    )
    report.status = version.status
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(report, version)
        await session.commit()
    return report, version


async def prepare(container, user, policy, *, changed=True, notify=True):
    schedule = await schedule_for(container, user)
    async with container.session_factory() as session:
        preferences = SqlNotificationPreferences(session)
        await SqlMfaRepository(session).set_email_enabled(user.id, True)
        await preferences.save_email(user.id, EmailPreferences(True, False))
        await preferences.save_subscription(
            user.id, schedule.id, SubscriptionEmailPreferences(policy, False)
        )
        row = await session.get(ScheduleRow, schedule.id)
        row.notify_on_change = notify
        await session.commit()
    schedule = await refresh(container, user, schedule.id)
    baseline, previous = await save_report(container, user)
    await mark(container, schedule, baseline)
    schedule = await refresh(container, user, schedule.id)
    report, version = await save_report(container, user, changed=changed)
    stored = job(owner_id=user.id, report_id=report.id, version_id=version.id)
    async with container.session_factory() as session:
        await SqlReportJobRepository(session).add(stored)
        editions = SqlSubscriptionEditionRepository(session)
        frozen = await editions.add_revision(revision_from_schedule(schedule, 1))
        pending = await editions.reserve(
            replace(_edition(schedule, frozen), baseline_version_id=previous.id)
        )
        queued = await editions.advance(
            replace(pending, workflow=EditionWorkflow.QUEUED, job_id=stored.id, revision=2),
            expected_revision=1,
        )
        assert queued is not None
        await session.commit()
    container.clock.advance(queued.created_at - container.clock.now())
    return schedule, queued, stored, version


async def publish(container, user, stored, version, *, commit=True):
    async with container.session_factory() as session:
        access = await container.access_policy(session).context(user, for_update=True)
        await publish_subscription_edition(
            session, stored, version, access, container.clock.now(), research_required=False
        )
        if commit:
            await session.commit()
        else:
            # Prove the hook ran before discarding its enclosing publication transaction.
            assert list(
                await session.scalars(
                    select(SubscriptionDeliveryRow).where(
                        SubscriptionDeliveryRow.channel == "email"
                    )
                )
            )
            await session.rollback()


async def mail(container):
    async with container.session_factory() as session:
        return list(
            await session.scalars(
                select(SubscriptionDeliveryRow).where(SubscriptionDeliveryRow.channel == "email")
            )
        )


@pytest.mark.parametrize(
    "policy,changed,notify,event",
    [
        (EditionEmailPolicy.EVERY, True, True, "edition_available"),
        (EditionEmailPolicy.EVERY, False, False, "edition_available"),
        (EditionEmailPolicy.MATERIAL, True, True, "material_change"),
        (EditionEmailPolicy.MATERIAL, True, False, "material_change"),
        (EditionEmailPolicy.MATERIAL, False, False, None),
        (EditionEmailPolicy.NONE, True, False, None),
    ],
)
async def test_publication_applies_independent_mail_policy_once(
    container, user, policy, changed, notify, event
):
    _, edition, stored, version = await prepare(
        container, user, policy, changed=changed, notify=notify
    )
    await publish(container, user, stored, version)
    await publish(container, user, stored, version)
    rows = await mail(container)
    assert [(row.edition_id, row.destination_ref, row.event_kind) for row in rows] == (
        [(edition.id, user.id, event)] if event else []
    )
    sender = Sender()
    worker = NotificationDispatcher(
        SqlEditionDeliveryStore(
            container.session_factory, container.access_policy, "http://app.test"
        ),
        sender,
        container.clock,
    )
    await worker.tick()
    await worker.tick()
    assert len(sender.messages) == int(event is not None)
    if not notify:
        async with container.session_factory() as session:
            if policy is EditionEmailPolicy.NONE:
                schedule = await session.get(ScheduleRow, edition.subscription_id)
                assert schedule.last_change is None
            assert not list(await session.scalars(select(AlertRow)))
            assert not list(
                await session.scalars(
                    select(SubscriptionDeliveryRow).where(
                        SubscriptionDeliveryRow.channel == "in_app"
                    )
                )
            )


@pytest.mark.parametrize("policy", [EditionEmailPolicy.EVERY, EditionEmailPolicy.MATERIAL])
async def test_rolled_back_publication_has_no_durable_edition_or_mail_intent(
    container, user, policy
):
    schedule, edition, stored, version = await prepare(container, user, policy)
    await publish(container, user, stored, version, commit=False)
    assert await mail(container) == []
    async with container.session_factory() as session:
        current = await SqlSubscriptionEditionRepository(session).get(edition.id)
        assert current == edition
        assert await session.get(SubscriptionEditionComparisonRow, edition.id) is None
        row = await session.get(ScheduleRow, schedule.id)
        assert row.last_report_id == schedule.last_report_id
    await publish(container, user, stored, version)
    assert len(await mail(container)) == 1


@pytest.mark.parametrize("change", ["disable", "archive", "definition"])
@pytest.mark.parametrize("policy", [EditionEmailPolicy.EVERY, EditionEmailPolicy.MATERIAL])
async def test_stale_or_disabled_projection_retains_history_without_user_mail(
    container, user, change, policy
):
    schedule, edition, stored, version = await prepare(container, user, policy)
    async with container.session_factory() as session:
        row = await session.get(ScheduleRow, schedule.id)
        if change == "definition":
            row.question = "A different research question"
        else:
            row.enabled = False
            if change == "archive":
                row.archived_at = container.clock.now()
        await session.commit()
    await publish(container, user, stored, version)
    assert await mail(container) == []
    async with container.session_factory() as session:
        current = await SqlSubscriptionEditionRepository(session).get(edition.id)
        assert current.workflow is EditionWorkflow.COMPLETED
        row = await session.get(ScheduleRow, schedule.id)
        assert row.last_report_id == schedule.last_report_id
