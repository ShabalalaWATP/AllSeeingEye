"""Composition for bounded subscription settings edits."""

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.subscription_settings import SqlSubscriptionSettings
from ase.application.schedules.edit_brief_settings import EditBriefSettings
from ase.container import Container


def brief_settings_editor(container: Container, session: AsyncSession) -> EditBriefSettings:
    repos = container.repositories(session)
    return EditBriefSettings(
        SqlSubscriptionSettings(session),
        container.access_policy(session),
        container.clock,
        container._auditor(repos),
        repos.uow,
    )
