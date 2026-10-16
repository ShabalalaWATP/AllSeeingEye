"""Synthetic saved graphs and explicit operator decisions for privacy regression tests."""

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import update

from ase.adapters.persistence.models import ScheduleRow, UserRow
from ase.adapters.persistence.research_briefs import SqlResearchBriefRepository
from ase.adapters.persistence.selected_index_models import SelectedIndexGateRow
from ase.adapters.persistence.subscription_edition_models import (
    SubscriptionEditionRow,
)
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.schedules.manage import ScheduleInput
from ase.application.schedules.revision_snapshot import revision_from_schedule
from ase.domain.private_removal import ReviewDecision, ReviewPurpose
from ase.domain.research import ResearchMode
from ase.domain.research_brief import ResearchBrief
from ase.domain.research_brief_scope import BriefCollection, BriefObservation, BriefScope
from ase.domain.research_brief_values import (
    BriefIdentity,
    BriefLens,
    BriefLimits,
    BriefMonitoring,
    BriefOutput,
    BriefQuestion,
)
from report_documents_helpers import document_records
from team_helpers import CONTEXT


async def authorise(container, admin, owner, *, inactive=False, decision=ReviewDecision.REMOVE):
    async with container.session_factory() as session:
        if inactive:
            await session.execute(
                update(UserRow).where(UserRow.id == owner.id).values(is_active=False)
            )
            await session.commit()
        return await container.private_removal(session).review(
            admin, owner.id, decision, ReviewPurpose.RIGHTS_REQUEST, 0
        )


async def report(container, owner, **changes):
    record, version = document_records(owner.id)
    for name, value in changes.items():
        setattr(record, name, value)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    return record, version


async def preview(container, admin, request):
    async with container.session_factory() as session:
        return await container.private_removal(session).preview(admin, request)


async def apply(container, admin, request, fingerprint):
    async with container.session_factory() as session:
        return await container.private_removal(session).apply(admin, request, fingerprint)


async def subscription(container, owner, *, archived=True, report_id=None, job_id=None):
    now = container.clock.now()
    async with container.session_factory() as session:
        schedule = await container.create_schedule(session).execute(
            owner,
            ScheduleInput(
                name="Private schedule", template_id="intsum", country_iso="UA", cadence="daily"
            ),
            CONTEXT,
        )
    async with container.session_factory() as session:
        if await session.get(SelectedIndexGateRow, 1) is None:
            session.add(SelectedIndexGateRow(id=1, revision=1))
        await session.execute(
            update(ScheduleRow)
            .where(ScheduleRow.id == schedule.id)
            .values(enabled=not archived, archived_at=now if archived else None)
        )
        revision = revision_from_schedule(schedule, 1)
        await SqlSubscriptionEditionRepository(session).add_revision(revision)
        edition = SubscriptionEditionRow(
            id=uuid4(),
            subscription_id=schedule.id,
            trigger="scheduled",
            due_at_utc=now,
            request_uuid=None,
            frozen_revision=1,
            requested_start=now - timedelta(days=1),
            requested_end=now,
            effective_intervals=[],
            gaps=[],
            compatibility_fingerprint=revision.compatibility_fingerprint,
            baseline_version_id=None,
            workflow="completed",
            report_quality="absent",
            coverage="unknown",
            created_at=now,
            updated_at=now,
            revision=1,
            job_id=job_id,
            report_id=report_id,
            version_id=None,
            safe_reason=None,
            covered_by_edition_id=None,
            accepted_as_baseline=False,
        )
        session.add(edition)
        await session.commit()
    return schedule, edition


async def brief(container, owner, *, scope=None):
    now = container.clock.now()
    value = ResearchBrief(
        identity=BriefIdentity(uuid4(), 1, owner.id, "Private brief", now, now),
        question=BriefQuestion("What changed?"),
        scope=scope or BriefScope(),
        observation=BriefObservation(policy="template_default"),
        lens=BriefLens(),
        collection=BriefCollection(),
        output=BriefOutput(depth=ResearchMode.QUICK),
        limits=BriefLimits(),
        monitoring=BriefMonitoring(),
    )
    async with container.session_factory() as session:
        await SqlResearchBriefRepository(session).add_revision(value, actor_id=owner.id)
        await session.commit()
    return value
