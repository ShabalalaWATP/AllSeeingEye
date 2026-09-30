"""Caller-owned publication transaction spanning editions, comparisons and schedule projection."""

from typing import Protocol
from uuid import UUID

from ase.application.access import AccessContext
from ase.application.ports.subscription_editions import SubscriptionEditionRepository
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.schedules import Schedule, ScheduleRunResult
from ase.domain.subscription_comparisons import EditionComparison
from ase.domain.subscription_editions import SubscriptionEdition


class SubscriptionPublication(Protocol):
    @property
    def editions(self) -> SubscriptionEditionRepository: ...
    async def baseline(self, version_id: UUID) -> tuple[ReportRecord, ReportVersion] | None: ...
    async def schedule(self, subscription_id: UUID) -> Schedule | None: ...
    async def add_comparison(self, comparison: EditionComparison) -> None: ...
    async def project_outcome(
        self, edition: SubscriptionEdition, result: ScheduleRunResult, access: AccessContext
    ) -> bool: ...
