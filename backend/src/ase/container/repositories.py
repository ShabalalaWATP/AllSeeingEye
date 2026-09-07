"""Repository bundle and session-scoped adapter construction for the composition root."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.audit import SqlAlchemyUnitOfWork, SqlAuditLogRepository
from ase.adapters.persistence.baselines import SqlBaselineRepository
from ase.adapters.persistence.claims import SqlClaimRepository
from ase.adapters.persistence.direction import SqlAoiRepository, SqlPlanRepository
from ase.adapters.persistence.llm import SqlLlmProfileRepository, SqlLlmUsageRepository
from ase.adapters.persistence.llm_bindings import SqlLlmBindingRepository
from ase.adapters.persistence.map_views import SqlMapViewRepository
from ase.adapters.persistence.reports import SqlReportRepository
from ase.adapters.persistence.schedules import SqlScheduleRepository
from ase.adapters.persistence.tokens import SqlPasswordTokenRepository, SqlRefreshTokenRepository
from ase.adapters.persistence.users import SqlAccountRequestRepository, SqlUserRepository
from ase.adapters.persistence.warning import SqlAlertRepository, SqlIndicatorRepository
from ase.application.ports import (
    AccountRequestRepository,
    AuditLogRepository,
    PasswordTokenRepository,
    RefreshTokenRepository,
    UnitOfWork,
    UserRepository,
)
from ase.application.ports.baselines import BaselineRepository
from ase.application.ports.claims import ClaimRepository
from ase.application.ports.direction import AoiRepository, PlanRepository
from ase.application.ports.llm import (
    LlmBindingRepository,
    LlmProfileRepository,
    LlmUsageRepository,
)
from ase.application.ports.map_views import MapViewRepository
from ase.application.ports.reports import ReportRepository
from ase.application.ports.schedules import ScheduleRepository
from ase.application.ports.warning import AlertRepository, IndicatorRepository


@dataclass(slots=True)
class Repositories:
    users: UserRepository
    requests: AccountRequestRepository
    refresh_tokens: RefreshTokenRepository
    password_tokens: PasswordTokenRepository
    audit: AuditLogRepository
    llm_profiles: LlmProfileRepository
    llm_usage: LlmUsageRepository
    llm_bindings: LlmBindingRepository
    reports: ReportRepository
    claims: ClaimRepository
    map_views: MapViewRepository
    baselines: BaselineRepository
    aois: AoiRepository
    plans: PlanRepository
    indicators: IndicatorRepository
    alerts: AlertRepository
    schedules: ScheduleRepository
    uow: UnitOfWork


def build_repositories(session: AsyncSession) -> Repositories:
    return Repositories(
        claims=SqlClaimRepository(session),
        users=SqlUserRepository(session),
        requests=SqlAccountRequestRepository(session),
        refresh_tokens=SqlRefreshTokenRepository(session),
        password_tokens=SqlPasswordTokenRepository(session),
        audit=SqlAuditLogRepository(session),
        llm_profiles=SqlLlmProfileRepository(session),
        llm_usage=SqlLlmUsageRepository(session),
        llm_bindings=SqlLlmBindingRepository(session),
        reports=SqlReportRepository(session),
        map_views=SqlMapViewRepository(session),
        baselines=SqlBaselineRepository(session),
        aois=SqlAoiRepository(session),
        plans=SqlPlanRepository(session),
        indicators=SqlIndicatorRepository(session),
        alerts=SqlAlertRepository(session),
        schedules=SqlScheduleRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )
