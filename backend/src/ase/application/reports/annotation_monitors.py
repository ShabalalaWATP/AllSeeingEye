"""Opt-in exact-root monitoring with explicit pause, catch-up and rebaseline actions."""

from dataclasses import replace
from uuid import UUID, uuid4

from ase.application.access import AccessContext, AccessPolicy
from ase.application.dto import AccessClaims
from ase.application.ports import Clock
from ase.application.ports.annotation_monitors import AnnotationMonitorRepository, ComparisonCodec
from ase.application.reports.claim_export_selection import SelectClaimExport
from ase.application.reports.comparison_inputs import ComparisonSelection
from ase.application.reports.comparison_manifest import comparison_json
from ase.application.reports.monitor_comparisons import (
    build_observation,
    resolve_side,
    validate_options,
    watches_from_selection,
)
from ase.application.reports.monitor_observation import rebaseline
from ase.domain.annotation_comparison import AnnotationKind
from ase.domain.annotation_monitoring import (
    MAX_MONITOR_BYTES,
    MAX_MONITOR_GLOBAL_BYTES,
    MAX_MONITORS_GLOBAL,
    MAX_MONITORS_PER_SCOPE,
    AnnotationMonitor,
    MonitorAction,
)
from ase.domain.errors import Conflict, InvalidRequest, NotFound


class AnnotationMonitors:
    def __init__(
        self,
        repository: AnnotationMonitorRepository,
        selector: SelectClaimExport,
        access: AccessPolicy,
        clock: Clock,
        codec: ComparisonCodec,
    ) -> None:
        self.repository, self.selector, self.access, self.clock, self.codec = (
            repository,
            selector,
            access,
            clock,
            codec,
        )

    async def budget(
        self, monitor: AnnotationMonitor, additional: int, *, creating: bool = False
    ) -> None:
        count, total, size, global_size = await self.repository.usage(
            monitor.created_by, monitor.team_id
        )
        if (
            (creating and (count >= MAX_MONITORS_PER_SCOPE or total >= MAX_MONITORS_GLOBAL))
            or size + additional > MAX_MONITOR_BYTES
            or global_size + additional > MAX_MONITOR_GLOBAL_BYTES
        ):
            raise InvalidRequest("The monitor count or retained manifest storage limit is reached.")

    async def current(
        self, access: AccessContext, key: UUID, *, write: bool = False
    ) -> AnnotationMonitor:
        value = await self.repository.get(key)
        if value is None:
            raise NotFound("Annotation monitor not found.")
        if write:
            access.require_write(value.created_by, value.team_id)
        else:
            access.require_read(value.created_by, value.team_id)
        return value

    async def create(
        self,
        actor: AccessClaims,
        name: str,
        selection: ComparisonSelection,
        categories: tuple[AnnotationKind, ...],
        notify: bool,
    ) -> AnnotationMonitor:
        watches = watches_from_selection(selection)
        validate_options(name, categories, watches)
        try:
            access = await self.selector.claims._context(actor)
            report = await self.selector.claims._report(access, selection.report_id)
            access.require_create(report.team_id)
            access.require_same_scope(
                actor.user_id, report.team_id, report.created_by, report.team_id
            )
            now = self.clock.now()
            value = AnnotationMonitor(
                uuid4(),
                actor.user_id,
                report.team_id,
                report.id,
                selection.version_number,
                name.strip(),
                categories,
                notify,
                "active",
                None,
                1,
                uuid4(),
                0,
                watches,
                now,
                now,
            )
            await self.budget(value, 1, creating=True)
            side, latest = await resolve_side(self.selector, access, value, latest=True)
            if latest != watches:
                raise Conflict("A selected root has a newer revision. Refresh the selection.")
            payload = comparison_json(build_observation(side, side, actor.user_id, now))
            await self.budget(value, len(payload), creating=True)
            await self.repository.create(value, payload)
            await self.selector.uow.commit()
            return value
        except BaseException:
            await self.selector.uow.rollback()
            raise

    async def get(self, actor: AccessClaims, key: UUID) -> AnnotationMonitor:
        try:
            access = await self.selector.claims._context(actor)
            value = await self.current(access, key)
            await self.selector.uow.commit()
            return value
        except BaseException:
            await self.selector.uow.rollback()
            raise

    async def page(
        self,
        actor: AccessClaims,
        report_id: UUID | None,
        number: int | None,
        limit: int,
        offset: int,
    ) -> tuple[list[AnnotationMonitor], int]:
        if (
            (report_id is None) != (number is None)
            or not 1 <= limit <= 50
            or not 0 <= offset <= 1_000_000
        ):
            raise InvalidRequest("Choose a bounded monitor page and paired report/version filters.")
        try:
            access = await self.selector.claims._context(actor)
            if report_id is not None:
                await self.selector.claims._report(access, report_id)
            result = await self.repository.page(access.visibility, report_id, number, limit, offset)
            await self.selector.uow.commit()
            return result
        except BaseException:
            await self.selector.uow.rollback()
            raise

    async def update(
        self,
        actor: AccessClaims,
        key: UUID,
        expected: int,
        action: MonitorAction,
        name: str | None = None,
        categories: tuple[AnnotationKind, ...] | None = None,
        notify: bool | None = None,
        rebaseline_policy: bool = False,
    ) -> AnnotationMonitor:
        try:
            access = await self.selector.claims._context(actor)
            previous = await self.current(access, key, write=True)
            if previous.revision != expected:
                raise Conflict("The monitor changed. Refresh before updating it.")
            value = replace(previous, revision=expected + 1, updated_at=self.clock.now())
            if action == "configure":
                value = replace(
                    value,
                    name=name.strip() if name is not None else value.name,
                    categories=categories if categories is not None else value.categories,
                    notify_on_change=notify if notify is not None else value.notify_on_change,
                )
                validate_options(value.name, value.categories, value.watches)
                if (value.categories, value.notify_on_change) != (
                    previous.categories,
                    previous.notify_on_change,
                ):
                    if not rebaseline_policy:
                        raise InvalidRequest(
                            "Confirm a fresh baseline before changing notification policy."
                        )
                    result = await rebaseline(self, access, previous, value, actor.user_id)
                    await self.selector.uow.commit()
                    return result
            elif action == "pause":
                value = replace(value, status="paused", unavailable_reason=None)
            elif action in {"resume_catch_up", "resume_rebaseline"}:
                if previous.status == "active":
                    raise InvalidRequest("Pause the monitor before choosing a resume policy.")
                await resolve_side(self.selector, access, previous)
                value = replace(value, status="active", unavailable_reason=None)
                if action == "resume_rebaseline":
                    result = await rebaseline(self, access, previous, value, actor.user_id)
                    await self.selector.uow.commit()
                    return result
            else:
                raise InvalidRequest("Unknown monitor action.")
            if not await self.repository.save(value, expected):
                raise Conflict("The monitor changed. Refresh before updating it.")
            await self.selector.uow.commit()
            return value
        except BaseException:
            await self.selector.uow.rollback()
            raise

    async def delete(self, actor: AccessClaims, key: UUID, expected: int) -> None:
        try:
            access = await self.selector.claims._context(actor)
            monitor = await self.current(access, key, write=True)
            if monitor.revision != expected or not await self.repository.delete(key, expected):
                raise Conflict("The monitor changed. Refresh before deleting its history.")
            await self.selector.uow.commit()
        except BaseException:
            await self.selector.uow.rollback()
            raise
