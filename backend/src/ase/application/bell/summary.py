"""One authorised read of everything the bell shows for the caller right now."""

from __future__ import annotations

from dataclasses import dataclass

from ase.application.access import AccessPolicy
from ase.application.bell.alerts import BellAlerts
from ase.application.bell.mentions import BellMentions
from ase.application.ports.bell import BellPreferenceRepository
from ase.domain.bell import BELL_ALERT_WINDOW, BellAlertSection, BellPreferences
from ase.domain.board_mentions import MentionSection
from ase.domain.users import User


@dataclass(frozen=True, slots=True)
class BellSummary:
    window_days: int
    alerts: BellAlertSection
    mentions: MentionSection
    preferences: BellPreferences


class BellService:
    def __init__(
        self,
        alerts: BellAlerts,
        mentions: BellMentions,
        preferences: BellPreferenceRepository,
        access: AccessPolicy,
    ) -> None:
        self._alerts = alerts
        self._mentions = mentions
        self._preferences = preferences
        self._access = access

    async def summary(self, actor: User) -> BellSummary:
        access = await self._access.context(actor)
        user_id = access.actor.id
        preferences = await self._preferences.get(user_id, access.visibility)
        muted_rules = await self._preferences.muted_rule_ids(user_id)
        return BellSummary(
            BELL_ALERT_WINDOW.days,
            await self._alerts.section(access, preferences, muted_rules),
            await self._mentions.section(access, preferences),
            preferences,
        )
