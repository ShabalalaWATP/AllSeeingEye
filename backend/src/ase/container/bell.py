"""Notification bell factories: summary, destinations, acknowledgement and preferences."""

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.annotation_monitors import SqlAnnotationMonitorRepository
from ase.adapters.persistence.bell import SqlBellAlertQueries, SqlBellPreferenceRepository
from ase.application.bell.alerts import BellAcknowledgements, BellAlerts
from ase.application.bell.preferences import BellPreferencesService
from ase.application.bell.scope import BellSignals
from ase.application.bell.summary import BellService
from ase.application.warning.alerts import AcknowledgeAlertUseCase
from ase.container.core import ContainerCore


class BellWiring(ContainerCore):
    def bell_signals(self) -> BellSignals:
        return BellSignals(self.bus)

    def bell_alerts(self, session: AsyncSession) -> BellAlerts:
        repos = self.repositories(session)
        return BellAlerts(
            SqlBellAlertQueries(session),
            repos.alerts,
            repos.reports,
            SqlAnnotationMonitorRepository(session),
            self.access_policy(session),
            self.clock,
        )

    def bell(self, session: AsyncSession) -> BellService:
        return BellService(
            self.bell_alerts(session),
            SqlBellPreferenceRepository(session),
            self.access_policy(session),
        )

    def bell_acknowledgements(self, session: AsyncSession) -> BellAcknowledgements:
        repos = self.repositories(session)
        access = self.access_policy(session)
        return BellAcknowledgements(
            repos.alerts,
            AcknowledgeAlertUseCase(
                repos.alerts, self.clock, self._auditor(repos), repos.uow, access
            ),
            access,
            repos.uow,
            self.bell_signals(),
        )

    def bell_preferences(self, session: AsyncSession) -> BellPreferencesService:
        repos = self.repositories(session)
        return BellPreferencesService(
            SqlBellPreferenceRepository(session),
            repos.indicators,
            self.access_policy(session),
            self.clock,
            repos.uow,
            self.bell_signals(),
        )
