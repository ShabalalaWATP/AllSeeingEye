"""Current rule access is required before revealing retained disposition counts."""

from datetime import timedelta
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.ports import Clock
from ase.application.ports.warning import AlertRepository, IndicatorRepository
from ase.domain.alert_feedback import AlertDisposition, AlertFeedback
from ase.domain.errors import NotFound
from ase.domain.users import User


class AlertFeedbackView:
    def __init__(
        self,
        alerts: AlertRepository,
        indicators: IndicatorRepository,
        access: AccessPolicy,
        clock: Clock,
    ) -> None:
        self.alerts, self.indicators, self.access, self.clock = alerts, indicators, access, clock

    async def execute(self, actor: User, indicator_id: UUID) -> AlertFeedback:
        access = await self.access.context(actor)
        rule = await self.indicators.get(indicator_id)
        if rule is None:
            raise NotFound()
        access.require_read(rule.created_by, rule.team_id)
        today = self.clock.now().replace(hour=0, minute=0, second=0, microsecond=0)
        since, until = today - timedelta(days=29), today + timedelta(days=1)
        counts = await self.alerts.feedback(rule, since, until)
        access = await self.access.context(actor)
        access.require_read(rule.created_by, rule.team_id)
        return AlertFeedback(
            indicator_id,
            since,
            until,
            counts.get(AlertDisposition.USEFUL, 0),
            counts.get(AlertDisposition.NOISE, 0),
            counts.get(AlertDisposition.DUPLICATE, 0),
        )
