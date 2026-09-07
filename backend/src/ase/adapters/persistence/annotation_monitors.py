"""Scope-filtered monitor storage with atomic checkpoint, transition and alert admission."""

import hashlib
from dataclasses import asdict
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.annotation_monitor_codec import (
    checked_payload,
    checked_transition,
    transition_hash,
)
from ase.adapters.persistence.annotation_monitor_models import (
    AnnotationMonitorRow as MonitorRow,
)
from ase.adapters.persistence.annotation_monitor_models import (
    AnnotationOutboxRow as OutboxRow,
)
from ase.adapters.persistence.annotation_monitor_models import (
    AnnotationTransitionRow as TransitionRow,
)
from ase.adapters.persistence.annotation_monitor_models import (
    AnnotationWatchRow as WatchRow,
)
from ase.adapters.persistence.operational_models import AlertRow
from ase.adapters.persistence.warning_mapping import _alert_row
from ase.domain.access import Visibility
from ase.domain.annotation_comparison import AnnotationKind
from ase.domain.annotation_monitoring import (
    AnnotationMonitor,
    AnnotationTransition,
    MonitorStatus,
    RevisionObservation,
    WatchedRevision,
)
from ase.domain.errors import NotFound
from ase.domain.warning import Alert


def _transition(row: TransitionRow) -> AnnotationTransition:
    return AnnotationTransition(
        row.id,
        row.monitor_id,
        row.checkpoint_before,
        row.checkpoint_after,
        row.sequence,
        cast(Literal["revision", "rebaseline"], row.kind),
        row.recorded_at,
        tuple(cast(AnnotationKind, value) for value in row.changed_categories),
        row.alert_id,
        row.comparison_sha256,
        row.configuration_revision,
        tuple(cast(AnnotationKind, c) for c in row.notification_categories),
        row.notify_on_change,
    )


class SqlAnnotationMonitorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, monitor_id: UUID) -> AnnotationMonitor | None:
        row = await self.session.get(MonitorRow, monitor_id, populate_existing=True)
        if row is None:
            return None
        watches = await self.session.scalars(
            select(WatchRow)
            .where(WatchRow.monitor_id == row.id)
            .order_by(WatchRow.kind, WatchRow.root_id)
            .execution_options(populate_existing=True)
        )
        return AnnotationMonitor(
            row.id,
            row.created_by,
            row.team_id,
            row.report_id,
            row.version_number,
            row.name,
            tuple(cast(AnnotationKind, value) for value in row.categories),
            row.notify_on_change,
            cast(MonitorStatus, row.status),
            row.unavailable_reason,
            row.revision,
            row.checkpoint_id,
            row.checkpoint_number,
            tuple(
                WatchedRevision(cast(AnnotationKind, w.kind), w.root_id, w.revision_id)
                for w in watches
            ),
            row.created_at,
            row.updated_at,
        )

    async def page(
        self,
        visibility: Visibility,
        report_id: UUID | None,
        number: int | None,
        limit: int,
        offset: int,
    ) -> tuple[list[AnnotationMonitor], int]:
        criteria = [visibility_predicate(MonitorRow.created_by, MonitorRow.team_id, visibility)]
        if report_id is not None:
            criteria.extend(
                [MonitorRow.report_id == report_id, MonitorRow.version_number == number]
            )
        total = await self.session.scalar(
            select(func.count()).select_from(MonitorRow).where(*criteria)
        )
        ids = await self.session.scalars(
            select(MonitorRow.id)
            .where(*criteria)
            .order_by(MonitorRow.created_at.desc(), MonitorRow.id)
            .limit(limit)
            .offset(offset)
        )
        return [value for key in ids if (value := await self.get(key)) is not None], int(total or 0)

    async def usage(self, owner: UUID, team: UUID | None) -> tuple[int, int, int, int]:
        scope = (
            MonitorRow.team_id == team
            if team is not None
            else and_(MonitorRow.team_id.is_(None), MonitorRow.created_by == owner)
        )
        count = await self.session.scalar(select(func.count()).select_from(MonitorRow).where(scope))
        total = await self.session.scalar(select(func.count()).select_from(MonitorRow))
        checkpoints = await self.session.scalar(
            select(func.sum(MonitorRow.checkpoint_bytes)).where(scope)
        )
        history = await self.session.scalar(
            select(func.sum(TransitionRow.byte_size))
            .join(MonitorRow, MonitorRow.id == TransitionRow.monitor_id)
            .where(scope)
        )
        global_checkpoints = await self.session.scalar(
            select(func.sum(MonitorRow.checkpoint_bytes))
        )
        global_history = await self.session.scalar(select(func.sum(TransitionRow.byte_size)))
        return (
            int(count or 0),
            int(total or 0),
            int(checkpoints or 0) + int(history or 0),
            int(global_checkpoints or 0) + int(global_history or 0),
        )

    async def create(self, monitor: AnnotationMonitor, payload: bytes) -> None:
        values = asdict(monitor)
        values.pop("watches")
        values["categories"] = list(monitor.categories)
        self.session.add(
            MonitorRow(
                **values,
                checkpoint_payload=payload.decode("utf-8"),
                checkpoint_sha256=hashlib.sha256(payload).hexdigest(),
                checkpoint_bytes=len(payload),
            )
        )
        await self.session.flush()
        self.session.add_all(
            [
                WatchRow(
                    monitor_id=monitor.id, kind=w.kind, root_id=w.root_id, revision_id=w.revision_id
                )
                for w in monitor.watches
            ]
        )
        await self.session.flush()

    async def checkpoint(self, monitor_id: UUID) -> bytes:
        row = await self.session.get(MonitorRow, monitor_id, populate_existing=True)
        if row is None:
            raise NotFound()
        return checked_payload(row.checkpoint_payload, row.checkpoint_sha256, row.checkpoint_bytes)

    async def save(self, value: AnnotationMonitor, expected_revision: int) -> bool:
        changed = await self.session.scalar(
            update(MonitorRow)
            .where(MonitorRow.id == value.id, MonitorRow.revision == expected_revision)
            .values(
                name=value.name,
                categories=list(value.categories),
                notify_on_change=value.notify_on_change,
                status=value.status,
                unavailable_reason=value.unavailable_reason,
                revision=value.revision,
                updated_at=value.updated_at,
            )
            .returning(MonitorRow.id)
            .execution_options(synchronize_session=False)
        )
        return changed is not None

    async def due(self, limit: int, after: UUID | None) -> list[UUID]:
        query = select(MonitorRow.id).where(MonitorRow.status != "paused")
        if after is not None:
            query = query.where(MonitorRow.id > after)
        return list(await self.session.scalars(query.order_by(MonitorRow.id).limit(limit)))

    async def next_event(self, monitor_id: UUID) -> RevisionObservation | None:
        row = await self.session.scalar(
            select(OutboxRow)
            .where(OutboxRow.monitor_id == monitor_id)
            .order_by(OutboxRow.id)
            .limit(1)
        )
        return (
            None
            if row is None
            else RevisionObservation(
                row.id,
                row.monitor_id,
                cast(AnnotationKind, row.kind),
                row.root_id,
                row.previous_revision_id,
                row.revision_id,
                row.created_at,
            )
        )

    async def advance(
        self,
        value: AnnotationMonitor,
        expected_revision: int,
        transition: AnnotationTransition,
        payload: bytes,
        event_id: int | None,
        alert: Alert | None,
        reset: bool = False,
    ) -> bool:
        if not await self.save(value, expected_revision):
            return False
        await self.session.execute(
            update(MonitorRow)
            .where(MonitorRow.id == value.id)
            .values(
                checkpoint_id=value.checkpoint_id,
                checkpoint_number=value.checkpoint_number,
                checkpoint_payload=payload.decode("utf-8"),
                checkpoint_sha256=hashlib.sha256(payload).hexdigest(),
                checkpoint_bytes=len(payload),
            )
        )
        for watch in value.watches:
            await self.session.execute(
                update(WatchRow)
                .where(
                    WatchRow.monitor_id == value.id,
                    WatchRow.kind == watch.kind,
                    WatchRow.root_id == watch.root_id,
                )
                .values(revision_id=watch.revision_id)
            )
        self.session.add(
            TransitionRow(
                **asdict(transition),
                payload=payload.decode("utf-8"),
                payload_sha256=transition_hash(transition, payload),
                byte_size=len(payload),
            )
        )
        if reset:
            await self.session.execute(delete(OutboxRow).where(OutboxRow.monitor_id == value.id))
        elif event_id is not None:
            await self.session.execute(
                delete(OutboxRow).where(OutboxRow.monitor_id == value.id, OutboxRow.id == event_id)
            )
        if alert is not None:
            self.session.add(_alert_row(alert))
        await self.session.flush()
        return True

    async def history(
        self, monitor_id: UUID, limit: int, offset: int
    ) -> tuple[list[AnnotationTransition], int]:
        total = await self.session.scalar(
            select(func.count())
            .select_from(TransitionRow)
            .where(TransitionRow.monitor_id == monitor_id)
        )
        rows = await self.session.scalars(
            select(TransitionRow)
            .where(TransitionRow.monitor_id == monitor_id)
            .order_by(TransitionRow.sequence.desc())
            .limit(limit)
            .offset(offset)
        )
        return [_transition(row) for row in rows], int(total or 0)

    async def transition(
        self, monitor_id: UUID, transition_id: UUID
    ) -> tuple[AnnotationTransition, bytes] | None:
        row = await self.session.get(TransitionRow, transition_id, populate_existing=True)
        if row is None or row.monitor_id != monitor_id:
            return None
        return _transition(row), checked_transition(
            _transition(row), row.payload, row.payload_sha256, row.byte_size
        )

    async def delete(self, monitor_id: UUID, expected_revision: int) -> bool:
        locked = await self.session.scalar(
            update(MonitorRow)
            .where(MonitorRow.id == monitor_id, MonitorRow.revision == expected_revision)
            .values(revision=expected_revision + 1)
            .returning(MonitorRow.id)
            .execution_options(synchronize_session=False)
        )
        if locked is None:
            return False
        await self.session.execute(
            delete(AlertRow).where(AlertRow.annotation_monitor_id == monitor_id)
        )
        for model in (OutboxRow, TransitionRow, WatchRow):
            await self.session.execute(delete(model).where(model.monitor_id == monitor_id))
        await self.session.execute(delete(MonitorRow).where(MonitorRow.id == monitor_id))
        await self.session.flush()
        return True
