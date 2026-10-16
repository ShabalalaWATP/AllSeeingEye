"""Bounded, account-locked erasure of terminal authentication records."""

from datetime import datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import SQLColumnExpression, delete, exists, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, aliased
from sqlalchemy.sql.elements import ColumnElement

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.mfa_models import MfaChallengeRow
from ase.adapters.persistence.models import AccountRequestRow, PasswordTokenRow, RefreshTokenRow
from ase.adapters.persistence.session_activity import RefreshFamilyActivityRow
from ase.adapters.persistence.token_families import RefreshFamilyRevocationRow
from ase.adapters.persistence.totp import AdminTotpRow
from ase.adapters.persistence.users import SqlUserRepository
from ase.adapters.persistence.web_push_models import PushDeliveryRow, PushDeviceRow
from ase.domain.auth_retention import FAMILY_RETENTION, LINK_RETENTION, AuthRetentionPolicy


class SqlAuthRetention:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def sweep(
        self, now: datetime, policy: AuthRetentionPolicy, *, dry_run: bool
    ) -> dict[str, int]:
        """Apply at most batch_size changes per category; the caller owns the transaction.

        Apply holds the administration guard before account locks. Existing auth flows
        hold account locks, so predicates are checked again after waiting for them.
        Preview takes no write locks and reports only bounded current candidates.
        """
        if policy.paused:
            return {}
        if not dry_run:
            await SqlUserRepository(self._session).lock_administration()
        cutoff = now - FAMILY_RETENTION
        sibling = aliased(RefreshTokenRow)
        terminal_family = ~exists().where(
            sibling.family_id == RefreshTokenRow.family_id, sibling.expires_at > cutoff
        )
        counts: dict[str, int] = {}

        async def batch(
            name: str,
            model: type[Base],
            key: InstrumentedAttribute[Any],
            predicate: ColumnElement[bool],
            order: InstrumentedAttribute[Any],
            user: SQLColumnExpression[UUID] | None = None,
            values: dict[str, None] | None = None,
        ) -> None:
            selection = select(key).where(predicate).order_by(order, key).limit(policy.batch_size)
            identifiers: list[UUID | str] = list(await self._session.scalars(selection))
            if dry_run or not identifiers:
                counts[name] = len(identifiers)
                return
            if user is not None:
                owners = await self._session.scalars(
                    select(user).where(key.in_(identifiers)).distinct().order_by(user)
                )
                for owner in owners:
                    await SqlUserRepository(self._session).lock_by_id(owner)
            statement = update(model).values(**values) if values is not None else delete(model)
            result = await self._session.execute(
                statement.where(key.in_(identifiers), predicate).execution_options(
                    synchronize_session=False
                )
            )
            counts[name] = int(cast("CursorResult[Any]", result).rowcount or 0)

        await batch(
            "password_links",
            PasswordTokenRow,
            PasswordTokenRow.id,
            or_(
                PasswordTokenRow.expires_at <= now - LINK_RETENTION,
                PasswordTokenRow.used_at <= now - LINK_RETENTION,
            ),
            PasswordTokenRow.created_at,
            PasswordTokenRow.user_id,
        )
        await batch(
            "mfa_challenges",
            MfaChallengeRow,
            MfaChallengeRow.token_hash,
            or_(MfaChallengeRow.expires_at <= now, MfaChallengeRow.consumed_at <= now),
            MfaChallengeRow.expires_at,
            MfaChallengeRow.user_id,
        )
        await batch(
            "pending_totp",
            AdminTotpRow,
            AdminTotpRow.user_id,
            (AdminTotpRow.pending_expires_at <= now)
            & (AdminTotpRow.pending_encrypted.is_not(None)),
            AdminTotpRow.pending_expires_at,
            AdminTotpRow.user_id,
            {"pending_encrypted": None, "pending_expires_at": None},
        )
        await batch(
            "push_receipts",
            PushDeliveryRow,
            PushDeliveryRow.id,
            exists().where(
                PushDeviceRow.id == PushDeliveryRow.device_id,
                exists().where(RefreshTokenRow.family_id == PushDeviceRow.family_id),
                ~exists().where(
                    RefreshTokenRow.family_id == PushDeviceRow.family_id,
                    RefreshTokenRow.expires_at > cutoff,
                ),
            ),
            PushDeliveryRow.created_at,
            select(PushDeviceRow.user_id)
            .where(PushDeviceRow.id == PushDeliveryRow.device_id)
            .scalar_subquery(),
        )
        await batch(
            "push_devices",
            PushDeviceRow,
            PushDeviceRow.id,
            exists().where(RefreshTokenRow.family_id == PushDeviceRow.family_id)
            & ~exists().where(
                RefreshTokenRow.family_id == PushDeviceRow.family_id,
                RefreshTokenRow.expires_at > cutoff,
            )
            & ~exists().where(PushDeliveryRow.device_id == PushDeviceRow.id),
            PushDeviceRow.created_at,
            PushDeviceRow.user_id,
        )
        await batch(
            "refresh_tokens",
            RefreshTokenRow,
            RefreshTokenRow.id,
            terminal_family & ~exists().where(PushDeviceRow.family_id == RefreshTokenRow.family_id),
            RefreshTokenRow.expires_at,
            RefreshTokenRow.user_id,
        )
        await batch(
            "family_activity",
            RefreshFamilyActivityRow,
            RefreshFamilyActivityRow.family_id,
            (RefreshFamilyActivityRow.last_activity_at <= cutoff)
            & ~exists().where(RefreshTokenRow.family_id == RefreshFamilyActivityRow.family_id)
            & ~exists().where(PushDeviceRow.family_id == RefreshFamilyActivityRow.family_id),
            RefreshFamilyActivityRow.last_activity_at,
            RefreshFamilyActivityRow.user_id,
        )
        await batch(
            "family_revocations",
            RefreshFamilyRevocationRow,
            RefreshFamilyRevocationRow.family_id,
            (RefreshFamilyRevocationRow.revoked_at <= cutoff)
            & ~exists().where(RefreshTokenRow.family_id == RefreshFamilyRevocationRow.family_id)
            & ~exists().where(PushDeviceRow.family_id == RefreshFamilyRevocationRow.family_id),
            RefreshFamilyRevocationRow.revoked_at,
        )
        await batch(
            "account_requests",
            AccountRequestRow,
            AccountRequestRow.id,
            AccountRequestRow.status.in_(("approved", "rejected"))
            & (AccountRequestRow.decided_at <= now - timedelta(days=policy.decision_days)),
            AccountRequestRow.decided_at,
        )
        return counts
