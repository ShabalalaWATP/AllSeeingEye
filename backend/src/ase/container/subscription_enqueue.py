"""Composition of subscription admission, with no execution policy in the container."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
        super().__init__(
            SqlSubscriptionTransactions(
                container.session_factory,
                container.access_policy,
                container.report_jobs,
                lambda session: container._auditor(container.repositories(session)),
            ),
            SqlSubscriptionDueQueue(container.session_factory, container.access_policy),
            container.clock,
            container.source_admission.guard,
        )
