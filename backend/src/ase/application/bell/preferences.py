"""Each account's in-app bell choices: muted kinds and muted alert rules.

Muting is a viewing preference. It is distinct from a rule's Enabled switch, never
acknowledges anything and affects no other account, so it is not audited.
"""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.bell.scope import BellSignals
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.bell import BellPreferenceRepository
from ase.application.ports.warning import IndicatorRepository
from ase.domain.bell import MAX_RULE_MUTES, BellKind, BellPreferences
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.users import User


class BellPreferencesService:
    def __init__(
        self,
        preferences: BellPreferenceRepository,
        indicators: IndicatorRepository,
        access: AccessPolicy,
        clock: Clock,
        uow: UnitOfWork,
        signals: BellSignals,
    ) -> None:
        self._preferences = preferences
        self._indicators = indicators
        self._access = access
        self._clock = clock
        self._uow = uow
        self._signals = signals

    async def get(self, actor: User) -> BellPreferences:
        access = await self._access.context(actor)
        return await self._preferences.get(access.actor.id, access.visibility)

    async def _changed(self, actor: User) -> BellPreferences:
        await self._uow.commit()
        await self._signals.users((actor.id,))
        return await self.get(actor)

    async def set_kinds(self, actor: User, kinds: Iterable[BellKind]) -> BellPreferences:
        access = await self._access.context(actor, for_update=True)
        await self._preferences.set_kinds(access.actor.id, frozenset(kinds), self._clock.now())
        return await self._changed(actor)

    async def mute_rule(self, actor: User, indicator_id: UUID) -> BellPreferences:
        access = await self._access.context(actor, for_update=True)
        rule = await self._indicators.get(indicator_id)
        if rule is None:
            raise NotFound("Alert rule not found.")
        access.require_read(rule.created_by, rule.team_id)
        user_id = access.actor.id
        if indicator_id not in await self._preferences.muted_rule_ids(user_id):
            if await self._preferences.count_rule_mutes(user_id) >= MAX_RULE_MUTES:
                raise InvalidRequest(
                    f"You can mute up to {MAX_RULE_MUTES} alert rules. Unmute one first."
                )
            await self._preferences.mute_rule(user_id, indicator_id, self._clock.now())
        return await self._changed(actor)

    async def unmute_rule(self, actor: User, indicator_id: UUID) -> BellPreferences:
        """Undo is always allowed for the caller's own mute, even after access changes."""
        access = await self._access.context(actor, for_update=True)
        await self._preferences.unmute_rule(access.actor.id, indicator_id)
        return await self._changed(actor)
