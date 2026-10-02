"""Durable digest claims reuse the conservative external-mail outcome contract."""

from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.persistence.notification_digest_counts import ReviewCounter, digest_counts
from ase.adapters.persistence.notification_digest_models import (
    DigestDeliveryRow,
    DigestPreferenceRow,
)
from ase.adapters.persistence.notification_preferences import SqlNotificationPreferences
from ase.application.access import AccessPolicy
from ase.domain.access import Visibility
from ase.domain.errors import Forbidden, NotFound, Unauthenticated
from ase.domain.notification_delivery import ClaimedDelivery, DeliveryOutcome, NotificationEmail


class SqlDigestDeliveryStore:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        access: Callable[[AsyncSession], AccessPolicy],
        base_url: str,
        reviews: ReviewCounter,
    ) -> None:
        self._sessions, self._access = sessions, access
        self._base_url, self._reviews = base_url.rstrip("/"), reviews

    async def recover_uncertain(self, now: datetime) -> None:
        async with self._sessions() as session:
            await session.execute(
                update(DigestDeliveryRow)
                .where(
                    DigestDeliveryRow.state == "sending",
                    DigestDeliveryRow.updated_at < now - timedelta(minutes=2),
                )
                .values(state="uncertain", safe_reason="worker_interrupted", updated_at=now)
            )
            await session.commit()

    async def claim(self, now: datetime) -> ClaimedDelivery | None:
        async with self._sessions() as session:
            eligible = (
                DigestDeliveryRow.state.in_(("pending", "unavailable")),
                DigestDeliveryRow.attempts < 3,
                or_(
                    DigestDeliveryRow.next_attempt_at.is_(None),
                    DigestDeliveryRow.next_attempt_at <= now,
                ),
            )
            candidate = await session.scalar(
                select(DigestDeliveryRow.id)
                .where(*eligible)
                .order_by(DigestDeliveryRow.created_at, DigestDeliveryRow.id)
                .limit(1)
            )
            if candidate is None:
                return None
            lease = uuid4()
            row = await session.scalar(
                update(DigestDeliveryRow)
                .where(
                    DigestDeliveryRow.id == candidate,
                    *eligible,
                )
                .values(
                    state="sending",
                    lease_token=lease,
                    attempts=DigestDeliveryRow.attempts + 1,
                    updated_at=now,
                )
                .returning(DigestDeliveryRow)
                .execution_options(synchronize_session=False)
            )
            if row is None:
                return None
            claim = ClaimedDelivery(row.id, row.id, row.user_id, "digest", lease, row.attempts)
            await session.commit()
            return claim

    async def prepare(self, claim: ClaimedDelivery, now: datetime) -> NotificationEmail | None:
        async with self._sessions() as session:
            row = await session.get(DigestDeliveryRow, claim.id)
            if row is None or row.state != "sending" or row.lease_token != claim.lease_token:
                return None
            message = None
            reason = None
            state = "cancelled"
            try:
                access = await self._access(session).background(
                    claim.recipient_id, None, for_update=True
                )
                preferences = await session.get(
                    DigestPreferenceRow, claim.recipient_id, populate_existing=True
                )
                email = SqlNotificationPreferences(session)
                account = await email.email(claim.recipient_id)
                if preferences is None or not preferences.enabled or not account.enabled:
                    reason = "opted_out"
                elif not await email.email_confirmed(claim.recipient_id):
                    reason = "email_unconfirmed"
                else:
                    visibility = Visibility(
                        claim.recipient_id,
                        False,
                        tuple(
                            team_id
                            for team_id in access.memberships
                            if team_id in access.teams and access.teams[team_id].is_active
                        ),
                    )
                    counts = await digest_counts(
                        session, visibility, row.window_start, row.window_end, self._reviews
                    )
                    if counts.empty:
                        state, reason = "empty", "no_visible_activity"
                    else:
                        partial = (
                            " (partial: first 1,000 accessible forecasts)"
                            if counts.reviews_truncated
                            else ""
                        )
                        body = (
                            f"Activity from {row.window_start.isoformat()} inclusive to "
                            f"{row.window_end.isoformat()} exclusive (UTC).\n\n"
                            f"Alerts: {counts.alerts}\n{self._base_url}/warning\n\n"
                            f"Finished research jobs: {counts.finished}\n"
                            f"Failed research jobs: {counts.failed}\n"
                            f"{self._base_url}/research/jobs\n\n"
                            "Forecast reviews scheduled in this period: "
                            f"{counts.reviews}{partial}\n"
                            f"{self._base_url}/research/saved\n\n"
                            "Counts use currently accessible, retained records. "
                            "No titles or report text are included.\n"
                            f"Manage email preferences: {self._base_url}"
                            "/account?section=notifications"
                        )
                        message = NotificationEmail(
                            access.actor.email, "The All Seeing Eye: daily digest", body
                        )
            except (Forbidden, NotFound, Unauthenticated):
                reason = "access_revoked"
            values: dict[str, object] = {"updated_at": now}
            if reason is not None:
                values.update(state=state, safe_reason=reason)
            owned = await session.scalar(
                update(DigestDeliveryRow)
                .where(
                    DigestDeliveryRow.id == claim.id,
                    DigestDeliveryRow.state == "sending",
                    DigestDeliveryRow.lease_token == claim.lease_token,
                )
                .values(**values)
                .returning(DigestDeliveryRow.id)
            )
            await session.commit()
            return message if owned is not None else None

    async def finish(self, claim: ClaimedDelivery, outcome: DeliveryOutcome, now: datetime) -> None:
        state, attempts, reason, next_attempt = outcome.value, claim.attempts, None, None
        if outcome is DeliveryOutcome.RETRYABLE:
            state = "pending" if attempts < 3 else "failed"
            reason, next_attempt = "transport_rejected", now + timedelta(minutes=5 * attempts)
        elif outcome is DeliveryOutcome.UNAVAILABLE:
            attempts -= 1
            reason, next_attempt = "email_not_configured", now + timedelta(minutes=15)
        elif outcome is DeliveryOutcome.UNCERTAIN:
            reason = "acceptance_unknown"
        async with self._sessions() as session:
            await session.execute(
                update(DigestDeliveryRow)
                .where(
                    DigestDeliveryRow.id == claim.id,
                    DigestDeliveryRow.state == "sending",
                    DigestDeliveryRow.lease_token == claim.lease_token,
                )
                .values(
                    state=state,
                    attempts=attempts,
                    safe_reason=reason,
                    next_attempt_at=next_attempt,
                    updated_at=now,
                )
            )
            await session.commit()
