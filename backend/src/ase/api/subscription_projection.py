"""Resolve report URLs for already-authorised subscription responses before release."""

from collections.abc import Mapping, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ase.api.schemas_schedules import ScheduleOut
from ase.api.schemas_subscription_editions import SubscriptionEditionOut
from ase.container import Container
from ase.domain.schedules import Schedule
from ase.domain.subscription_comparisons import EditionComparison
from ase.domain.subscription_editions import SubscriptionEdition
from ase.domain.users import User

type Reference = tuple[UUID | None, UUID | None]


async def _numbers(
    container: Container, session: AsyncSession, actor: User, references: Sequence[Reference]
) -> dict[Reference, int]:
    exact = {(report, version) for report, version in references if report and version}
    if not exact:
        return {}
    access = await container.access_policy(session).context(actor)
    resolved = await container.repositories(session).reports.version_numbers(
        access.visibility, exact
    )
    return {(report, version): number for (report, version), number in resolved.items()}


async def schedule_outputs(
    container: Container, session: AsyncSession, actor: User, schedules: Sequence[Schedule]
) -> list[ScheduleOut]:
    references = [(item.last_report_id, item.last_version_id) for item in schedules]
    references += [
        (item.last_change.previous_report_id, item.last_change.previous_version_id)
        for item in schedules
        if item.last_change
    ]
    numbers = await _numbers(container, session, actor, references)
    return [
        ScheduleOut.from_schedule(
            item,
            last_version_number=numbers.get((item.last_report_id, item.last_version_id)),
            previous_version_number=numbers.get(
                (item.last_change.previous_report_id, item.last_change.previous_version_id)
            )
            if item.last_change
            else None,
        )
        for item in schedules
    ]


async def edition_outputs(
    container: Container,
    session: AsyncSession,
    actor: User,
    editions: Sequence[SubscriptionEdition],
    comparisons: Mapping[UUID, EditionComparison] | None = None,
) -> list[SubscriptionEditionOut]:
    numbers = await _numbers(
        container, session, actor, [(item.report_id, item.version_id) for item in editions]
    )
    return [
        SubscriptionEditionOut.from_edition(
            item,
            comparisons.get(item.id) if comparisons else None,
            version_number=numbers.get((item.report_id, item.version_id)),
        )
        for item in editions
    ]
