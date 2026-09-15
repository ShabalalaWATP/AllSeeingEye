"""Scoped edition controls reuse the retained report-job transition and its CAS fence."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.domain.errors import Conflict, NotFound
from ase.domain.subscription_editions import EditionWorkflow, SubscriptionEdition

if TYPE_CHECKING:
    from ase.container import Container
    from ase.domain.users import User

EditionControl = Literal["pause", "resume", "retry"]
RESUMABLE = frozenset({EditionWorkflow.PAUSED, EditionWorkflow.BLOCKED, EditionWorkflow.RETRY_WAIT})


async def control_edition(
    container: Container,
    session: AsyncSession,
    actor: User,
    schedule_id: UUID,
    edition_id: UUID,
    action: EditionControl,
    *,
    check_session: Callable[[], Awaitable[None]],
) -> SubscriptionEdition:
    """A retry resumes the same saved job; it never creates a fresh edition."""
    await check_session()
    access = await container.access_policy(session).context(actor)
    schedule = await container.repositories(session).schedules.get(schedule_id)
    if schedule is None:
        raise NotFound("Subscription not found.")
    access.require_write(schedule.created_by, schedule.team_id)
    ledger = SqlSubscriptionEditionRepository(session)
    edition = await ledger.get(edition_id)
    if edition is None or edition.subscription_id != schedule_id:
        raise NotFound("Subscription edition not found.")
    if edition.job_id is None:
        raise Conflict("This edition has no retained report job to control.")
    if action == "pause":
        if edition.workflow not in {
            EditionWorkflow.QUEUED,
            EditionWorkflow.RUNNING,
            EditionWorkflow.PAUSED,
        }:
            raise Conflict("Only a queued or running edition can be paused.")
        await container.report_jobs(session).pause(
            actor, edition.job_id, check_session=check_session
        )
    else:
        if edition.workflow not in RESUMABLE | {
            EditionWorkflow.QUEUED,
            EditionWorkflow.RUNNING,
        }:
            raise Conflict("This edition cannot resume its retained report job.")
        if edition.workflow in RESUMABLE:
            await container.report_jobs(session).resume(
                actor, edition.job_id, check_session=check_session
            )
        else:
            await check_session()
    current = await ledger.get(edition_id)
    if current is None:
        raise Conflict("The subscription edition changed during its control request.")
    await check_session()
    return current
