"""Account and per-subscription opt-ins always apply to the current account only."""

from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.ports.notification_delivery import NotificationPreferenceRepository
from ase.application.ports.repositories import UnitOfWork
from ase.application.ports.schedules import ScheduleRepository
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.notification_delivery import EmailPreferences, SubscriptionEmailPreferences
from ase.domain.users import User


class NotificationPreferences:
    def __init__(
        self,
        repository: NotificationPreferenceRepository,
        schedules: ScheduleRepository,
        access: AccessPolicy,
        uow: UnitOfWork,
    ) -> None:
        self._repository, self._schedules = repository, schedules
        self._access, self._uow = access, uow

    async def email(self, actor: User) -> tuple[EmailPreferences, bool]:
        await self._access.context(actor)
        return await self._repository.email(actor.id), await self._repository.email_confirmed(
            actor.id
        )

    async def save_email(self, actor: User, preferences: EmailPreferences) -> None:
        await self._access.context(actor, for_update=True)
        if preferences.enabled and not await self._repository.email_confirmed(actor.id):
            raise InvalidRequest(
                "Confirm email ownership by enrolling email verification in Security first."
            )
        await self._repository.save_email(actor.id, preferences)
        await self._uow.commit()

    async def subscription(
        self,
        actor: User,
        subscription_id: UUID,
    ) -> SubscriptionEmailPreferences:
        await self._check_subscription(actor, subscription_id, write=False)
        return await self._repository.subscription(actor.id, subscription_id)

    async def save_subscription(
        self,
        actor: User,
        subscription_id: UUID,
        preferences: SubscriptionEmailPreferences,
    ) -> None:
        await self._check_subscription(actor, subscription_id, write=True)
        await self._repository.save_subscription(actor.id, subscription_id, preferences)
        await self._uow.commit()

    async def _check_subscription(self, actor: User, subscription_id: UUID, *, write: bool) -> None:
        access = await self._access.context(actor, for_update=write)
        schedule = await self._schedules.get(subscription_id)
        if schedule is None or schedule.archived_at is not None:
            raise NotFound()
        access.require_read(schedule.created_by, schedule.team_id)
        # An administrator's inspection permission does not opt them into others' data.
        if schedule.team_id is None and schedule.created_by != actor.id:
            raise NotFound()
        if schedule.team_id is not None and schedule.team_id not in access.memberships:
            raise NotFound()
