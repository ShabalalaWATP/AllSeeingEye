"""Atomic page and cursor storage for authorised selected subscriptions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.selected_index_eviction import enforce_owner_limits
from ase.adapters.persistence.selected_index_models import (
    SelectedIndexCursorRow,
    SelectedIndexGateRow,
    SelectedIndexLossRow,
    SelectedIndexRecordRow,
)
from ase.domain.errors import Conflict, Forbidden
from ase.domain.selected_subscription_index import SelectedIndexLimits, SelectedMetadata, _key, _utc


def _page_digest(
    records: tuple[SelectedMetadata, ...], cursor_value: str | None, watermark_at: datetime | None
) -> str:
    payload = {
        "fingerprints": [record.fingerprint for record in records],
        "cursor_value": cursor_value,
        "watermark_at": watermark_at.isoformat() if watermark_at is not None else None,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_page(
    source_id: str,
    page_key: str,
    expected_revision: int,
    records: tuple[SelectedMetadata, ...],
    cursor_value: str | None,
    watermark_at: datetime | None,
    now: datetime,
    limits: SelectedIndexLimits,
) -> tuple[datetime, datetime | None, str]:
    _key(source_id, "source_id", 100)
    _key(page_key, "page_key", 128)
    if type(expected_revision) is not int or expected_revision < 0:
        raise ValueError("expected_revision must be non-negative")
    if type(records) is not tuple or len(records) > limits.page_records:
        raise ValueError("page exceeds the record ceiling")
    if any(
        type(record) is not SelectedMetadata or record.source_id != source_id for record in records
    ):
        raise ValueError("page records must be validated and from the selected source")
    if sum(record.stored_bytes for record in records) > limits.owner_bytes:
        raise ValueError("page exceeds owner byte ceiling")
    if len({record.fingerprint for record in records}) > limits.owner_records:
        raise ValueError("page exceeds owner item ceiling")
    if cursor_value is not None and (
        type(cursor_value) is not str
        or not 1 <= len(cursor_value) <= 512
        or any(ord(char) < 32 for char in cursor_value)
    ):
        raise ValueError("cursor_value must be bounded and printable")
    normalised_now = _utc(now, "now")
    watermark_at = _utc(watermark_at, "watermark_at")
    if normalised_now is None:
        raise ValueError("now is required")
    return normalised_now, watermark_at, _page_digest(records, cursor_value, watermark_at)


class SqlSelectedSubscriptionIndexRepository:
    """Caller owns the transaction and supplies verified current team memberships.

    Each page is a savepoint inside that transaction. No network call belongs inside it.
    The caller must only submit sources and policy receipts admitted for this subscription.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _schedule(
        self,
        subscription_id: UUID,
        *,
        actor_id: UUID,
        authorised_team_ids: tuple[UUID, ...],
    ) -> ScheduleRow:
        if (
            not isinstance(subscription_id, UUID)
            or not isinstance(actor_id, UUID)
            or not isinstance(authorised_team_ids, tuple)
            or any(not isinstance(team_id, UUID) for team_id in authorised_team_ids)
        ):
            raise ValueError("Use authenticated actor and verified team identifiers")
        personal_scope = and_(ScheduleRow.team_id.is_(None), ScheduleRow.created_by == actor_id)
        scope = (
            or_(personal_scope, ScheduleRow.team_id.in_(authorised_team_ids))
            if authorised_team_ids
            else personal_scope
        )
        schedule = await self.session.scalar(
            select(ScheduleRow).where(ScheduleRow.id == subscription_id, scope)
        )
        if schedule is None:
            raise Forbidden("Selected subscription is not authorised")
        return schedule

    async def _writable_schedule(
        self,
        subscription_id: UUID,
        *,
        actor_id: UUID,
        authorised_team_ids: tuple[UUID, ...],
    ) -> ScheduleRow:
        schedule = await self._schedule(
            subscription_id, actor_id=actor_id, authorised_team_ids=authorised_team_ids
        )
        # The background collector acts as the originating owner after a fresh
        # membership check. Mere team read membership does not grant page writes.
        if schedule.created_by != actor_id:
            raise Forbidden("Only the selected subscription owner may retain pages")
        if not schedule.enabled:
            raise Conflict("Selected subscription is disabled")
        return schedule

    async def get_cursor(
        self,
        subscription_id: UUID,
        source_id: str,
        *,
        actor_id: UUID,
        authorised_team_ids: tuple[UUID, ...] = (),
    ) -> SelectedIndexCursorRow | None:
        _key(source_id, "source_id", 100)
        await self._schedule(
            subscription_id, actor_id=actor_id, authorised_team_ids=authorised_team_ids
        )
        return await self.session.get(SelectedIndexCursorRow, (subscription_id, source_id))

    async def list_records(
        self,
        subscription_id: UUID,
        *,
        actor_id: UUID,
        authorised_team_ids: tuple[UUID, ...] = (),
        limit: int = 100,
    ) -> tuple[SelectedIndexRecordRow, ...]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be 1 to 100")
        await self._schedule(
            subscription_id, actor_id=actor_id, authorised_team_ids=authorised_team_ids
        )
        rows = await self.session.scalars(
            select(SelectedIndexRecordRow)
            .where(SelectedIndexRecordRow.subscription_id == subscription_id)
            .order_by(SelectedIndexRecordRow.id.desc())
            .limit(limit)
        )
        return tuple(rows)

    async def list_losses(
        self,
        subscription_id: UUID,
        *,
        actor_id: UUID,
        authorised_team_ids: tuple[UUID, ...] = (),
    ) -> tuple[SelectedIndexLossRow, ...]:
        await self._schedule(
            subscription_id, actor_id=actor_id, authorised_team_ids=authorised_team_ids
        )
        rows = await self.session.scalars(
            select(SelectedIndexLossRow)
            .where(SelectedIndexLossRow.subscription_id == subscription_id)
            .order_by(SelectedIndexLossRow.source_id, SelectedIndexLossRow.reason)
            .limit(128)
        )
        return tuple(rows)

    async def persist_page(
        self,
        subscription_id: UUID,
        source_id: str,
        *,
        actor_id: UUID,
        authorised_team_ids: tuple[UUID, ...] = (),
        expected_revision: int,
        page_key: str,
        records: tuple[SelectedMetadata, ...],
        cursor_value: str | None,
        watermark_at: datetime | None,
        now: datetime,
        limits: SelectedIndexLimits | None = None,
    ) -> int:
        """Retain a completed page and advance its cursor in one caller-owned transaction."""

        limits = limits or SelectedIndexLimits()
        now, watermark_at, digest = _validate_page(
            source_id, page_key, expected_revision, records, cursor_value, watermark_at, now, limits
        )
        schedule = await self._writable_schedule(
            subscription_id, actor_id=actor_id, authorised_team_ids=authorised_team_ids
        )
        # Write before SAVEPOINT so SQLite opens the outer transaction. The gate also
        # serialises aggregate quota decisions on PostgreSQL until caller commit.
        gate_id = await self.session.scalar(
            update(SelectedIndexGateRow)
            .where(SelectedIndexGateRow.id == 1)
            .values(revision=SelectedIndexGateRow.revision + 1)
            .returning(SelectedIndexGateRow.id)
        )
        if gate_id != 1:
            raise Conflict("Selected-index write gate is unavailable")
        async with self.session.begin_nested():
            cursor = await self.session.get(SelectedIndexCursorRow, (subscription_id, source_id))
            if cursor is None:
                source_count = await self.session.scalar(
                    select(func.count())
                    .select_from(SelectedIndexCursorRow)
                    .where(SelectedIndexCursorRow.subscription_id == subscription_id)
                )
                if (source_count or 0) >= limits.sources_per_subscription:
                    raise Conflict("Selected subscription source ceiling is reached")
            if cursor is not None and cursor.last_page_key == page_key:
                if cursor.last_page_sha256 != digest:
                    raise Conflict("Selected-index page key was reused with different content")
                return cursor.revision
            current_revision = cursor.revision if cursor is not None else 0
            if current_revision != expected_revision:
                raise Conflict("Selected-index cursor changed; retry from the stored cursor")
            if (
                cursor is not None
                and cursor.watermark_at is not None
                and (watermark_at is None or watermark_at < cursor.watermark_at)
            ):
                raise Conflict("Selected-index watermark cannot move backwards")

            for record in records:
                existing = await self.session.scalar(
                    select(SelectedIndexRecordRow.id).where(
                        SelectedIndexRecordRow.subscription_id == subscription_id,
                        SelectedIndexRecordRow.fingerprint == record.fingerprint,
                    )
                )
                if existing is not None:
                    continue
                previous = await self.session.scalar(
                    select(SelectedIndexRecordRow)
                    .where(
                        SelectedIndexRecordRow.subscription_id == subscription_id,
                        SelectedIndexRecordRow.source_id == source_id,
                        SelectedIndexRecordRow.origin_key == record.origin_key,
                    )
                    .order_by(SelectedIndexRecordRow.id.desc())
                    .limit(1)
                )
                self.session.add(
                    SelectedIndexRecordRow(
                        subscription_id=subscription_id,
                        owner_id=schedule.created_by,
                        team_id=schedule.team_id,
                        source_id=source_id,
                        item_key=record.item_key,
                        origin_key=record.origin_key,
                        source_version=record.source_version,
                        title=record.title,
                        content_sha256=record.content_sha256,
                        fingerprint=record.fingerprint,
                        policy_id=record.policy_id,
                        retention_days=record.retention_days,
                        stored_bytes=record.stored_bytes,
                        retrieved_at=record.retrieved_at,
                        published_at=record.published_at,
                        observed_at=record.observed_at,
                        updated_at=record.updated_at,
                        first_seen_at=now,
                        expires_at=now
                        + timedelta(days=min(record.retention_days, limits.max_age_days)),
                        corrects_id=previous.id if previous is not None else None,
                        corrects_fingerprint=(
                            previous.fingerprint if previous is not None else None
                        ),
                    )
                )
                await self.session.flush()
            await enforce_owner_limits(
                self.session, owner_id=schedule.created_by, now=now, limits=limits
            )
            if cursor is None:
                self.session.add(
                    SelectedIndexCursorRow(
                        subscription_id=subscription_id,
                        source_id=source_id,
                        owner_id=schedule.created_by,
                        team_id=schedule.team_id,
                        revision=1,
                        cursor_value=cursor_value,
                        watermark_at=watermark_at,
                        last_page_key=page_key,
                        last_page_sha256=digest,
                        updated_at=now,
                    )
                )
            else:
                cursor.revision += 1
                cursor.cursor_value = cursor_value
                cursor.watermark_at = watermark_at
                cursor.last_page_key = page_key
                cursor.last_page_sha256 = digest
                cursor.updated_at = now
            await self.session.flush()
            return current_revision + 1
