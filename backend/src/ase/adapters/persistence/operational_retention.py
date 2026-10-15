"""Bounded expiry and terminal receipt minimisation, preserving deduplication keys."""

from datetime import datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.models import AuditLogRow, LlmUsageRow
from ase.adapters.persistence.notification_digest_models import DigestDeliveryRow
from ase.adapters.persistence.subscription_edition_models import SubscriptionDeliveryRow
from ase.adapters.persistence.users import SqlUserRepository
from ase.domain.operational_retention import TERMINAL_EMAIL_STATES, OperationalRetentionPolicy
from ase.domain.subscription_monthly_budget import utc_month


class SqlOperationalRetention:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def sweep(
        self, now: datetime, policy: OperationalRetentionPolicy, *, dry_run: bool
    ) -> dict[str, int]:
        """One transaction, at most 100 changes per category, no unbounded count query.

        Preview does not take write locks. Apply serialises with admission/opt-out
        through the administration guard and rechecks every predicate on mutation.
        Delivery claims/completions also fence state, so terminal receipts stay terminal.
        """
        if policy.paused:
            return {}
        month_start, _ = utc_month(now)
        if not dry_run:
            await SqlUserRepository(self._session).lock_administration()
        counts: dict[str, int] = {}

        async def batch(
            name: str,
            model: type[Base],
            key: InstrumentedAttribute[Any],
            predicate: ColumnElement[bool],
            order: InstrumentedAttribute[Any],
            values: dict[str, None] | None = None,
        ) -> None:
            if name in policy.held_categories:
                counts[name] = 0
                return
            identifiers: list[int | UUID] = list(
                await self._session.scalars(
                    select(key).where(predicate).order_by(order, key).limit(policy.batch_size)
                )
            )
            if dry_run or not identifiers:
                counts[name] = len(identifiers)
                return
            statement = update(model).values(**values) if values is not None else delete(model)
            result = await self._session.execute(
                statement.where(key.in_(identifiers), predicate).execution_options(
                    synchronize_session=False
                )
            )
            counts[name] = int(cast("CursorResult[Any]", result).rowcount or 0)

        await batch(
            "audit",
            AuditLogRow,
            AuditLogRow.id,
            AuditLogRow.at < now - timedelta(days=policy.audit_days),
            AuditLogRow.at,
        )
        await batch(
            "llm_usage",
            LlmUsageRow,
            LlmUsageRow.id,
            LlmUsageRow.at < min(now - timedelta(days=policy.usage_days), month_start),
            LlmUsageRow.at,
        )
        expired = now - timedelta(days=policy.delivery_days)
        fields: dict[str, None] = dict.fromkeys(("lease_token", "next_attempt_at", "safe_reason"))
        email_fields = {**fields, "destination_ref": None}
        await batch(
            "subscription_email",
            SubscriptionDeliveryRow,
            SubscriptionDeliveryRow.id,
            (SubscriptionDeliveryRow.channel == "email")
            & SubscriptionDeliveryRow.state.in_(TERMINAL_EMAIL_STATES)
            & (SubscriptionDeliveryRow.updated_at < expired)
            & or_(
                *(getattr(SubscriptionDeliveryRow, field).is_not(None) for field in email_fields)
            ),
            SubscriptionDeliveryRow.updated_at,
            email_fields,
        )
        await batch(
            "digest",
            DigestDeliveryRow,
            DigestDeliveryRow.id,
            DigestDeliveryRow.state.in_((*TERMINAL_EMAIL_STATES, "empty"))
            & (DigestDeliveryRow.updated_at < expired)
            & or_(*(getattr(DigestDeliveryRow, field).is_not(None) for field in fields)),
            DigestDeliveryRow.updated_at,
            fields,
        )
        return counts
