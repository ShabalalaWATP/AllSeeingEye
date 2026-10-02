"""Read a rule's warm-up status under its current personal or team access."""

from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.ports import Clock
from ase.application.ports.warning import IndicatorBaselineStore, IndicatorRepository
from ase.domain.errors import NotFound
from ase.domain.indicator_baseline import IndicatorBaseline
from ase.domain.users import User


class IndicatorBaselineView:
    def __init__(
        self,
        indicators: IndicatorRepository,
        baselines: IndicatorBaselineStore,
        access: AccessPolicy,
        clock: Clock,
    ) -> None:
        self.indicators, self.baselines, self.access, self.clock = (
            indicators,
            baselines,
            access,
            clock,
        )

    async def execute(self, actor: User, indicator_id: UUID) -> IndicatorBaseline:
        access = await self.access.context(actor)
        rule = await self.indicators.get(indicator_id)
        if rule is None:
            raise NotFound()
        access.require_read(rule.created_by, rule.team_id)
        result = await self.baselines.summary(rule, self.clock.now())
        access = await self.access.context(actor)
        access.require_read(rule.created_by, rule.team_id)
        return result
