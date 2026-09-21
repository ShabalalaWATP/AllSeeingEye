"""Composition of subscription admission, with no execution policy in the container."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.subscription_admission import (
    SqlSubscriptionDueQueue,
    SqlSubscriptionTransactions,
    sql_session_check,
)
from ase.application.schedules.subscription_enqueue import SubscriptionAdmission as AdmissionService

if TYPE_CHECKING:
    from ase.container import Container


class SubscriptionAdmission(AdmissionService):
    """Compatibility factory for existing container consumers and scheduled workers."""

    session_check = staticmethod(sql_session_check)

    def __init__(self, container: Container) -> None:
        async def research_available(session: AsyncSession, owner_id: UUID, now: datetime) -> bool:
            remaining = (await container.research_usage(session).allowance(owner_id, now)).remaining
            return remaining is None or remaining > 0

        super().__init__(
            SqlSubscriptionTransactions(
                container.session_factory,
                container.access_policy,
                container.report_jobs,
                lambda session: container._auditor(container.repositories(session)),
                research_available,
            ),
            SqlSubscriptionDueQueue(container.session_factory, container.access_policy),
            container.clock,
            container.source_admission.guard,
        )
