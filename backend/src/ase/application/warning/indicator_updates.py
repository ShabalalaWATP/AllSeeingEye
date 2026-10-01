"""Editing, pausing and resuming one alert rule in place, guarded by its current revision.

A rule's revision is its `updated_at` value. An edit names the revision it was made from and
is written with one conditional update, so two edits of the same revision cannot both land.
Personal or team scope never changes through editing. Removing a location, category or
keyword restriction makes the rule unrestricted on that dimension, so it needs an explicit
confirmation rather than happening because a field was left empty.

Pausing (`enabled` false) stops evaluation: a paused rule raises no alert, notification or
report. Resuming records the resume instant, and evaluation then counts only activity
published after it, so the paused period is never replayed as a burst of alerts.
"""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime
from uuid import UUID

from ase.application.direction.plan_updates import next_revision
from ase.application.dto import RequestContext
from ase.application.warning.indicators import IndicatorInput, _IndicatorUseCase, build_indicator
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.users import User
from ase.domain.warning import Indicator

STALE_RULE = (
    "This alert rule was changed after you opened it. Reload the latest version and reapply "
    "your edits before saving."
)
_UNTRACKED = frozenset({"id", "created_by", "created_at", "updated_at", "resumed_at"})


def widened_dimensions(before: Indicator, after: Indicator) -> dict[str, str]:
    """Restrictions the edit removes entirely, by the request field that removed them."""
    widened: dict[str, str] = {}
    located = before.countries or before.bbox or before.research_area
    if located and not (after.countries or after.bbox or after.research_area):
        widened["countries"] = "This removes the location restriction: the rule watches everywhere."
    if before.categories and not after.categories:
        widened["categories"] = "This removes the category restriction: every category counts."
    if before.keywords and not after.keywords:
        widened["keywords"] = "This removes the keyword restriction: every matching item counts."
    return widened


def changed_fields(before: Indicator, after: Indicator) -> list[str]:
    return [
        item.name
        for item in fields(Indicator)
        if item.name not in _UNTRACKED and getattr(before, item.name) != getattr(after, item.name)
    ]


def _audit_action(before: Indicator, after: Indicator) -> AuditAction:
    if before.enabled and not after.enabled:
        return AuditAction.INDICATOR_PAUSED
    if after.enabled and not before.enabled:
        return AuditAction.INDICATOR_RESUMED
    return AuditAction.INDICATOR_UPDATED


class UpdateIndicatorUseCase(_IndicatorUseCase):
    async def execute(
        self,
        actor: User,
        indicator_id: UUID,
        data: IndicatorInput,
        expected_updated_at: datetime,
        context: RequestContext,
        *,
        confirm_wider_scope: bool = False,
    ) -> Indicator:
        access = await self._access.context(actor, for_update=True)
        existing = await self._indicators.get(indicator_id)
        if existing is None:
            raise NotFound("Alert rule not found.")
        access.require_write(existing.created_by, existing.team_id)
        if data.team_id != existing.team_id:
            raise InvalidRequest("An alert rule's personal or team scope cannot be changed.")
        if existing.updated_at != expected_updated_at:
            raise Conflict(STALE_RULE)
        # Pausing never needs the linked plan; a new link or a running rule always does.
        if data.enabled or data.plan_id != existing.plan_id:
            await self._check_plan(data, existing.created_by, access)
        now = next_revision(existing.updated_at, self._clock.now())
        resumed = data.enabled and not existing.enabled
        indicator = build_indicator(
            data, templates=self._templates, indicator_id=existing.id,
            owner=existing.created_by, created=existing.created_at, now=now,
            resumed_at=now if resumed else existing.resumed_at,
        )  # fmt: skip
        widened = widened_dimensions(existing, indicator)
        if widened and not confirm_wider_scope:
            raise InvalidRequest(
                "This edit would make the alert rule unrestricted. Choose specific values, or "
                "confirm the wider scope before saving.",
                fields=widened,
            )
        if not await self._indicators.save_if_unchanged(indicator, expected_updated_at):
            await self._uow.rollback()
            raise Conflict(STALE_RULE)
        await self._auditor.record(
            _audit_action(existing, indicator), actor=actor.id, subject=str(indicator.id),
            ip=context.ip,
            details={"name": indicator.name, "changed": changed_fields(existing, indicator)},
        )  # fmt: skip
        await self._uow.commit()
        return indicator
