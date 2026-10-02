"""Export authority is stricter than reading a team's rule or editing one's own rule."""

from uuid import UUID, uuid4

from ase.application.access import AccessContext, AccessPolicy
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.alert_routing import AlertRoutingRepository, AlertWebhookValidator
from ase.application.ports.warning import IndicatorRepository
from ase.domain.alert_routing import AlertRoute, AlertWebhookDestination
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound
from ase.domain.teams import MembershipRole
from ase.domain.users import User
from ase.domain.warning import Indicator


def require_export(access: AccessContext, owner: UUID, team_id: UUID | None) -> None:
    access.require_write(owner, team_id)
    if team_id is not None:
        team = access.teams.get(team_id)
        if team is None or not team.is_active:
            raise Forbidden("External routing requires an active team.")
        if (
            not access.actor.is_admin
            and access.memberships.get(team_id) is not MembershipRole.MANAGER
        ):
            raise Forbidden("Only team managers can route team alerts outside the application.")


class AlertRoutingService:
    def __init__(
        self,
        routes: AlertRoutingRepository,
        indicators: IndicatorRepository,
        access: AccessPolicy,
        validator: AlertWebhookValidator,
        clock: Clock,
        uow: UnitOfWork,
        auditor: Auditor,
    ) -> None:
        self._routes, self._indicators, self._access = routes, indicators, access
        self._validator, self._clock, self._uow = validator, clock, uow
        self._auditor = auditor

    async def get(self, actor: User, indicator_id: UUID) -> tuple[AlertRoute, bool]:
        access = await self._access.context(actor)
        indicator = await self._indicator(indicator_id)
        access.require_read(indicator.created_by, indicator.team_id)
        can_manage = True
        try:
            require_export(access, indicator.created_by, indicator.team_id)
        except (Forbidden, NotFound):
            can_manage = False
        route = await self._routes.route(indicator_id)
        return route or AlertRoute(indicator_id, actor.id), can_manage

    async def save(
        self,
        actor: User,
        indicator_id: UUID,
        *,
        email_enabled: bool,
        webhook_id: UUID | None,
        expected_revision: int,
        context: RequestContext,
    ) -> AlertRoute:
        access = await self._access.context(actor, for_update=True)
        indicator = await self._indicator(indicator_id)
        require_export(access, indicator.created_by, indicator.team_id)
        previous = await self._routes.route(indicator_id)
        revision = previous.revision if previous else 0
        if revision != expected_revision:
            raise Conflict("Routing changed. Reload it before saving.")
        if webhook_id is not None:
            destination = await self._routes.destination(webhook_id)
            if destination is None or not destination.enabled:
                raise InvalidRequest("Choose an available webhook destination.")
            access.require_same_scope(
                indicator.created_by, indicator.team_id, destination.created_by, destination.team_id
            )
        route = AlertRoute(indicator_id, actor.id, email_enabled, webhook_id, revision + 1)
        await self._routes.save_route(route)
        await self._auditor.record(
            AuditAction.ALERT_ROUTING_UPDATED,
            actor=actor.id,
            subject=str(indicator_id),
            ip=context.ip,
            details={
                "email_enabled": email_enabled,
                "webhook_id": str(webhook_id) if webhook_id else None,
            },
        )
        await self._uow.commit()
        return route

    async def _indicator(self, indicator_id: UUID) -> Indicator:
        indicator = await self._indicators.get(indicator_id)
        if indicator is None:
            raise NotFound()
        return indicator

    async def destinations(
        self, actor: User, team_id: UUID | None
    ) -> list[AlertWebhookDestination]:
        access = await self._access.context(actor)
        require_export(access, actor.id, team_id)
        return await self._routes.destinations(actor.id, team_id)

    async def register_destination(
        self,
        actor: User,
        name: str,
        url: str,
        team_id: UUID | None,
        context: RequestContext,
    ) -> AlertWebhookDestination:
        require_export(await self._access.context(actor), actor.id, team_id)
        clean_name = " ".join(name.split())
        if not clean_name or len(clean_name) > 100 or len(url) > 2048:
            raise InvalidRequest("Supply a destination name and a valid HTTPS URL.")
        # DNS validation happens without the administration lock; recheck before writing.
        await self._validator.validate(url)
        access = await self._access.context(actor, for_update=True)
        require_export(access, actor.id, team_id)
        if len(await self._routes.destinations(actor.id, team_id)) >= 20:
            raise InvalidRequest("This workspace has reached its 20-webhook limit.")
        destination = AlertWebhookDestination(
            uuid4(), clean_name, actor.id, team_id, True, self._clock.now()
        )
        await self._routes.add_destination(destination, url)
        await self._auditor.record(
            AuditAction.ALERT_DESTINATION_REGISTERED,
            actor=actor.id,
            subject=str(destination.id),
            ip=context.ip,
        )
        await self._uow.commit()
        return destination

    async def remove_destination(
        self, actor: User, destination_id: UUID, context: RequestContext
    ) -> None:
        access = await self._access.context(actor, for_update=True)
        destination = await self._routes.destination(destination_id)
        if destination is None:
            raise NotFound()
        require_export(access, destination.created_by, destination.team_id)
        await self._routes.disable_destination(destination_id)
        await self._auditor.record(
            AuditAction.ALERT_DESTINATION_REMOVED,
            actor=actor.id,
            subject=str(destination_id),
            ip=context.ip,
        )
        await self._uow.commit()
