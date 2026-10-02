"""Recheck current export authority, route revision, scope and opt-ins before network I/O."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.alert_routing_models import (
    AlertNotificationRow,
    AlertRoutingRow,
    AlertWebhookDestinationRow,
)
from ase.adapters.persistence.models import AlertRow, IndicatorRow
from ase.adapters.persistence.notification_preferences import SqlNotificationPreferences
from ase.adapters.persistence.warning_mapping import _alert_from_row, _indicator_from_row
from ase.application.access import AccessContext, AccessPolicy
from ase.application.ports.llm import SecretCipher
from ase.application.warning.notification_routing import require_export
from ase.domain.alert_routing import PreparedAlertDelivery
from ase.domain.errors import Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.notification_delivery import NotificationEmail
from ase.domain.warning import Indicator


class _Unavailable(Exception):
    """A fixed, non-sensitive cancellation reason, never a transport exception."""


async def prepare_alert_delivery(
    session: AsyncSession,
    outbox: AlertNotificationRow,
    access_policy: AccessPolicy,
    cipher: SecretCipher,
    *,
    installation_url: str | None,
    base_url: str,
) -> tuple[PreparedAlertDelivery | None, str | None]:
    try:
        row = await session.get(AlertRow, outbox.alert_id)
        rule = (
            await session.get(IndicatorRow, row.indicator_id) if row and row.indicator_id else None
        )
        if row is None or rule is None or not rule.enabled:
            raise _Unavailable("rule_unavailable")
        origin = (rule.created_by, rule.team_id)
        await access_policy.background(rule.created_by, rule.team_id, for_update=True)
        rule = await session.get(IndicatorRow, rule.id, populate_existing=True)
        row = await session.get(AlertRow, row.id, populate_existing=True)
        if (
            rule is None
            or row is None
            or not rule.enabled
            or (rule.created_by, rule.team_id) != origin
            or (row.created_by, row.team_id) != origin
        ):
            raise _Unavailable("scope_changed")
        alert, indicator = _alert_from_row(row), _indicator_from_row(rule)
        if outbox.channel == "installation_webhook":
            if not installation_url:
                raise _Unavailable("installation_copy_disabled")
            return PreparedAlertDelivery(alert, indicator, webhook_url=installation_url), None
        route = await session.get(AlertRoutingRow, rule.id, populate_existing=True)
        if route is None or route.revision != outbox.route_revision:
            raise _Unavailable("routing_changed")
        access = await access_policy.background(route.configured_by, rule.team_id, for_update=True)
        require_export(access, rule.created_by, rule.team_id)
        if outbox.channel == "email":
            if not route.email_enabled or str(route.configured_by) != outbox.destination_ref:
                raise _Unavailable("routing_changed")
            preferences = SqlNotificationPreferences(session)
            account = await preferences.email(route.configured_by)
            if not account.enabled or not await preferences.email_confirmed(route.configured_by):
                raise _Unavailable("email_opted_out_or_unconfirmed")
            email = _email_message(
                access.actor.email, indicator.name, alert.title, account.include_names, base_url
            )
            return PreparedAlertDelivery(alert, indicator, email=email), None
        if outbox.channel != "webhook" or str(route.webhook_id) != outbox.destination_ref:
            raise _Unavailable("routing_changed")
        url = await _webhook_url(
            session, outbox.destination_ref, indicator, access, access_policy, cipher
        )
        return PreparedAlertDelivery(alert, indicator, webhook_url=url), None
    except _Unavailable as exc:
        return None, str(exc)
    except (Forbidden, InvalidRequest, NotFound, Unauthenticated):
        return None, "access_revoked"
    except ValueError:
        return None, "destination_unavailable"


def _email_message(
    recipient: str,
    rule_name: str,
    title: str,
    include_names: bool,
    base_url: str,
) -> NotificationEmail:
    details = f"\nRule: {rule_name}\nAlert: {title}\n" if include_names else ""
    base = base_url.rstrip("/")
    return NotificationEmail(
        recipient,
        "The All Seeing Eye: alert notification",
        f"An alert rule has fired.{details}\n\nOpen securely: {base}/warning"
        f"\n\nManage email preferences: {base}/account?section=notifications",
    )


async def _webhook_url(
    session: AsyncSession,
    reference: str,
    rule: Indicator,
    access: AccessContext,
    access_policy: AccessPolicy,
    cipher: SecretCipher,
) -> str:
    destination = await session.get(
        AlertWebhookDestinationRow, UUID(reference), populate_existing=True
    )
    if destination is None or not destination.enabled:
        raise _Unavailable("destination_unavailable")
    access.require_same_scope(
        rule.created_by, rule.team_id, destination.created_by, destination.team_id
    )
    # An endpoint registered by a former manager cannot keep exporting team data.
    registered = await access_policy.background(
        destination.created_by, destination.team_id, for_update=True
    )
    require_export(registered, destination.created_by, destination.team_id)
    return cipher.decrypt(destination.url_encrypted)
